import os
import subprocess
import logging
import math
import re
import json
import io
import csv
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_bam_header, calculate_bam_md5, is_sorted, resolve_reference, verify_paths_exist
from wgsextract_cli.core.constants import SEQUENCERS, REFERENCE_MODELS, REF_GENOME_FILENAMES, N_ADJUST

def determine_sequencer(qname):
    """Identify sequencer type from QNAME using regex patterns."""
    if not qname: return "Unknown"
    for name, pattern in SEQUENCERS.items():
        if re.search(pattern, qname):
            return name
    return "Unknown"

def register(subparsers, base_parser):
    parser = subparsers.add_parser("info", parents=[base_parser], help="Parses header, verifies coordinate sorting, calculates stats and detects reference genome signature.")
    parser.add_argument("--detailed", action="store_true", help="Perform full index and body sample analysis (detailed mode)")
    parser.add_argument("--csv", action="store_true", help="Output the table as CSV instead of formatted text")
    
    info_subs = parser.add_subparsers(dest="info_cmd", required=False)
    calc_cov = info_subs.add_parser("calculate-coverage", parents=[base_parser], help="Calculate FULL breadth coverage using samtools depth (1-3 hours)")
    calc_cov.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM)")
    calc_cov.set_defaults(func=run)

    samp_cov = info_subs.add_parser("coverage-sample", parents=[base_parser], help="Estimate coverage using random sampling (under 10 seconds)")
    samp_cov.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM)")
    samp_cov.set_defaults(func=run)
    
    parser.set_defaults(func=run)

def get_file_stats(filepath):
    """Retrieve file size and check for index existence."""
    size_bytes = os.path.getsize(filepath)
    size_gb = size_bytes / (1024**3)
    
    indexed = False
    if os.path.exists(filepath + ".bai") or os.path.exists(filepath + ".crai"):
        indexed = True
    elif filepath.endswith(".bam") and os.path.exists(filepath[:-4] + ".bai"):
        indexed = True
    elif filepath.endswith(".cram") and os.path.exists(filepath[:-5] + ".crai"):
        indexed = True
        
    return size_gb, indexed

def run_body_sample(filepath, cram_opt):
    """Sample first 100k reads to calculate length, insert size, and read type."""
    logging.info(f"Sampling reads from {os.path.basename(filepath)} for metrics...")
    cmd = ["samtools", "view"] + (cram_opt if cram_opt else []) + [filepath]
    
    total_len = total_tlen = count = paired_count = 0
    tlen_values = []
    len_values = []
    first_qname = None
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL)
        for _ in range(100000):
            line = proc.stdout.readline()
            if not line: break
            fields = line.split("\t")
            if len(fields) < 11: continue
            
            if first_qname is None: first_qname = fields[0]
            flag, tlen, seq = int(fields[1]), abs(int(fields[8])), fields[9]
            
            if flag & 1: paired_count += 1
            seq_len = len(seq)
            total_len += seq_len
            len_values.append(seq_len)
            
            if tlen > 0:
                total_tlen += tlen
                tlen_values.append(tlen)
            count += 1
        proc.terminate()
    except Exception: pass
        
    avg_len = total_len / count if count > 0 else 0
    avg_tlen = total_tlen / len(tlen_values) if len(tlen_values) > 0 else 0
    std_len = math.sqrt(sum((x - avg_len)**2 for x in len_values) / count) if count > 1 else 0
    std_tlen = math.sqrt(sum((x - avg_tlen)**2 for x in tlen_values) / len(tlen_values)) if len(tlen_values) > 1 else 0
    is_paired = paired_count > (count / 2) if count > 0 else False
    
    return count, avg_len, std_len, avg_tlen, std_tlen, is_paired, first_qname

def parse_idxstats(filepath):
    """Parse samtools idxstats for mapped/unmapped counts."""
    idx = subprocess.run(["samtools", "idxstats", filepath], capture_output=True, text=True)
    stats, genome_len, total_mapped, total_unmapped = [], 0, 0, 0
    
    for line in idx.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            name, length, mapped, unmapped = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            stats.append({"name": name, "length": length, "mapped": mapped, "unmapped": unmapped})
            if name != "*": genome_len += length
            total_mapped += mapped
            total_unmapped += unmapped
            
    return stats, genome_len, total_mapped, total_unmapped

