import csv
import io
import json
import logging
import math
import os
import re
import subprocess
import time
from typing import Any

from wgsextract_cli.core.constants import (
    N_ADJUST,
    REFERENCE_MODELS,
    REFGEN_BY_SNCOUNT,
    SEQUENCERS,
)
from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    get_bam_header,
    is_sorted,
    verify_paths_exist,
)


def determine_sequencer(qname):
    """Identify sequencer type from QNAME using regex patterns."""
    if not qname:
        return "Unknown"
    for name, pattern in SEQUENCERS.items():
        if re.search(pattern, qname):
            # Special logic for Dante MGI flow plate ID from legacy
            if "6xxx" in name:
                return name.replace("6xxx", qname[6:10] + " bad")
            return name
    # If unrecognized, return "Unknown" so we can show the full QNAME in detailed info
    return "Unknown"


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "info", parents=[base_parser], help=CLI_HELP["cmd_info"]
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help=CLI_HELP["arg_detailed"],
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help=CLI_HELP["arg_csv"],
    )

    info_subs = parser.add_subparsers(dest="info_cmd", required=False)
    calc_cov = info_subs.add_parser(
        "calculate-coverage",
        parents=[base_parser],
        help=CLI_HELP["cmd_calculate-coverage"],
    )
    calc_cov.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    calc_cov.set_defaults(func=run)

    samp_cov = info_subs.add_parser(
        "coverage-sample", parents=[base_parser], help=CLI_HELP["cmd_coverage-sample"]
    )
    samp_cov.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    samp_cov.set_defaults(func=run)

    parser.set_defaults(func=run)


def get_file_stats(filepath):
    """Retrieve file size and check for index existence."""
    size_bytes = os.path.getsize(filepath)
    size_gb = size_bytes / (1024**3)

    indexed = False
    # Check for direct appended index (e.g. file.bam.bai, file.cram.crai)
    if os.path.exists(filepath + ".bai") or os.path.exists(filepath + ".crai"):
        indexed = True
    # Check for replaced extension index (e.g. file.bai, file.crai)
    elif filepath.lower().endswith(".bam") and os.path.exists(filepath[:-4] + ".bai"):
        indexed = True
    elif filepath.lower().endswith(".cram") and os.path.exists(filepath[:-5] + ".crai"):
        indexed = True
    # Check for .csi index (sometimes used for large files)
    elif os.path.exists(filepath + ".csi"):
        indexed = True

    return size_gb, indexed


def run_body_sample(filepath, cram_opt):
    """Sample first 20k reads to calculate length, insert size, and read type."""
    logging.info(
        LOG_MESSAGES["sampling_metrics"].format(filename=os.path.basename(filepath))
    )
    cmd = ["samtools", "view"] + (cram_opt if cram_opt else []) + [filepath]

    total_len = count = paired_count = 0
    tlen_values = []
    len_values = []
    first_qname = None

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL
        )
        assert proc.stdout is not None
        for _ in range(20000):
            line = proc.stdout.readline()
            if not line:
                break
            fields = line.split("\t")
            if len(fields) < 11:
                continue

            if first_qname is None:
                first_qname = fields[0]

            flag = int(fields[1])
            rnext = fields[6]
            tlen = int(fields[8])
            seq = fields[9]

            # Skip supplementary, secondary, or fail-QC reads (0xB00)
            if flag & 0xB00:
                continue

            if flag & 1:
                paired_count += 1

            seq_len = len(seq)
            if seq_len > 1:
                total_len += seq_len
                len_values.append(seq_len)
                count += 1

            # Only process forward reads with valid next segment on same chrom
            # and limit to 50k to match legacy behavior (avoids chimeric skews)
            if rnext == "=" and 0 < tlen < 50000:
                tlen_values.append(tlen)

        proc.terminate()
    except Exception:
        pass

    avg_len = total_len / count if count > 0 else 0
    avg_tlen = sum(tlen_values) / len(tlen_values) if len(tlen_values) > 0 else 0
    std_len = (
        math.sqrt(sum((x - avg_len) ** 2 for x in len_values) / count)
        if count > 1
        else 0
    )
    std_tlen = (
        math.sqrt(sum((x - avg_tlen) ** 2 for x in tlen_values) / len(tlen_values))
        if len(tlen_values) > 1
        else 0
    )
    is_paired = paired_count > (count / 2) if count > 0 else False

    return count, avg_len, std_len, avg_tlen, std_tlen, is_paired, first_qname


