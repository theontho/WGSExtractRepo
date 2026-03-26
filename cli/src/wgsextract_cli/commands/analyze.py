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

    # 2. VCF Processing
    final_vcf = None
    if vcf_inputs:
        final_vcf = process_vcf_inputs(args, vcf_inputs, outdir)
    elif input_file and not args.skip_calling:
        final_vcf = call_variants(args, input_file, outdir)
    else:
        logging.warning("No VCF inputs and calling skipped or not possible.")

    # 3. Annotation & Discovery
    if final_vcf:
        run_discovery_chain(args, final_vcf, outdir)


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


def process_vcf_inputs(args, vcf_inputs, outdir):
    """Merges multiple VCFs if necessary."""
    if len(vcf_inputs) == 1:
        return ensure_vcf_prepared(vcf_inputs[0])

    logging.info(
        LOG_MESSAGES["analyze_vcf_merge"].format(
            count=len(vcf_inputs), output="merged.vcf.gz"
        )
    )

    prepared_vcfs = [ensure_vcf_prepared(v) for v in vcf_inputs]
    merged_vcf = os.path.join(outdir, "merged.vcf.gz")

    try:
        # Use bcftools concat -a to combine SNV, CNV, SV records for the same individual
        # --allow-overlaps handles cases where different callers report at the same position
        # and we want to keep both for annotation.
        subprocess.run(
            ["bcftools", "concat", "-a", "--allow-overlaps", "-Oz", "-o", merged_vcf]
            + prepared_vcfs,
            check=True,
        )
        ensure_vcf_indexed(merged_vcf)
        return merged_vcf
    except subprocess.CalledProcessError as e:
        logging.error(f"VCF concatenation failed: {e}")
        # Fallback to merge if concat fails? Or just return first?
        # Concatenation is usually better for SNV + CNV + SV from the same person.
        return prepared_vcfs[0]


def call_variants(args, input_file, outdir):
    """Calls SNPs and InDels if no VCF is provided."""
    logging.info("Step 2: No VCF provided. Calling SNPs and InDels...")

    # Use bcftools as default fast caller
    snps_vcf = os.path.join(outdir, "snps.vcf.gz")
    run_cli_subcommand(["vcf", "snp", "--input", input_file, "--outdir", outdir], args)

    indels_vcf = os.path.join(outdir, "indels.vcf.gz")
    run_cli_subcommand(
        ["vcf", "indel", "--input", input_file, "--outdir", outdir], args
    )

    # Merge them
    return process_vcf_inputs(args, [snps_vcf, indels_vcf], outdir)


def run_discovery_chain(args, vcf_file, outdir):
    """Annotates and filters for significant variants."""
    logging.info("Step 3: Annotating and searching for significant variants...")

    # 1. Chained Annotation (standard set)
    # clinvar,revel,phylop,gnomad,spliceai,alphamissense,pharmgkb
    ann_vcf = os.path.join(outdir, "chain_annotated.vcf.gz")
    run_cli_subcommand(
        [
            "vcf",
            "chain-annotate",
            "--input",
            vcf_file,
            "--outdir",
            outdir,
            "--annotations",
            "clinvar,revel,phylop,gnomad,spliceai,alphamissense,pharmgkb",
        ],
        args,
    )

    if not os.path.exists(ann_vcf):
        logging.error("Annotation chain failed to produce output.")
        return

    # 2. Discovery / Significant Filtering
    logging.info(LOG_MESSAGES["analyze_discovery_start"])

    discovery_vcf = os.path.join(outdir, "significant_variants.vcf.gz")

    # Dynamically build filter expression based on what's in the header
    # (prevents crashes if some annotation steps were skipped)
    try:
        res_h = subprocess.run(
            ["bcftools", "view", "-h", ann_vcf],
            capture_output=True,
            text=True,
            check=True,
        )
        header = res_h.stdout
    except Exception as e:
        logging.error(f"Failed to read VCF header: {e}")
        header = ""

    filters = []
    # Rare (check both GNOMAD_AF and AF)
    if "ID=GNOMAD_AF," in header:
        filters.append('INFO/GNOMAD_AF < 0.01 || INFO/GNOMAD_AF == "."')
    elif "ID=AF," in header:
        filters.append('INFO/AF < 0.01 || INFO/AF == "."')

    # Pathogenic
    if "ID=CLNSIG," in header:
        filters.append('INFO/CLNSIG ~ "Pathogenic"')

    # Impactful
    if "ID=REVEL," in header:
        filters.append("INFO/REVEL > 0.7")
    if "ID=SpliceAI," in header:
        filters.append('INFO/SpliceAI ~ "|0.[89]"')
    if "ID=am_pathogenicity," in header:
        filters.append("INFO/am_pathogenicity > 0.7")

    if not filters:
        logging.warning(
            "No annotation tags found in header for significant variant filtering."
        )
        # If no tags, maybe just keep everything or common filters?
        filter_expr = "QUAL > 30"  # Very basic fallback
    else:
        filter_expr = " || ".join(filters)

    logging.debug(f"Discovery filter expression: {filter_expr}")

    try:
        subprocess.run(
            [
                "bcftools",
                "filter",
                "-i",
                filter_expr,
                "-Oz",
                "-o",
                discovery_vcf,
                ann_vcf,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        ensure_vcf_indexed(discovery_vcf)

        # Count significant
        res = subprocess.run(
            ["bcftools", "view", "-H", discovery_vcf], capture_output=True, text=True
        )
        count = len(res.stdout.strip().split("\n")) if res.stdout.strip() else 0

        logging.info(
            LOG_MESSAGES["analyze_discovery_complete"].format(
                count=count, output=discovery_vcf
            )
        )

    except subprocess.CalledProcessError as e:
        logging.error(f"Discovery filtering failed: {e}")


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
        # but the sub-commands usually log their own ℹ️ messages which we've silenced.
        # Actually, for 'info' it prints a table to stdout.
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