def generate_chrom_table(idx_stats, avg_len, gender, ref_model_name, coverage_map=None):
    """Build the detailed per-chromosome metrics table."""
    valid_autos, valid_somal = [str(i) for i in range(1, 23)], ['X', 'Y']
    stats_autos, stats_somal, stats_mito = [], [], []
    if coverage_map is None: coverage_map = {}
    
    build = '38' if '38' in ref_model_name else '37' if '37' in ref_model_name else '19' if '19' in ref_model_name else '99'
    n_adjust_map = N_ADJUST.get(build, {})
    
    stats_total, stats_altcont = ["T", "Total", 0, 0, 0, 0.0, 0.0, ""], ["O", "Other", 0, 0, 0, 0.0, 0.0, ""]
    
    for s in idx_stats:
        if s["mapped"] == 0: continue
        chromosome = s["name"]
        chromnum = chromosome.upper().replace("CHR", "").replace("MT", "M")
        map_seg, mod_len = s["mapped"] + s["unmapped"], s["length"]
        n_count = n_adjust_map.get(chromnum, 0)
        cvg = coverage_map.get(chromnum, "")
        row = [chromnum, chromosome, mod_len, n_count, map_seg, 0.0, 0.0, cvg]
        
        if chromnum in valid_autos: stats_autos.append(row)
        elif chromnum in valid_somal: stats_somal.append(row)
        elif chromnum == "M": stats_mito.append(row)
        elif chromnum != "*":
            stats_altcont[2] += mod_len
            stats_altcont[4] += map_seg
            
    stats_autos.sort(key=lambda x: int(x[0]))
    stats_somal.sort(key=lambda x: x[0])
    final_table = stats_autos + stats_somal + stats_mito
    
    for row in final_table:
        if row[0] == 'Y' and gender == 'Female': continue
        stats_total[2] += row[2]
        stats_total[3] += row[3]
        stats_total[4] += row[4]
    
    final_table.append(stats_total)
    if stats_altcont[4] > 0: final_table.append(stats_altcont)
        
    for i in range(len(final_table)):
        eff_len = final_table[i][2] - final_table[i][3] + 0.0001
        temp_mapped_gbases = float(final_table[i][4] * avg_len)
        final_table[i][5] = round(temp_mapped_gbases / (10**9), 2)
        final_table[i][6] = round(temp_mapped_gbases / eff_len)
        if final_table[i][1] in ["Total", "Other"]:
            final_table[i][7] = coverage_map.get("TOTAL_EST" if final_table[i][1] == "Total" else "OTHER", "")
            
    return final_table

def render_info(data):
    """Generate the formatted console output string."""
    output_lines = []
    if data.get("chrom_table_csv"):
        output_lines.append("By Reference Sequence Name\nSeq        Model    Model    # Segs      Map    Map Breadth\nName         Len  'N' Len       Map   Gbases    ARD Coverage")
        def fmt_num(val):
            val = int(val)
            if val == 0: return "0 K"
            if val >= 1_000_000: return f"{val / 1_000_000:.0f} M"
            return f"{val / 1_000:.0f} K" if val >= 1_000 else str(val)

        reader = csv.DictReader(io.StringIO(data["chrom_table_csv"]))
        for r in reader:
            output_lines.append(f"{r['Seq Name']:<7} {fmt_num(r['Model Len']):>8} {fmt_num(r['Model N Len']):>8} {fmt_num(r['# Segs Map']):>9} {float(r['Map Gbases']):>8.2f} {float(r['Map ARD']):>6.0f} x {r['Breadth Coverage']:>8}")
        output_lines.append("\n" + "-" * 60 + "\n")

    output_lines.append(f"{data.get('filename', 'Unknown')}\n{'':<28}{'MAPPED':<15}{'RAW'}")
    m = data.get("metrics", {})
    output_lines.append(f"{'Avg Read Depth':<28}{m.get('ard_mapped', 0):.0f} x{'':<11}{m.get('ard_raw', 0):.0f} x\n{'Avg Read Depth (WES)':<28}")
    output_lines.append(f"{'Gigabases':<28}{m.get('gbases_mapped', 0):.2f}{'':<11}{m.get('gbases_raw', 0):.2f}")
    output_lines.append(f"{'Read Segs':<28}{m.get('reads_mapped_m', 0):.0f} M{'':<11}{m.get('reads_raw_m', 0):.0f} M")
    output_lines.append(f"{'Reads':<28}{m.get('reads_mapped_pct', 0):.0f} %{'':<12}{m.get('reads_raw_pct', 100):.0f} %\n\n{'Reference Model':<28}{data.get('ref_model_str', 'Unknown')}")
    
    if data.get("avg_read_len", 0) > 0:
        output_lines.append(f"{'Avg Read Length':<28}{data['avg_read_len']:.0f} bp, {data.get('std_read_len', 0):.0f} σ, {'Paired-end' if data.get('is_paired') else 'Single-end'}")
        output_lines.append(f"{'Avg Insert Size':<28}{data.get('avg_insert_size', 0):.0f} bp, {data.get('std_insert_size', 0):.0f} σ")
    else:
        output_lines.append(f"{'Avg Read Length':<28}Could not compute")
        
    output_lines.append(f"{'File Content':<28}{data.get('file_content', 'Unknown')}\n{'Bio Gender':<28}{data.get('gender', 'Unknown')}\n{'Sequencer':<28}{data.get('sequencer', 'Unknown')}")
    fstats = data.get("file_stats", {})
    output_lines.append(f"{'File Stats':<28}{'Sorted' if fstats.get('sorted') else 'Unsorted'}, {'Indexed' if fstats.get('indexed') else 'Unindexed'}, {fstats.get('size_gb', 0):.1f} GBs")
    return "\n".join(output_lines) + "\n"