def load_n_counts(ref_path):
    """Try to load chromosome N counts from a sidecar _ncnt.csv file."""
    if not ref_path or not os.path.isfile(ref_path):
        return {}

    prefix = re.sub(r"\.(fasta|fna|fa)(\.gz)?$", "", ref_path)
    ncnt_file = prefix + "_ncnt.csv"
    if not os.path.exists(ncnt_file):
        return {}

    logging.debug(LOG_MESSAGES["info_loading_n"].format(file=ncnt_file))
    n_counts = {}
    try:
        with open(ncnt_file, newline="") as f:
            # Try to detect if it's tab-separated or comma-separated
            first_line = f.readline()
            f.seek(0)
            delimiter = "\t" if "\t" in first_line else ","
            reader = csv.reader(f, delimiter=delimiter)
            for row in reader:
                if (
                    len(row) >= 3
                ):  # countingNs script uses SN, NumBP, NumNs (so index 2)
                    chrom, count = row[0], row[2]
                    if chrom.startswith("#"):
                        continue
                    # Normalize chrom name like generate_chrom_table does
                    cnum = chrom.upper().replace("CHR", "").replace("MT", "M")
                    try:
                        # Remove commas from number if present (e.g. 1,234,567)
                        clean_count = count.replace(",", "")
                        n_counts[cnum] = int(float(clean_count))
                    except ValueError:
                        pass
                elif len(row) >= 2:
                    chrom, count = row[0], row[1]
                    if chrom.startswith("#"):
                        continue
                    cnum = chrom.upper().replace("CHR", "").replace("MT", "M")
                    try:
                        clean_count = count.replace(",", "")
                        n_counts[cnum] = int(float(clean_count))
                    except ValueError:
                        pass
    except Exception as e:
        logging.debug(f"Failed to read {ncnt_file}: {e}")

    return n_counts


def parse_idxstats(filepath):
    """Parse samtools idxstats for mapped/unmapped counts."""
    idx = subprocess.run(
        ["samtools", "idxstats", filepath], capture_output=True, text=True
    )
    stats, genome_len, total_mapped, total_unmapped = [], 0, 0, 0

    for line in idx.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4:
            name, length, mapped, unmapped = (
                parts[0],
                int(parts[1]),
                int(parts[2]),
                int(parts[3]),
            )
            stats.append(
                {"name": name, "length": length, "mapped": mapped, "unmapped": unmapped}
            )
            if name != "*":
                genome_len += length
            total_mapped += mapped
            total_unmapped += unmapped

    return stats, genome_len, total_mapped, total_unmapped


