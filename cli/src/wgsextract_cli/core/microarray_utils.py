import os
import logging
import subprocess
from pyliftover import LiftOver

def chr_to_int(chrom):
    """
    Converts chromosome name to an integer for sorting.
    M/MT -> 23, X -> 24, Y -> 25.
    Ported from program/aconv.py chrconv().
    """
    c = str(chrom).upper().replace("CHR", "")
    if c == "M" or c == "MT":
        return 23
    if c == "X":
        return 24
    if c == "Y":
        return 25
    try:
        return int(c)
    except ValueError:
        return 99 # Unknown

def sort_microarray_file(input_file, output_file):
    """
    Sorts a microarray TSV file by chromosome and position.
    """
    data = []
    header = []
    with open(input_file, "r") as f:
        for line in f:
            if line.startswith("#"):
                header.append(line)
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                data.append(parts)
    
    # Sort by chromosome (using chr_to_int) and then position
    data.sort(key=lambda x: (chr_to_int(x[1]), int(x[2])))
    
    with open(output_file, "w") as f:
        for line in header:
            f.write(line)
        for parts in data:
            f.write("\t".join(parts) + "\n")

def liftover_hg38_to_hg19(input_txt, output_txt, chain_file, templates_dir=None):
    """
    Performs liftover from hg38 to hg19 using pyliftover.
    Ported from legacy program/hg38tohg19.py.
    """
    if not os.path.exists(chain_file):
        raise FileNotFoundError(f"Liftover chain file not found: {chain_file}")

    lo = LiftOver(chain_file)
    bad_chrom = 0
    bad_pos = 0
    
    # Primary 25 sequences as in legacy code
    valid_chroms = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]

    # Use a temporary file for unsorted liftover results
    tmp_txt = output_txt + ".tmp"
    
    with open(tmp_txt, "w") as f_sink:
        with open(input_txt, "r") as f_source:
            for line in f_source:
                if line.startswith('#'):
                    continue
                
                parts = line.strip().split("\t")
                if len(parts) < 4:
                    continue
                
                snp_id, chrom, pos, result = parts[0], parts[1], parts[2], parts[3]
                
                # Normalize chromosome name for pyliftover
                old_chrom = ("chr" + chrom).replace("chrMT", "chrM")
                
                try:
                    new_coord = lo.convert_coordinate(old_chrom, int(pos))
                except (ValueError, TypeError):
                    continue

                if new_coord:
                    new_chrom = new_coord[0][0]
                    new_pos = new_coord[0][1]
                    
                    if new_chrom in valid_chroms:
                        # Normalize back to legacy format (no 'chr', M->MT)
                        out_chrom = new_chrom.replace("chrM", "MT").replace("chr", "")
                        f_sink.write(f"{snp_id}\t{out_chrom}\t{new_pos}\t{result}\n")
                    else:
                        bad_chrom += 1
                else:
                    bad_pos += 1
    
    if bad_chrom or bad_pos:
        logging.warning(f"Liftover partially failed: {bad_chrom} to AltContig, {bad_pos} not in new model")

    # Now sort the temporary file and add the header if templates_dir is provided
    header = []
    if templates_dir:
        head_v3 = os.path.join(templates_dir, "head", "23andMe_V3.txt")
        if os.path.exists(head_v3):
            with open(head_v3, "r") as f_h:
                header = f_h.readlines()
    
    data = []
    with open(tmp_txt, "r") as f:
        for line in f:
            data.append(line.strip().split("\t"))
    
    data.sort(key=lambda x: (chr_to_int(x[1]), int(x[2])))
    
    with open(output_txt, "w") as f:
        f.writelines(header)
        for parts in data:
            f.write("\t".join(parts) + "\n")
    
    if os.path.exists(tmp_txt):
        os.remove(tmp_txt)

def get_template_format(format_name):
    """Returns metadata for known microarray formats."""
    # Ported from legacy program/aconv.py logic
    formats = {
        "23andMe_V3": {"suffix": ".txt", "parts": 1},
        "23andMe_V4": {"suffix": ".txt", "parts": 2},
        "23andMe_V5": {"suffix": ".txt", "parts": 2},
        "Ancestry_V1": {"suffix": ".txt", "parts": 4},
        "Ancestry_V2": {"suffix": ".txt", "parts": 5},
        "FTDNA_V3": {"suffix": ".csv", "parts": 3},
        "MyHeritage_V1": {"suffix": ".csv", "parts": 1},
        "MyHeritage_V2": {"suffix": ".csv", "parts": 1},
        "23andMe_SNPs_API": {"suffix": ".txt", "parts": 1},
        "23andMe_V35": {"suffix": ".txt", "parts": 1},
        "LDNA_V1": {"suffix": ".txt", "parts": 1},
        "LDNA_V2": {"suffix": ".txt", "parts": 1},
    }
    return formats.get(format_name)