def run_full_coverage(input_p, ref_p, out_p, region=None):
    """Long-running full breadth coverage pipeline."""
    if os.path.exists(out_p) and os.path.getsize(out_p) > 120: return
    print(f"Calculating full coverage (1-3 hours)... saving to {out_p}")
    awk = "{ names[$1]=$1 ; if($3==0){zero[$1]++} else {nz[$1]++ ; sumnz[$1]+=$3 ; if($3>7){nI[$1]++ ; sumnI[$1]+=$3} else {if($3>3){n7[$1]++ ; sumn7[$1]+=$3} else {n3[$1]++ ; sumn3[$1]+=$3} } } } END { printf(\"%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n\",\"chr\",\"zero\",\"nonzero\",\"sum nz\",\"fract nz\",\"avg nz\",\"avg all\",\"TotalBC\",\"Bet1-3\",\"sum Bet1-3\",\"Bet4-7\",\"sum Bet4-7\",\"Gtr7\",\"sum Gtr7\"); for (x in names) { totalbc = zero[x]+nz[x]+1 ; printf(\"%s\\t%d\\t%d\\t%d\\t%f\\t%f\\t%f\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n\",x,zero[x],nz[x],sumnz[x],nz[x]/totalbc,sumnz[x]/(nz[x]+1),sumnz[x]/totalbc,totalbc-1,n3[x],sumn3[x],n7[x],sumn7[x],nI[x],sumnI[x]) } }"
    
    opts = []
    if input_p.lower().endswith(".cram") and ref_p:
        if os.path.isfile(str(ref_p)):
            opts = ["--reference", str(ref_p)]
            
    try:
        region_args = ["-r", region] if region else []
        cmd = ["samtools", "depth", "-aa"] + region_args + opts + [input_p]
        cmd = [x for x in cmd if x is not None]
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["awk", awk], stdin=p1.stdout, stdout=open(out_p, "w"))
        p1.stdout.close(); p2.communicate()
    except Exception as e: logging.error(f"Coverage failed: {e}")