def generate_chrom_table(
    idx_stats, avg_len, gender, ref_model_name, coverage_map=None, n_counts=None
):
    """Build the detailed per-chromosome metrics table."""
    valid_autos, valid_somal, valid_mito = (
        [str(i) for i in range(1, 23)],
        ["X", "Y"],
        ["M"],
    )
    if "DOG" in ref_model_name.upper():
        valid_autos = [str(i) for i in range(1, 39)]
        valid_somal = ["X"]
        valid_mito = ["M"]
        build = "Dog"
    elif "CAT" in ref_model_name.upper():
        valid_autos = [
            "A1",
            "A2",
            "A3",
            "B1",
            "B2",
            "B3",
            "B4",
            "C1",
            "C2",
            "D1",
            "D2",
            "D3",
            "D4",
            "E1",
            "E2",
            "E3",
            "F1",
            "F2",
        ]
        valid_somal = ["X", "Y"]
        valid_mito = ["M"]
        build = "Cat"
    else:
        build = (
            "38"
            if any(x in ref_model_name.upper() for x in ["38", "HG38", "GRCH38"])
            else "37"
            if any(x in ref_model_name.upper() for x in ["37", "HG19", "GRCH37"])
            else "19"
            if "19" in ref_model_name
            else "99"
        )

    stats_autos: list[list[Any]] = []
    stats_somal: list[list[Any]] = []
    stats_mito: list[list[Any]] = []
    if coverage_map is None:
        coverage_map = {}

    # Use loaded N counts if available, otherwise fallback to hardcoded defaults
    n_adjust_map = N_ADJUST.get(build, {}).copy()
    if n_counts:
        n_adjust_map.update(n_counts)

    stats_total: list[Any] = ["T", "Total", 0, 0, 0, 0.0, 0.0, ""]
    stats_altcont: list[Any] = ["O", "Other", 0, 0, 0, 0.0, 0.0, ""]

    for s in idx_stats:
        if s["mapped"] == 0:
            continue
        chromosome = s["name"]
        chromnum = chromosome.upper().replace("CHR", "").replace("MT", "M")
        map_seg, mod_len = s["mapped"] + s["unmapped"], s["length"]
        n_count = n_adjust_map.get(chromnum, 0)
        cvg = coverage_map.get(chromnum, "")
        row = [chromnum, chromosome, mod_len, n_count, map_seg, 0.0, 0.0, cvg]

        if chromnum in valid_autos:
            stats_autos.append(row)
        elif chromnum in valid_somal:
            stats_somal.append(row)
        elif chromnum in valid_mito:
            stats_mito.append(row)
        elif chromnum != "*":
            stats_altcont[2] += mod_len
            stats_altcont[4] += map_seg

    if build == "Cat":
        stats_autos.sort(key=lambda x: x[0])
    else:
        stats_autos.sort(key=lambda x: int(x[0]) if x[0].isdigit() else x[0])

    stats_somal.sort(key=lambda x: x[0])
    final_table = stats_autos + stats_somal + stats_mito

    for row in final_table:
        if row[0] == "Y" and gender == "Female" and build not in ["Dog", "Cat"]:
            continue
        stats_total[2] += row[2]
        stats_total[3] += row[3]
        stats_total[4] += row[4]

    final_table.append(stats_total)
    if int(stats_altcont[4]) > 0:
        final_table.append(stats_altcont)

    for i in range(len(final_table)):
        eff_len = final_table[i][2] - final_table[i][3] + 0.0001
        temp_mapped_gbases = float(final_table[i][4] * avg_len)
        final_table[i][5] = round(temp_mapped_gbases / (10**9), 2)
        final_table[i][6] = round(temp_mapped_gbases / eff_len)
        if final_table[i][1] in ["Total", "Other"]:
            final_table[i][7] = coverage_map.get(
                "TOTAL_EST" if final_table[i][1] == "Total" else "OTHER", ""
            )

    return final_table


