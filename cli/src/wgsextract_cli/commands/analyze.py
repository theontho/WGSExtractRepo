import copy
import csv
import json
import logging
import os
import subprocess
import sys
from datetime import datetime

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    ensure_vcf_indexed,
    ensure_vcf_prepared,
    get_resource_defaults,
    resolve_reference,
    run_command,
    verify_paths_exist,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "analyze", help=CLI_HELP.get("cmd_analyze", "Analyze genomic data.")
    )
    analyze_subs = parser.add_subparsers(dest="analyze_cmd", required=True)

    comp_parser = analyze_subs.add_parser(
        "comprehensive",
        parents=[base_parser],
        help=CLI_HELP.get("cmd_comprehensive", "Full-chain analysis."),
    )
    comp_parser.add_argument(
        "--vcf-inputs",
        nargs="+",
        help=CLI_HELP.get("arg_vcf_inputs", "Multiple VCF files."),
    )
    comp_parser.add_argument(
        "--skip-calling",
        action="store_true",
        help="Skip variant calling if --vcf-inputs is missing (fail instead).",
    )
    comp_parser.add_argument(
        "--batch",
        help=CLI_HELP.get("arg_batch", "Batch file for multiple samples."),
    )
    comp_parser.set_defaults(func=cmd_comprehensive)

    gen_batch_parser = analyze_subs.add_parser(
        "batch-gen",
        parents=[base_parser],
        help=CLI_HELP.get("cmd_batch_gen", "Generate a batch file from a directory."),
    )
    gen_batch_parser.add_argument(
        "--directory",
        required=True,
        help=CLI_HELP.get("arg_directory", "Directory to scan."),
    )
    gen_batch_parser.add_argument(
        "--output",
        default="batch.csv",
        help="Output batch file path.",
    )
    gen_batch_parser.set_defaults(func=cmd_batch_gen)


