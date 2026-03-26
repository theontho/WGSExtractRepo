import json
import logging
import os
import subprocess
import sys

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ensure_vcf_indexed,
    ensure_vcf_prepared,
    get_resource_defaults,
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
    comp_parser.set_defaults(func=cmd_comprehensive)


def cmd_comprehensive(args):
    verify_dependencies(["bcftools", "samtools", "tabix"])
    log_dependency_info(["bcftools", "samtools", "tabix"])

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

    logging.info(
        LOG_MESSAGES["analyze_comprehensive_start"].format(
            input=input_file or ", ".join(vcf_inputs)
        )
    )

    # 1. BAM/CRAM Analysis (Info, QC, Lineage)
    gender = "Unknown"
    if input_file:
        gender = run_bam_chain(args, input_file, outdir)

    # 2. VCF Processing (Independently per type)
    results = []
    if vcf_inputs:
        for vcf in vcf_inputs:
            v_type = detect_vcf_type(vcf)
            res = run_vcf_workflow(args, vcf, v_type, outdir)
            if res:
                results.append(res)
    elif input_file and not args.skip_calling:
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
    logging.info(f"Processing {v_type.upper()} VCF: {vcf_path}")

    # Define targeted annotations per type
    if v_type == "snp-indel":
        # Full chain for SNPs
        anns = "clinvar,revel,phylop,gnomad,spliceai,alphamissense,pharmgkb"
    elif v_type == "cnv":
        # ClinVar and gnomAD (SV) are most relevant for CNVs
        anns = "clinvar,gnomad"
    else:  # SV
        anns = "clinvar,gnomad"

    work_dir = os.path.join(outdir, f"work_{v_type}_{base_name}")
    os.makedirs(work_dir, exist_ok=True)

    ann_vcf = os.path.join(work_dir, f"{base_name}_annotated.vcf.gz")

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

    # Locate the final annotated file (chain-annotate puts it in outdir)
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

    filters = []
    if v_type == "snp-indel":
        if "ID=GNOMAD_AF," in header:
            filters.append('INFO/GNOMAD_AF < 0.01 || INFO/GNOMAD_AF == "."')
        elif "ID=AF," in header:
            filters.append('INFO/AF < 0.01 || INFO/AF == "."')

        if "ID=CLNSIG," in header:
            filters.append('INFO/CLNSIG ~ "Pathogenic"')

        if "ID=REVEL," in header:
            filters.append("INFO/REVEL > 0.7")
        if "ID=SpliceAI," in header:
            filters.append('INFO/SpliceAI ~ "|0.[89]"')
        if "ID=am_pathogenicity," in header:
            filters.append("INFO/am_pathogenicity > 0.7")

    elif v_type in ["cnv", "sv"]:
        # For CNVs/SVs, we care about Pathogenicity or high population frequency overlaps?
        # Actually usually we want Pathogenic or very large/rare.
        if "ID=CLNSIG," in header:
            filters.append('INFO/CLNSIG ~ "Pathogenic"')
        # If no specific annotations, maybe just keep anything not PASS-filtered
        filters.append('FILTER == "PASS"')

    filter_expr = " || ".join(filters) if filters else "QUAL > 30"

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
        return len(res.stdout.strip().split("\n")) if res.stdout.strip() else 0
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
    logging.info("Step 1: Running BAM/CRAM basic metrics and QC...")

    # Info (Detailed run to get gender)
    run_cli_subcommand(
        ["info", "--detailed", "--input", input_file, "--outdir", outdir], args
    )

    # Detect gender from cache
    gender = "Unknown"
    cache_file = os.path.join(outdir, f"{os.path.basename(input_file)}.wgse_info.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                data = json.load(f)
                gender = data.get("gender", "Unknown")
                logging.info(f"Detected biological sex: {gender}")
        except Exception:
            pass

    # QC (coverage-sample)
    run_cli_subcommand(
        ["info", "coverage-sample", "--input", input_file, "--outdir", outdir], args
    )

    # Lineage (Y and MT)
    logging.info("Running lineage analysis...")
    run_cli_subcommand(
        ["lineage", "mt-haplogroup", "--input", input_file, "--outdir", outdir], args
    )

    # Y-lineage only if it's NOT female
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
    if args.ref:
        cmd.extend(["--ref", args.ref])
    if args.threads:
        cmd.extend(["--threads", str(args.threads)])
    if args.debug:
        cmd.append("--debug")

    try:
        # Capture output to prevent spam during comprehensive analysis
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # If it's a command that produces direct info output, we might want to see it
        if (
            "info" in cmd_args
            and "--detailed" in cmd_args
            and "coverage-sample" not in cmd_args
        ):
            print(res.stdout)
    except subprocess.CalledProcessError as e:
        logging.warning(f"Subcommand failed: {' '.join(cmd)}. Error: {e}")
        if e.stderr:
            logging.error(e.stderr)