def render_info(data, detailed=False):
    """Generate the formatted console output string."""
    output_lines = []
    if detailed and data.get("chrom_table_csv"):
        reader = list(csv.DictReader(io.StringIO(data["chrom_table_csv"])))

        # Check if we actually have any coverage data to show
        has_coverage = any(
            r.get("Breadth Coverage") for r in reader if r.get("Breadth Coverage")
        )

        header_line1 = LOG_MESSAGES["info_header1"]
        header_line2 = LOG_MESSAGES["info_header2"]
        if has_coverage:
            header_line1 += LOG_MESSAGES["info_header_breadth"]
            header_line2 += LOG_MESSAGES["info_header_coverage"]

        output_lines.append(
            f"{LOG_MESSAGES['info_rendering_name']}\n{header_line1}\n{header_line2}"
        )

        def fmt_num(val):
            val = int(float(val))
            if val == 0:
                return "0 K"
            if val >= 1_000_000:
                return f"{val / 1_000_000:.0f} M"
            return f"{val / 1_000:.0f} K" if val >= 1_000 else str(val)

        for r in reader:
            row = f"{r['Seq Name']:<7} {fmt_num(r['Model Len']):>8} {fmt_num(r['Model N Len']):>8} {fmt_num(r['# Segs Map']):>9} {float(r['Map Gbases']):>8.2f} {float(r['Map ARD']):>6.0f} x"
            if has_coverage:
                row += f" {r['Breadth Coverage']:>8}"
            output_lines.append(row)
        output_lines.append("\n" + "-" * 60 + "\n")

    m = data.get("metrics", {})
    if detailed:
        output_lines.append(
            f"{data.get('filename', 'Unknown')}\n{'':<28}{'MAPPED':<15}{'RAW'}"
        )
        output_lines.append(
            f"{LOG_MESSAGES['info_avg_read_depth']:<28}{m.get('ard_mapped', 0):.0f} x{'':<11}{m.get('ard_raw', 0):.0f} x"
        )
        output_lines.append(
            f"{LOG_MESSAGES['info_avg_read_depth_wes']:<28}{m.get('ard_wes_mapped', '')}{'':<11}{m.get('ard_wes_raw', '')}"
        )
        output_lines.append(
            f"{LOG_MESSAGES['info_gigabases']:<28}{m.get('gbases_mapped', 0):.2f}{'':<11}{m.get('gbases_raw', 0):.2f}"
        )
        output_lines.append(
            f"{LOG_MESSAGES['info_read_segs']:<28}{m.get('reads_mapped_m', 0):.0f} M{'':<11}{m.get('reads_raw_m', 0):.0f} M"
        )
        output_lines.append(
            f"{LOG_MESSAGES['info_reads']:<28}{m.get('reads_mapped_pct', 0):.0f} %{'':<12}{m.get('reads_raw_pct', 100):.0f} %\n"
        )

    output_lines.append(
        f"{LOG_MESSAGES['info_ref_genome']:<28}{data.get('ref_model_str', 'Unknown')}"
    )
    if data.get("md5_signature"):
        output_lines.append(f"{'MD5 Signature:':<28}{data['md5_signature']}")
    if data.get("refined_ns"):
        output_lines.append(
            f"{LOG_MESSAGES['info_refined_ns']:<28}{LOG_MESSAGES['info_refined_ns_active']}"
        )

    if data.get("avg_read_len", 0) > 0:
        output_lines.append(
            f"{LOG_MESSAGES['info_avg_read_len']:<28}{data['avg_read_len']:.0f} bp (SD={data.get('std_read_len', 0):.0f} bp), {'Paired-end' if data.get('is_paired') else 'Single-end'}"
        )
        output_lines.append(
            f"{LOG_MESSAGES['info_avg_insert_size']:<28}{data.get('avg_insert_size', 0):.0f} bp (SD={data.get('std_insert_size', 0):.0f} bp)"
        )
    else:
        output_lines.append(
            f"{LOG_MESSAGES['info_avg_read_len']:<28}{LOG_MESSAGES['info_could_not_compute']}"
        )

    if detailed:
        output_lines.append(
            f"{LOG_MESSAGES['info_file_content']:<28}{data.get('file_content', 'Unknown')}"
        )

    if data.get("gender") and data.get("gender") != "Unknown":
        output_lines.append(
            f"{LOG_MESSAGES['info_bio_gender']:<28}{data.get('gender')}"
        )
    if data.get("sequencer"):
        if data["sequencer"] != "Unknown":
            output_lines.append(
                f"{LOG_MESSAGES['info_sequencer']:<28}{data.get('sequencer')}"
            )
        elif detailed and data.get("first_qname"):
            output_lines.append(
                f"{LOG_MESSAGES['info_sequencer']:<28}Unknown: {data['first_qname']}"
            )

    fstats = data.get("file_stats", {})
    output_lines.append(
        f"{LOG_MESSAGES['info_file_stats']:<28}{'Sorted' if fstats.get('sorted') else 'Unsorted'}, {'Indexed' if fstats.get('indexed') else 'Unindexed'}, {fstats.get('size_gb', 0):.1f} GBs"
    )
    if fstats.get("version"):
        output_lines.append(f"{'File Format':<28}{fstats['version']}")

    if detailed:
        glossary = [
            "\n" + "=" * 60,
            "GLOSSARY",
            "=" * 60,
            "TABLE COLUMNS:",
            "  Seq Name        - Reference sequence or chromosome name.",
            "  Model Len       - Total length of the reference sequence.",
            "  Model 'N' Len   - Number of 'N' bases (gaps) in the reference.",
            "  # Segs Map      - Count of read segments mapped to this sequence.",
            "  Map Gbases      - Billions of bases mapped to this sequence.",
            "  Map ARD         - Average Read Depth (Gbases / Effective Length).",
            "  Breadth Coverage- % of sequence covered by at least one read.",
            "",
            "METRICS SUMMARY:",
            "  MAPPED          - Statistics for reads aligned to the reference.",
            "  RAW             - Statistics for all reads (aligned + unaligned).",
            "  Avg Read Depth  - Mean depth across all positions.",
            "  ARD (WES)       - Estimated depth if limited to exome regions.",
            "  Gigabases       - Total data volume in billions of base pairs.",
            "  Read Segs       - Total number of reads/segments in millions.",
            "  Reads %         - Percentage of total reads successfully mapped.",
            "",
            "REFERENCE GENOME:",
            "  Build Name      - e.g., hs38DH, hg19. (Chr)=Primary only, (Full)=All.",
            "  Mito Type       - rCRS (Modern) or Yoruba (Legacy) mtDNA reference.",
            "  SNs             - Total count of named sequences in the reference.",
            "",
            "OTHER:",
            "  Bio Gender      - Predicted biological sex based on X/Y ratio.",
            "  Avg Read Length - Mean base pairs per read (SD = standard deviation).",
            "  Avg Insert Size - Mean distance between pairs (inner + reads).",
            "  File Content    - Auto (Autosomes), X/Y, Mito, Other (Alts), Unmap.",
            "  Sequencer       - Identified sequencing platform based on read IDs.",
            "  File Stats      - Binary status (Sorted/Indexed) and file size.",
            "=" * 60,
        ]
        output_lines.extend(glossary)

    return "\n".join(output_lines) + "\n"