def cmd_comprehensive(args):
    verify_dependencies(["bcftools", "samtools", "tabix"])
    log_dependency_info(["bcftools", "samtools", "tabix"])

    batch_file = args.batch if args.batch else os.environ.get("WGSE_BATCH")
    if batch_file:
        run_batch_comprehensive(args, batch_file)
        return

    input_file = args.input
    vcf_inputs = args.vcf_inputs if args.vcf_inputs else []
    env_vcf = os.environ.get("WGSE_VCF_INPUTS")
    if not vcf_inputs and env_vcf:
        vcf_inputs = env_vcf.split()

    if not input_file and not vcf_inputs:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    # Pre-flight Validation
    paths_to_verify = {}
    if input_file:
        paths_to_verify["--input"] = input_file
    for i, v in enumerate(vcf_inputs):
        paths_to_verify[f"vcf-input-{i}"] = v

    if not verify_paths_exist(paths_to_verify):
        sys.exit(1)

    outdir = args.outdir if args.outdir else os.getcwd()
    os.makedirs(outdir, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🚀 STAGE: Starting Comprehensive Analysis ({now})")
    print(f"📂 Output Directory: {outdir}")

    print("-" * 60)

    # 1. BAM/CRAM Analysis (Info, QC, Lineage)
    gender = "Unknown"
    if input_file:
        gender = run_bam_chain(args, input_file, outdir)

    # 2. VCF Processing (Independently per type)
    results = []
    if vcf_inputs:
        print(f"\n🚀 STAGE: Processing Input VCFs ({len(vcf_inputs)} files)")
        for vcf in vcf_inputs:
            v_type = detect_vcf_type(vcf)
            res = run_vcf_workflow(args, vcf, v_type, outdir)
            if res:
                results.append(res)
    elif input_file and not args.skip_calling:
        print("\n🚀 STAGE: Variant Calling (No input VCFs provided)")
        # Call SNV and InDels if nothing else provided
        snps_vcf = os.path.join(outdir, "snps.vcf.gz")
        run_cli_subcommand(
            ["vcf", "snp", "--input", input_file, "--outdir", outdir], args
        )

        indels_vcf = os.path.join(outdir, "indels.vcf.gz")
        run_cli_subcommand(
            ["vcf", "indel", "--input", input_file, "--outdir", outdir], args
        )

        for vcf, v_type in [(snps_vcf, "snp-indel"), (indels_vcf, "snp-indel")]:
            if os.path.exists(vcf):
                res = run_vcf_workflow(args, vcf, v_type, outdir)
                if res:
                    results.append(res)

    # 3. Final Summary Report
    generate_summary_report(results, outdir)


def run_batch_comprehensive(args, batch_file):
    """Runs comprehensive analysis for multiple samples defined in batch_file."""

    if not os.path.exists(batch_file):
        logging.error(f"Batch file not found: {batch_file}")
        sys.exit(1)

    with open(batch_file) as f:
        # Detect delimiter (CSV or TSV)
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.seek(0)
        reader = csv.DictReader(f, dialect=dialect)

        # Map header names flexibly
        headers = reader.fieldnames or []
        name_col = next(
            (c for c in headers if c.lower() in ["name", "sample", "id"]), "name"
        )
        input_col = next(
            (c for c in headers if c.lower() in ["input", "bam", "cram"]), "input"
        )
        vcf_col = next((c for c in headers if "vcf" in c.lower()), "vcf")

        for row in reader:
            name = row.get(name_col, "Unknown")
            input_path = row.get(input_col)
            vcf_paths = row.get(vcf_col, "")

            # Clean up vcf_paths - handle comma or space separated
            vcf_list = []
            if vcf_paths:
                vcf_list = [
                    v.strip()
                    for v in vcf_paths.replace(",", ";").split(";")
                    if v.strip()
                ]

            print("\n" + "#" * 80)
            print(f"### BATCH PROCESSING: {name}")
            print("#" * 80)

            # Create sample-specific outdir
            sample_outdir = os.path.join(
                args.outdir if args.outdir else os.getcwd(), name
            )
            os.makedirs(sample_outdir, exist_ok=True)

            # Build dummy args for this sample
            sample_args = copy.deepcopy(args)
            sample_args.input = input_path
            sample_args.vcf_inputs = vcf_list
            sample_args.outdir = sample_outdir
            sample_args.batch = None  # Prevent recursion

            try:
                cmd_comprehensive(sample_args)
            except Exception as e:
                logging.error(f"Failed to process sample {name}: {e}")


def cmd_batch_gen(args):
    """Generates a batch file by scanning a directory."""
    scan_dir = args.directory
    if not os.path.exists(scan_dir):
        logging.error(f"Directory not found: {scan_dir}")
        sys.exit(1)

    print(f"🔍 Scanning directory: {scan_dir}")

    samples: dict[str, dict] = {}  # name -> {input, vcfs}

    for root, _, files in os.walk(scan_dir):
        for f in files:
            full_path = os.path.abspath(os.path.join(root, f))
            lower_f = f.lower()

            # Heuristic: sample1.bam -> name sample1
            # sample1.vcf.gz -> name sample1
            # Strip common suffixes for better grouping
            def clean_name(n):
                # Strip all extensions first
                name = n
                while "." in name:
                    base, ext = os.path.splitext(name)
                    if ext.lower() in [
                        ".vcf",
                        ".gz",
                        ".bam",
                        ".cram",
                        ".tbi",
                        ".csi",
                        ".bai",
                        ".crai",
                    ]:
                        name = base
                    else:
                        break

                # Strip common genomic suffixes
                for suffix in [
                    "_snp",
                    "_sv",
                    "_indel",
                    "_cnv",
                    ".snp",
                    ".sv",
                    ".indel",
                    ".cnv",
                    "_metrics",
                    "_info",
                ]:
                    if name.lower().endswith(suffix):
                        name = name[: -len(suffix)]

                return name

            if lower_f.endswith((".bam", ".cram")):
                name = clean_name(f)
                if name not in samples:
                    samples[name] = {"input": None, "vcfs": []}
                samples[name]["input"] = full_path

            elif lower_f.endswith((".vcf.gz", ".vcf")):
                # Avoid adding indexes as VCFs
                if not lower_f.endswith((".tbi", ".csi")):
                    name = clean_name(f)
                    if name not in samples:
                        samples[name] = {"input": None, "vcfs": []}
                    samples[name]["vcfs"].append(full_path)

    if not samples:
        logging.warning("No genomic files found in the directory.")
        return

    output_path = args.output
    print(f"✍️ Writing batch file to: {output_path}")

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "input", "vcf"])
        for name, data in sorted(samples.items()):
            vcf_str = ";".join(data["vcfs"])
            writer.writerow([name, data["input"] or "", vcf_str])

    print(f"✅ Generated batch file with {len(samples)} samples.")