def write_formatted_line(f, format_name, snp_id, chrom, pos, result):
    """Writes a line in the specific vendor format. Ported from aconv.py."""
    
    if "Ancestry" in format_name:
        if result == "--": result = "00"
        # Ancestry expects tab separated alleles
        if len(result) == 2:
            val = f"{result[0]}\t{result[1]}"
        else:
            val = "0\t0" # Fallback
        f.write(f"{snp_id}\t{chrom}\t{pos}\t{val}\n")
    
    elif "23andMe" in format_name or format_name == "23andMe_SNPs_API":
        chrom = chrom.replace("M", "MT")
        f.write(f"{snp_id}\t{chrom}\t{pos}\t{result}\n")
    
    elif format_name in ["FTDNA_V1_Affy", "MyHeritage_V2", "MyHeritage_V1"]:
        # MyHeritage V1 specific genotype swap
        if format_name == "MyHeritage_V1":
            if result == "CT": result = "TC"
            elif result == "GT": result = "TG"
        f.write(f'"{snp_id}","{chrom}","{pos}","{result}"\n')
    
    elif format_name == "FTDNA_V2":
        f.write(f'"{snp_id}","{chrom}","{pos}","{result}"\n')

    elif format_name == "FTDNA_V3":
        f.write(f"{snp_id},{chrom},{pos},{result}\n")
    
    else:
        # Generic fallback
        f.write(f"{snp_id}\t{chrom}\t{pos}\t{result}\n")

def convert_to_vendor_format(format_name, combined_kit_txt, output_path, templates_dir):
    """
    Converts a CombinedKit.txt to a vendor-specific format using templates.
    Ported from legacy program/aconv.py.
    """
    fmt_info = get_template_format(format_name)
    if not fmt_info:
        logging.warning(f"Unknown format: {format_name}, using generic fallback.")
        fmt_info = {"suffix": ".txt", "parts": 1}
    
    # Resolve the actual templates root
    if os.path.isdir(os.path.join(templates_dir, "raw_file_templates")):
        templates_root = os.path.join(templates_dir, "raw_file_templates")
    elif os.path.basename(templates_dir.rstrip(os.sep)) == "raw_file_templates":
        templates_root = templates_dir
    else:
        templates_root = templates_dir # Fallback

    # Load all called variants into memory for fast lookup
    called_variants = {}
    with open(combined_kit_txt, "r") as f:
        for line in f:
            if line.startswith('#'): continue
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                # Key is (chrom, pos)
                called_variants[(str(parts[1]), str(parts[2]))] = parts[3]

    # Handle multiple parts (concatenated at the end)
    temp_files = []
    for i in range(1, fmt_info["parts"] + 1):
        part_suffix = f"_{i}" if fmt_info["parts"] > 1 else ""
        template_name = f"{format_name}{part_suffix}{fmt_info['suffix']}"
        body_template = os.path.join(templates_root, "body", template_name)
        
        part_out = output_path + f".part{i}"
        temp_files.append(part_out)
        
        with open(part_out, "w") as f_out:
            if not os.path.exists(body_template):
                logging.warning(f"Template body not found: {body_template}")
                continue

            with open(body_template, "r") as f_temp:
                for line in f_temp:
                    line = line.strip().replace('"', '')
                    if not line: continue
                    
                    # Parse template line
                    parts = line.split(",") if fmt_info["suffix"] == ".csv" else line.split("\t")
                    if len(parts) < 3: continue
                    
                    # Templates are usually: ID, CHROM, POS
                    t_id, t_chrom, t_pos = parts[0], parts[1], parts[2]

                    # Lookup called result
                    result = called_variants.get((str(t_chrom), str(t_pos)), "--")
                    if "Ancestry" in format_name and result == "--":
                        result = "00"
                    
                    write_formatted_line(f_out, format_name, t_id, t_chrom, t_pos, result)

    # Concatenate parts and add header
    head_template = os.path.join(templates_root, "head", f"{format_name}{fmt_info['suffix']}")
    with open(output_path, "wb") as f_final:
        if os.path.exists(head_template):
            with open(head_template, "rb") as f_h:
                f_final.write(f_h.read())
        
        for part_file in temp_files:
            if os.path.exists(part_file):
                with open(part_file, "rb") as f_p:
                    f_final.write(f_p.read())
                os.remove(part_file)
