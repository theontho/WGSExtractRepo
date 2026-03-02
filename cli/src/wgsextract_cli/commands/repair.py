import sys
import os

def register(subparsers):
    parser = subparsers.add_parser("repair", help="Repair formatting violations in FTDNA files.")
    repair_subs = parser.add_subparsers(dest="repair_cmd", required=True)
    
    bam_parser = repair_subs.add_parser("ftdna-bam", help="Fix QNAME spaces in FTDNA BigY BAM files (reads/writes SAM on stdin/stdout).")
    bam_parser.set_defaults(func=repair_bam)
    
    vcf_parser = repair_subs.add_parser("ftdna-vcf", help="Fix FILTER column in FTDNA BigY VCF files (reads/writes VCF on stdin/stdout).")
    vcf_parser.set_defaults(func=repair_vcf)

def repair_bam(args):
    # We assume called in a pipeline with samtools -h view used to pass in complete SAM on stdin; filtered SAM on stdout
    header = True
    for line in sys.stdin:
        if header:
            if line[0] == '@':
                os.write(1, str.encode(line))
                continue
            else:
                header = False

        fields = line.split('\t')
        fields[0] = fields[0].replace(" ",":")
        line = '\t'.join(fields)
        os.write(1, str.encode(line))

def repair_vcf(args):
    # We assume called in a pipeline with bcftools view used to pass in complete VCF on stdin; filtered output on stdout
    header = True
    format_found = False
    info_found = False
    
    for line in sys.stdin:
        if header and line[0] == '#':
            if not format_found and "##FORMAT=<ID" in line:
                os.write(1, b'##FILTER=<ID=PASS,Description="Passed all filters">\n')
                os.write(1, b'##FILTER=<ID=DP1,Description="Single Read">\n')
                os.write(1, b'##FILTER=<ID=DPM,Description="More than 750 reads">\n')
                os.write(1, b'##FILTER=<ID=Q40,Description="Quality below 40">\n')
                os.write(1, b'##FILTER=<ID=GTL,Description="?">\n')
                format_found = True
            if not info_found and "##INFO=<ID" in line:
                os.write(1, b'##INFO=<ID=HG,Number=1,Type=String,Description="Haplogroup if sample is derived">\n')
                os.write(1, b'##INFO=<ID=ISOGG,Number=1,Type=String,Description="ISOGG Haplogroup if sample is derived">\n')
                info_found = True
            if "#CHROM" in line:
                header = False
            os.write(1, str.encode(line))
            continue

        fields = line.split('\t')
        if len(fields) > 6 and "PASS" == fields[6]:
            os.write(1, str.encode(line))
            continue

        if len(fields) > 6:
            entries = fields[6].split(";")
            for i in range(len(entries)):
                entries[i] = "DP1" if "DP=1"  == entries[i] else \
                             "DPM" if "DP="   in entries[i] else \
                             "GTL" if "GTL="  in entries[i] else \
                             "Q40" if "QUAL=" in entries[i] else ""
            entries = [e for e in entries if e]
            fields[6] = ";".join(entries) if entries else "."
            line = '\t'.join(fields)
            
        os.write(1, str.encode(line))