def detect_vcf_type(vcf_path):
    """Simple heuristic to detect SNV, CNV, or SV."""
    fname = os.path.basename(vcf_path).lower()
    if "cnv" in fname:
        return "cnv"
    if "sv" in fname:
        return "sv"
    return "snp-indel"


def run_vcf_workflow(args, vcf_path, v_type, outdir):
    """Annotates and filters a single VCF file based on its type."""
    base_name = os.path.basename(vcf_path).split(".")[0]
    print(f"\n🔹 Sub-Stage: Processing {v_type.upper()} ({os.path.basename(vcf_path)})")

    # Define targeted annotations per type
    if v_type == "snp-indel":
        # Full chain for SNPs, now including VEP
        anns = "clinvar,revel,phylop,gnomad,spliceai,alphamissense,pharmgkb,vep"
    elif v_type == "cnv":
        # ClinVar and gnomAD are most relevant for CNVs
        anns = "clinvar,gnomad"
    else:  # SV
        anns = "clinvar,gnomad"

    work_dir = os.path.join(outdir, f"work_{v_type}_{base_name}")
    os.makedirs(work_dir, exist_ok=True)

    run_cli_subcommand(
        [
            "vcf",
            "chain-annotate",
            "--input",
            vcf_path,
            "--outdir",
            work_dir,
            "--annotations",
            anns,
        ],
        args,
    )

    # Locate the final annotated file
    actual_ann_vcf = os.path.join(work_dir, "chain_annotated.vcf.gz")
    if not os.path.exists(actual_ann_vcf):
        logging.warning(f"Annotation failed for {vcf_path}")
        return None

    # Run Discovery Filter
    discovery_vcf = os.path.join(outdir, f"significant_{v_type}_{base_name}.vcf.gz")
    count = run_discovery_filter(args, actual_ann_vcf, v_type, discovery_vcf)

    return {"type": v_type, "input": vcf_path, "output": discovery_vcf, "count": count}


def run_discovery_filter(args, ann_vcf, v_type, out_vcf):
    """Dynamically builds filter based on type and headers."""
    try:
        res_h = subprocess.run(
            ["bcftools", "view", "-h", ann_vcf],
            capture_output=True,
            text=True,
            check=True,
        )
        header = res_h.stdout
    except Exception:
        header = ""

    # Build Logic: Rare OR Pathogenic OR High Impact
    filters = []

    # Rare
    if "ID=GNOMAD_AF," in header:
        filters.append('INFO/GNOMAD_AF < 0.01 || INFO/GNOMAD_AF == "."')
    elif "ID=AF," in header:
        filters.append('INFO/AF < 0.01 || INFO/AF == "."')

    # Pathogenic
    if "ID=CLNSIG," in header:
        filters.append('INFO/CLNSIG ~ "Pathogenic"')

    if v_type == "snp-indel":
        if "ID=REVEL," in header:
            filters.append("INFO/REVEL > 0.7")
        if "ID=SpliceAI," in header:
            filters.append('INFO/SpliceAI ~ "|0.[89]"')
        if "ID=am_pathogenicity," in header:
            filters.append("INFO/am_pathogenicity > 0.7")

    # Combine with OR
    if filters:
        filter_expr = " || ".join(filters)
    else:
        filter_expr = "QUAL > 30"

    print(f"🔍 Applying Discovery Filter: {filter_expr}")

    try:
        subprocess.run(
            ["bcftools", "filter", "-i", filter_expr, "-Oz", "-o", out_vcf, ann_vcf],
            capture_output=True,
            text=True,
            check=True,
        )
        ensure_vcf_indexed(out_vcf)
        res = subprocess.run(
            ["bcftools", "view", "-H", out_vcf], capture_output=True, text=True
        )
        count = len(res.stdout.strip().split("\n")) if res.stdout.strip() else 0
        print(f"✅ Found {count} significant variants.")
        return count
    except Exception as e:
        logging.error(f"Discovery filter failed for {v_type}: {e}")
        return 0