def run_full_coverage(input_p, ref_p, out_p, region=None):
    """Long-running full breadth coverage pipeline."""
    if os.path.exists(out_p) and os.path.getsize(out_p) > 120:
        return
    print(LOG_MESSAGES["info_full_coverage"].format(path=out_p))
    awk = '{ names[$1]=$1 ; if($3==0){zero[$1]++} else {nz[$1]++ ; sumnz[$1]+=$3 ; if($3>7){nI[$1]++ ; sumnI[$1]+=$3} else {if($3>3){n7[$1]++ ; sumn7[$1]+=$3} else {n3[$1]++ ; sumn3[$1]+=$3} } } } END { printf("%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n","chr","zero","nonzero","sum nz","fract nz","avg nz","avg all","TotalBC","Bet1-3","sum Bet1-3","Bet4-7","sum Bet4-7","Gtr7","sum Gtr7"); for (x in names) { totalbc = zero[x]+nz[x]+1 ; printf("%s\\t%d\\t%d\\t%d\\t%f\\t%f\\t%f\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\t%d\\n",x,zero[x],nz[x],sumnz[x],nz[x]/totalbc,sumnz[x]/(nz[x]+1),sumnz[x]/totalbc,totalbc-1,n3[x],sumn3[x],n7[x],sumn7[x],nI[x],sumnI[x]) } }'

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
        if p1.stdout:
            p1.stdout.close()
        p2.communicate()
    except Exception as e:
        logging.error(f"Coverage failed: {e}")


def run_sampled_coverage(input_p, ref_p, idx_stats, out_p, region=None):
    """Fast sampling-based coverage estimation."""
    import random

    print(LOG_MESSAGES["info_sampling_coverage"])
    sample_results: dict[str, Any] = {}
    total_b, covered_b = 0, 0

    if region:
        chroms = [
            (
                s["name"],
                s["length"],
                s["name"].upper().replace("CHR", "").replace("MT", "M"),
            )
            for s in idx_stats
            if s["name"] == region
        ]
    else:
        chroms = [
            (
                s["name"],
                s["length"],
                s["name"].upper().replace("CHR", "").replace("MT", "M"),
            )
            for s in idx_stats
            if s["length"] > 100_000
            and (
                s["name"].upper().replace("CHR", "").isdigit()
                or s["name"].upper().replace("CHR", "") in ["X", "Y"]
            )
        ]

    if not chroms:
        return

    opts = []
    if input_p.lower().endswith(".cram") and ref_p:
        if os.path.isfile(str(ref_p)):
            opts = ["--reference", str(ref_p)]

    for _ in range(100):
        cname, clen, cnum = random.choice(chroms)
        start = random.randint(1, clen - 1000)
        cmd = (
            [
                "samtools",
                "depth",
                "-a",
                "-G",
                "0",
                "-Q",
                "0",
                "-r",
                f"{cname}:{start}-{start + 999}",
            ]
            + opts
            + [input_p]
        )
        cmd = [x for x in cmd if x is not None]
        res = subprocess.run(cmd, capture_output=True, text=True)
        win_total = win_covered = 0
        if res.stdout:
            for line in res.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                win_total += 1
                if int(parts[2]) > 0:
                    win_covered += 1
        if win_total > 0:
            if cnum not in sample_results:
                sample_results[cnum] = []
            sample_results[cnum].append(win_covered / win_total)
            total_b += win_total
            covered_b += win_covered
    final_map = {
        cnum: f"~{sum(scores) / len(scores) * 100:.0f} %"
        for cnum, scores in sample_results.items()
    }
    if total_b > 0:
        final_map["TOTAL_EST"] = f"~{covered_b / total_b * 100:.0f} %"
    with open(out_p, "w") as f:
        json.dump(final_map, f)