def run_sampled_coverage(input_p, ref_p, idx_stats, out_p, region=None):
    """Fast sampling-based coverage estimation."""
    import random
    print("Estimating coverage using random sampling..."); sample_results, total_b, covered_b = {}, 0, 0
    
    if region:
        chroms = [(s["name"], s["length"], s["name"].upper().replace("CHR", "").replace("MT", "M")) for s in idx_stats if s["name"] == region]
    else:
        chroms = [(s["name"], s["length"], s["name"].upper().replace("CHR", "").replace("MT", "M")) for s in idx_stats if s["length"] > 100_000 and (s["name"].upper().replace("CHR", "").isdigit() or s["name"].upper().replace("CHR", "") in ["X", "Y"])]
    
    if not chroms: return
    
    opts = []
    if input_p.lower().endswith(".cram") and ref_p:
        if os.path.isfile(str(ref_p)):
            opts = ["--reference", str(ref_p)]

    for _ in range(100):
        cname, clen, cnum = random.choice(chroms)
        start = random.randint(1, clen - 1000)
        cmd = ["samtools", "depth", "-a", "-G", "0", "-Q", "0", "-r", f"{cname}:{start}-{start+999}"] + opts + [input_p]
        cmd = [x for x in cmd if x is not None]
        res = subprocess.run(cmd, capture_output=True, text=True)
        win_total = win_covered = 0
        if res.stdout:
            for line in res.stdout.splitlines():
                parts = line.split('\t'); 
                if len(parts) < 3: continue
                win_total += 1
                if int(parts[2]) > 0: win_covered += 1
        if win_total > 0:
            if cnum not in sample_results: sample_results[cnum] = []
            sample_results[cnum].append(win_covered / win_total)
            total_b += win_total; covered_b += win_covered
    final_map = {cnum: f"~{sum(scores)/len(scores)*100:.0f} %" for cnum, scores in sample_results.items()}
    if total_b > 0: final_map["TOTAL_EST"] = f"~{covered_b/total_b*100:.0f} %"
    with open(out_p, "w") as f: json.dump(final_map, f)