def generate_summary_report(results, outdir):
    """Prints a nice summary of all findings."""
    print("\n" + "=" * 60)
    print("GENOMIC ANALYSIS SUMMARY REPORT")
    print("=" * 60)

    total_sig = 0
    for res in results:
        print(f"[{res['type'].upper()}] {os.path.basename(res['input'])}")
        print(f"  Significant variants: {res['count']}")
        print(f"  Results file: {res['output']}")
        total_sig += res["count"]
        print("-" * 30)

    print(f"\nTOTAL SIGNIFICANT VARIANTS FOUND: {total_sig}")
    print("=" * 60 + "\n")


def run_bam_chain(args, input_file, outdir):
    """Runs info, qc, and lineage steps. Returns detected gender."""
    print("\n🚀 STAGE: BAM/CRAM Metrics & Lineage")

    # 1. Info (Detailed run to show table and get gender)
    # We call it even if cached to ensure the table is displayed. It's very fast when cached.
    run_cli_subcommand(
        ["info", "--detailed", "--input", input_file, "--outdir", outdir], args
    )

    # 2. Detect gender from the (newly updated) cache to drive subsequent logic
    gender = "Unknown"
    cache_file = os.path.join(outdir, f"{os.path.basename(input_file)}.wgse_info.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
                gender = data.get("gender", "Unknown")
        except Exception:
            pass

    # 3. mt-haplogroup (Haplogrep)
    run_cli_subcommand(
        ["lineage", "mt-haplogroup", "--input", input_file, "--outdir", outdir], args
    )

    # 4. Y-lineage only if it's NOT female
    if gender != "Female":
        run_cli_subcommand(
            ["lineage", "y-haplogroup", "--input", input_file, "--outdir", outdir], args
        )
    else:
        logging.info("Skipping Y-lineage analysis for female genome.")

    return gender


def run_cli_subcommand(cmd_args, args):
    """Helper to run a wgsextract subcommand."""
    cmd = ["uv", "run", "wgsextract"] + cmd_args

    # Use explicit ref if provided, otherwise resolve from env/defaults
    ref_path = args.ref
    if not ref_path:
        # Try to resolve for BAM/CRAM inputs
        input_path = args.input
        md5_sig = (
            calculate_bam_md5(input_path, None)
            if input_path and input_path.lower().endswith((".bam", ".cram"))
            else None
        )
        lib = ReferenceLibrary(None, md5_sig, input_path=input_path)
        ref_path = lib.root

    if ref_path:
        cmd.extend(["--ref", ref_path])

    if args.threads:
        cmd.extend(["--threads", str(args.threads)])
    if args.debug:
        cmd.append("--debug")
    if getattr(args, "force", False):
        cmd.append("--force")

    try:
        # For curated commands, we want real-time output to show progress/results.
        # For everything else, we capture to keep the UI clean.
        curated_cmds = ["info", "lineage", "vcf", "vep"]
        should_stream = any(c in cmd_args for c in curated_cmds)

        if should_stream:
            # Run without capturing to allow real-time progress updates to reach the terminal.
            # Internal sub-sub-commands (like bcftools) are still captured at their level.
            subprocess.run(cmd, check=True)
        else:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

    except subprocess.CalledProcessError as e:
        logging.warning(f"Subcommand failed: {' '.join(cmd)}. Error: {e}")
        if e.stderr:
            logging.error(e.stderr)