def run(args):
    from wgsextract_cli.core.utils import resolve_reference

    start_time = time.time()
    verify_dependencies(["samtools"])
    log_dependency_info(["samtools"])
    if not args.input:
        return logging.error("--input required.")

    if not verify_paths_exist({"--input": args.input}):
        return

    logging.debug(f"Input file: {os.path.abspath(args.input)}")

    # Fetch header once to avoid redundant subprocess calls
    t0 = time.time()
    # If it's a CRAM and we have a ref, try to resolve it early to help samtools read the header
    initial_ref = None
    if args.input.lower().endswith(".cram") and args.ref:
        resolved = resolve_reference(args.ref, None)
        if resolved and os.path.isfile(resolved):
            initial_ref = resolved
            logging.debug(
                f"CRAM detected, using resolved reference for header: {initial_ref}"
            )
        else:
            logging.debug("CRAM detected, but reference is not installed or invalid.")

    header = get_bam_header(args.input, cram_opt=initial_ref)
    if not header:
        logging.error(
            f"Could not read header from {args.input}. Samtools might be missing, file is corrupt, or it requires a reference (-T)."
        )
        return
    logging.debug(f"Header fetch took {time.time() - t0:.3f}s")

    # Calculate MD5 from header to identify reference genome
    t0 = time.time()
    md5_sig = calculate_bam_md5(args.input, header=header)
    logging.debug(f"MD5 signature: {md5_sig} (took {time.time() - t0:.3f}s)")

    t0 = time.time()
    resolved_ref = resolve_reference(args.ref, md5_sig)
    logging.debug(f"Resolved reference: {resolved_ref} (took {time.time() - t0:.3f}s)")

    if getattr(args, "info_cmd", None) in ["calculate-coverage", "coverage-sample"]:
        args.detailed = True
    if args.detailed and args.input.lower().endswith(".cram") and not resolved_ref:
        return logging.error("--ref required for detailed mode with CRAM.")

    outdir = (
        args.outdir
        if hasattr(args, "outdir") and args.outdir
        else os.path.dirname(os.path.abspath(args.input))
    )
    # Ensure outdir exists if explicitly provided
    if hasattr(args, "outdir") and args.outdir:
        os.makedirs(outdir, exist_ok=True)

    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    json_cache = os.path.join(outdir, f"{os.path.basename(args.input)}.wgse_info.json")

    data = {}
    if os.path.exists(json_cache):
        logging.debug(f"Cache file found: {json_cache}")
        try:
            with open(json_cache) as f:
                data = json.load(f)
            # If we only wanted fast mode and we have it, we can return early
            if not args.detailed and data.get("avg_read_len"):
                logging.debug("Cache hit for fast metrics.")
                print(render_info(data, detailed=False))
                return
            # If we wanted detailed mode and we have the chrom table, we can return early
            if (
                args.detailed
                and data.get("chrom_table_csv")
                and getattr(args, "info_cmd", None)
                not in ["calculate-coverage", "coverage-sample"]
            ):
                logging.debug("Cache hit for detailed metrics.")
                if getattr(args, "csv", False):
                    print(data.get("chrom_table_csv", ""), end="")
                else:
                    print(render_info(data, detailed=True))
                return
            logging.debug(
                f"Cache miss or partial: detailed={args.detailed}, has_read_len={bool(data.get('avg_read_len'))}, has_chrom_table={bool(data.get('chrom_table_csv'))}"
            )
        except Exception as e:
            logging.debug(f"Cache read error: {e}")
            pass
    else:
        logging.debug(f"No cache file at {json_cache}")

    # 1. FAST METRICS (Compute if missing from cache)
    if not data.get("avg_read_len"):
        logging.debug("Generating fast metrics...")
        cram_opt = []
        if resolved_ref and os.path.isfile(resolved_ref):
            cram_opt = ["-T", resolved_ref]

        t0 = time.time()
        sorted_status = is_sorted(args.input, cram_opt, header=header)
        logging.debug(f"Sort check: {sorted_status} (took {time.time() - t0:.3f}s)")

        t0 = time.time()
        size_gb, indexed = get_file_stats(args.input)
        logging.debug(
            f"File stats: {size_gb:.2f}GB, indexed={indexed} (took {time.time() - t0:.3f}s)"
        )

        from wgsextract_cli.core.utils import get_file_version

        file_version = get_file_version(args.input)

        # Get SN count from header for fast mode
        num_sns = len([line for line in header.splitlines() if line.startswith("@SQ")])

        ref_model_name, ref_mito, ref_fname = REFERENCE_MODELS.get(
            md5_sig, ("Unknown", "", "")
        )

        # Guess from SN count if MD5 is unknown
        if ref_model_name == "Unknown" and num_sns in REFGEN_BY_SNCOUNT:
            # Entry format: [is_primary, filename, mito_tag]
            _, ref_fname_raw, ref_mito_raw = REFGEN_BY_SNCOUNT[num_sns]
            ref_fname = str(ref_fname_raw)
            ref_mito = str(ref_mito_raw)
            # Deduce name from filename
            if "hg19" in ref_fname.lower() or "grch37" in ref_fname.lower():
                ref_model_name = "hg19"
            elif "hg38" in ref_fname.lower() or "grch38" in ref_fname.lower():
                ref_model_name = "hg38"
            else:
                ref_model_name = ref_fname.split(".")[0]

        # Guess from filename if still unknown
        if ref_model_name == "Unknown" and resolved_ref:
            bn = os.path.basename(resolved_ref).upper()
            if any(x in bn for x in ["38", "HG38", "GRCH38"]):
                ref_model_name = "hg38"
            elif any(x in bn for x in ["37", "HG19", "GRCH37"]):
                ref_model_name = "hg19"
            elif any(x in bn for x in ["T2T", "CHM13"]):
                ref_model_name = "t2t"
            elif "19" in bn:
                ref_model_name = "hg19"

        ref_model_str = (
            f"{ref_model_name} (Chr), {ref_mito}, {num_sns} SNs"
            if ref_model_name != "Unknown"
            else f"Unknown, {num_sns} SNs"
        )

        t0 = time.time()
        (
            count,
            avg_len,
            std_len,
            avg_tlen,
            std_tlen,
            is_paired,
            first_qname,
        ) = run_body_sample(args.input, cram_opt)
        logging.debug(f"Body sampling took {time.time() - t0:.3f}s")

        sequencer = determine_sequencer(first_qname)

        # Populate data dict with fast metrics
        data.update(
            {
                "filename": os.path.basename(args.input),
                "md5_signature": md5_sig,
                "file_stats": {
                    "sorted": sorted_status,
                    "indexed": indexed,
                    "size_gb": size_gb,
                    "version": file_version,
                },
                "ref_model_str": ref_model_str,
                "suggested_ref_file": ref_fname,
                "avg_read_len": avg_len,
                "std_read_len": std_len,
                "is_paired": is_paired,
                "avg_insert_size": avg_tlen,
                "std_insert_size": std_tlen,
                "sequencer": sequencer,
                "first_qname": first_qname,
            }
        )

    if not args.detailed:
        print(render_info(data, detailed=False))
        # Save cache even in fast mode
        try:
            with open(json_cache, "w") as f:
                json.dump(data, f, indent=2)
            logging.debug(f"Fast metrics cached to {json_cache}")
        except Exception:
            pass
        logging.debug(f"Total info time: {time.time() - start_time:.3f}s")
        return

    # 2. DETAILED METRICS (Compute if missing from cache)
    if not data.get("chrom_table_csv") or getattr(args, "info_cmd", None) in [
        "calculate-coverage",
        "coverage-sample",
    ]:
        t0 = time.time()
        idx_stats, genome_len, total_mapped, total_unmapped = parse_idxstats(args.input)
        logging.debug(f"Idxstats took {time.time() - t0:.3f}s")

        total_reads = total_mapped + total_unmapped

        # Extract variables from data for calculations
        avg_len = data["avg_read_len"]
        ref_model_name = (
            data["ref_model_str"].split(" (")[0]
            if " (" in data["ref_model_str"]
            else "Unknown"
        )

        cov_file, sample_file = (
            os.path.join(outdir, f"{os.path.basename(args.input)}_bincvg.csv"),
            os.path.join(outdir, f"{os.path.basename(args.input)}_samplecvg.json"),
        )

        info_cmd = getattr(args, "info_cmd", None)
        region = getattr(args, "region", None)

        coverage_map = {}
        if info_cmd == "calculate-coverage":
            run_full_coverage(args.input, resolved_ref, cov_file, region=region)
            if os.path.exists(cov_file) and os.path.getsize(cov_file) > 120:
                with open(cov_file) as f:
                    for line in f.readlines()[1:]:
                        p = line.split("\t")
                        if len(p) > 7:
                            coverage_map[
                                p[0].upper().replace("CHR", "").replace("MT", "M")
                            ] = f"{(int(p[2]) / int(p[7])) * 100:.0f} %"
        elif info_cmd == "coverage-sample":
            run_sampled_coverage(
                args.input, resolved_ref, idx_stats, sample_file, region=region
            )
            if os.path.exists(sample_file):
                try:
                    with open(sample_file) as f:
                        coverage_map = json.load(f)
                except Exception:
                    pass

        y_reads = next(
            (
                s["mapped"]
                for s in idx_stats
                if s["name"].upper().replace("CHR", "") == "Y"
            ),
            0,
        )
        x_reads = next(
            (
                s["mapped"]
                for s in idx_stats
                if s["name"].upper().replace("CHR", "") == "X"
            ),
            0,
        )
        gender = (
            ("Male" if y_reads > (x_reads * 0.05) else "Female")
            if x_reads > 0
            else "Unknown"
        )

        n_counts = load_n_counts(resolved_ref)
        if n_counts:
            data["refined_ns"] = True

        chrom_table = generate_chrom_table(
            idx_stats, avg_len, gender, ref_model_name, coverage_map, n_counts=n_counts
        )
        total_row = next(r for r in chrom_table if r[1] == "Total")
        mapped_segs = total_row[4] + next(
            (r[4] for r in chrom_table if r[1] == "Other"), 0
        )

        # Detailed metrics update
        data.update(
            {
                "gender": gender,
                "file_content": ", ".join(
                    [
                        k
                        for k, v in {
                            "Auto": any(
                                s["mapped"] > 0
                                and s["name"].upper().replace("CHR", "").isdigit()
                                for s in idx_stats
                            ),
                            "X": x_reads > 0,
                            "Y": y_reads > 0,
                            "Mito": any(
                                s["mapped"] > 0
                                and s["name"].upper().replace("CHR", "") in ["M", "MT"]
                                for s in idx_stats
                            ),
                            "Other": any(
                                s["mapped"] > 0
                                and s["name"] != "*"
                                and not s["name"].upper().replace("CHR", "").isdigit()
                                and s["name"].upper().replace("CHR", "")
                                not in ["X", "Y", "M", "MT"]
                                for s in idx_stats
                            ),
                        }.items()
                        if v
                    ]
                    + (["Unmap"] if total_unmapped > 0 else [])
                ),
                "metrics": {
                    "ard_mapped": (total_row[4] * avg_len)
                    / (total_row[2] - total_row[3] + 0.0001),
                    "ard_raw": (total_reads * avg_len)
                    / (total_row[2] - total_row[3] + 0.0001),
                    "gbases_mapped": (mapped_segs * avg_len) / (10**9),
                    "gbases_raw": (total_reads * avg_len) / (10**9),
                    "reads_mapped_m": mapped_segs / 1_000_000,
                    "reads_raw_m": total_reads / 1_000_000,
                    "reads_mapped_pct": (mapped_segs / total_reads * 100)
                    if total_reads > 0
                    else 0,
                    "reads_raw_pct": 100.0,
                },
            }
        )

        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(
            [
                "Seq Name",
                "Model Len",
                "Model N Len",
                "# Segs Map",
                "Map Gbases",
                "Map ARD",
                "Breadth Coverage",
            ]
        )
        for row in chrom_table:
            cw.writerow(
                [
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    f"{row[5]:.2f}",
                    f"{row[6]:.0f}",
                    row[7],
                ]
            )
        data["chrom_table_csv"] = si.getvalue()

    # Common detailed output and final save
    from wgsextract_cli.core.warnings import print_warning

    if data.get("avg_read_len", 0) > 410:
        print_warning("LongReadSequenceWarning")
    if data.get("metrics", {}).get("ard_mapped", 0) < 10:
        print_warning("LowCoverageWarning")

    if getattr(args, "csv", False):
        print(data["chrom_table_csv"], end="")
    else:
        print(render_info(data, detailed=True))
        try:
            with open(json_cache, "w") as f:
                json.dump(data, f, indent=2)
            print(LOG_MESSAGES["info_metrics_cached"].format(path=json_cache))
        except Exception:
            pass