def run(args):
    verify_dependencies(["samtools"])
    if not args.input: return logging.error("--input required.")
    
    if not verify_paths_exist({'--input': args.input}): return

    print(f"Analyzing {args.input}...")
    md5_sig = calculate_bam_md5(args.input, None)
    resolved_ref = resolve_reference(args.ref, md5_sig)
    
    if getattr(args, "info_cmd", None) in ["calculate-coverage", "coverage-sample"]: args.detailed = True
    if args.detailed and args.input.lower().endswith(".cram") and not resolved_ref: return logging.error("--ref required for detailed mode with CRAM.")
        
    outdir = args.outdir if hasattr(args, "outdir") and args.outdir else os.path.dirname(os.path.abspath(args.input))
    json_cache = os.path.join(outdir, f"{os.path.basename(args.input)}.wgse_info.json")

    if args.detailed and os.path.exists(json_cache) and getattr(args, "info_cmd", None) not in ["calculate-coverage", "coverage-sample"]:
        print(f"Loading cached metrics from {json_cache}...")
        try:
            with open(json_cache, "r") as f: data = json.load(f)
            if getattr(args, "csv", False): print(data.get("chrom_table_csv", ""), end="")
            else: print(render_info(data))
            return
        except Exception: pass

    cram_opt = ["-T", resolved_ref] if resolved_ref else []
    sorted_status = is_sorted(args.input, cram_opt)
    size_gb, indexed = get_file_stats(args.input)
    if not args.detailed:
        from wgsextract_cli.core.warnings import print_warning
        if not sorted_status or not indexed:
            print_warning('warnBAMNoStatsNoIndex')
        if args.input.lower().endswith(".cram"):
            print_warning('warnCRAMNoStats')

        print(f"{'='*60}\nFilename: {os.path.basename(args.input)}\nMD5: {md5_sig}\nStats: {'Sorted' if sorted_status else 'Unsorted'}, {'Indexed' if indexed else 'Unindexed'}, {size_gb:.1f} GBs\n{'='*60}\nNote: Fast mode. Run with --detailed for more.")
        return
    
    count, avg_len, std_len, avg_tlen, std_tlen, is_paired, first_qname = run_body_sample(args.input, cram_opt)
    sequencer = determine_sequencer(first_qname)
    idx_stats, genome_len, total_mapped, total_unmapped = parse_idxstats(args.input)
    total_reads = total_mapped + total_unmapped
    ref_model_name, ref_mito, _ = REFERENCE_MODELS.get(md5_sig, ("Unknown", "", ""))
    ref_model_str = f"{ref_model_name} (Chr), {ref_mito}, {len([s for s in idx_stats if s['name'] != '*'])} SNs" if ref_model_name != "Unknown" else f"Unknown, {len([s for s in idx_stats if s['name'] != '*'])} SNs"
    
    cov_file, sample_file = os.path.join(outdir, f"{os.path.basename(args.input)}_bincvg.csv"), os.path.join(outdir, f"{os.path.basename(args.input)}_samplecvg.json")
    
    region = getattr(args, "region", None)
    if getattr(args, "info_cmd", None) == "calculate-coverage": run_full_coverage(args.input, resolved_ref, cov_file, region=region)
    elif getattr(args, "info_cmd", None) == "coverage-sample": run_sampled_coverage(args.input, resolved_ref, idx_stats, sample_file, region=region)

    coverage_map = {}
    if os.path.exists(cov_file) and os.path.getsize(cov_file) > 120:
        with open(cov_file, "r") as f:
            for line in f.readlines()[1:]:
                p = line.split('\t')
                if len(p) > 7: coverage_map[p[0].upper().replace("CHR", "").replace("MT", "M")] = f"{(int(p[2])/int(p[7]))*100:.0f} %"
    elif os.path.exists(sample_file):
        try:
            with open(sample_file, "r") as f: coverage_map = json.load(f)
        except Exception: pass

    y_reads = next((s["mapped"] for s in idx_stats if s["name"].upper().replace("CHR", "") == "Y"), 0)
    x_reads = next((s["mapped"] for s in idx_stats if s["name"].upper().replace("CHR", "") == "X"), 0)
    gender = ("Male" if y_reads > (x_reads * 0.05) else "Female") if x_reads > 0 else "Unknown"
    chrom_table = generate_chrom_table(idx_stats, avg_len, gender, ref_model_name, coverage_map)
    total_row = next(r for r in chrom_table if r[1] == "Total")
    mapped_segs = total_row[4] + next((r[4] for r in chrom_table if r[1] == "Other"), 0)
    
    data = {
        "filename": os.path.basename(args.input), "md5_signature": md5_sig,
        "file_stats": {"sorted": sorted_status, "indexed": indexed, "size_gb": size_gb},
        "ref_model_str": ref_model_str, "avg_read_len": avg_len, "std_read_len": std_len, "is_paired": is_paired,
        "avg_insert_size": avg_tlen, "std_insert_size": std_tlen, "gender": gender, "sequencer": sequencer,
        "file_content": ", ".join([k for k, v in {"Auto": any(s["mapped"] > 0 and s["name"].upper().replace("CHR", "").isdigit() for s in idx_stats), "X": x_reads > 0, "Y": y_reads > 0, "Mito": any(s["mapped"] > 0 and s["name"].upper().replace("CHR", "") in ["M", "MT"] for s in idx_stats), "Other": any(s["mapped"] > 0 and s["name"] != "*" and not s["name"].upper().replace("CHR", "").isdigit() and s["name"].upper().replace("CHR", "") not in ["X", "Y", "M", "MT"] for s in idx_stats)}.items() if v] + (["Unmap"] if total_unmapped > 0 else [])),
        "metrics": {
            "ard_mapped": (total_row[4]*avg_len)/(total_row[2]-total_row[3]+0.0001), "ard_raw": (total_reads*avg_len)/(total_row[2]-total_row[3]+0.0001),
            "gbases_mapped": (mapped_segs*avg_len)/(10**9), "gbases_raw": (total_reads*avg_len)/(10**9),
            "reads_mapped_m": mapped_segs/1_000_000, "reads_raw_m": total_reads/1_000_000,
            "reads_mapped_pct": (mapped_segs/total_reads*100) if total_reads > 0 else 0, "reads_raw_pct": 100.0
        }
    }
    si = io.StringIO(); cw = csv.writer(si)
    cw.writerow(["Seq Name", "Model Len", "Model N Len", "# Segs Map", "Map Gbases", "Map ARD", "Breadth Coverage"])
    for row in chrom_table: cw.writerow([row[1], row[2], row[3], row[4], f"{row[5]:.2f}", f"{row[6]:.0f}", row[7]])
    data["chrom_table_csv"] = si.getvalue()

    from wgsextract_cli.core.warnings import print_warning
    if avg_len > 410:
        print_warning('LongReadSequenceWarning')
    if data['metrics']['ard_mapped'] < 10:
        print_warning('LowCoverageWarning')

    if getattr(args, "csv", False): print(data["chrom_table_csv"], end="")
    else:
        print(render_info(data))
        try:
            with open(json_cache, "w") as f: json.dump(data, f, indent=2)
            print(f"(Metrics cached to {json_cache} for future runs)")
        except Exception: pass
