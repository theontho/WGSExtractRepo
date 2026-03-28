import logging
import os
import shutil
import subprocess
import sys

from wgsextract_cli.core.dependencies import (
    get_tool_path,
    log_dependency_info,
    verify_dependencies,
)
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    ensure_vcf_indexed,
    ensure_vcf_prepared,
    get_resource_defaults,
    get_sam_view_cmd,
    popen,
    run_command,
    verify_paths_exist,
)
from wgsextract_cli.core.warnings import print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "vcf",
        help="Variant calling and processing using bcftools, delly, or freebayes.",
    )
    vcf_subs = parser.add_subparsers(dest="vcf_cmd", required=True)

    snp_parser = vcf_subs.add_parser(
        "snp", parents=[base_parser], help=CLI_HELP["cmd_snp"]
    )

    snp_group = snp_parser.add_mutually_exclusive_group(required=False)
    snp_group.add_argument(
        "--ploidy-file",
        help="File defining ploidy per chromosome (auto-resolved from --ref if possible)",
    )
    snp_group.add_argument("--ploidy", help="Predefined ploidy name or value")
    snp_parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)"
    )
    snp_parser.set_defaults(func=cmd_snp)

    indel_parser = vcf_subs.add_parser(
        "indel", parents=[base_parser], help=CLI_HELP["cmd_indel"]
    )
    indel_group = indel_parser.add_mutually_exclusive_group(required=False)
    indel_group.add_argument(
        "--ploidy-file",
        help="File defining ploidy per chromosome (auto-resolved from --ref if possible)",
    )
    indel_group.add_argument("--ploidy", help="Predefined ploidy name or value")
    indel_parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)"
    )
    indel_parser.set_defaults(func=cmd_indel)

    annotate_parser = vcf_subs.add_parser(
        "annotate", parents=[base_parser], help=CLI_HELP["cmd_annotate"]
    )
    annotate_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help=CLI_HELP["arg_vcf_input"],
    )
    annotate_parser.add_argument(
        "--ann-vcf", help="Annotation VCF file (auto-resolved from --ref if possible)"
    )
    annotate_parser.add_argument("--cols", help="Columns to annotate (e.g. ID,INFO/HG)")
    annotate_parser.set_defaults(func=cmd_annotate)

    filter_parser = vcf_subs.add_parser(
        "filter", parents=[base_parser], help=CLI_HELP["cmd_filter"]
    )
    filter_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help=CLI_HELP["arg_vcf_input"],
    )
    filter_parser.add_argument(
        "--expr", help="bcftools filter expression (e.g. 'QUAL>30')"
    )
    filter_parser.add_argument("--gene", help="Filter by Gene Name (e.g. BRCA1, KCNQ2)")
    filter_parser.add_argument(
        "--exclude-near-gaps",
        action="store_true",
        help="Exclude variants in or near genomic gaps (requires Count Ns output)",
    )
    filter_parser.add_argument("-r", "--region", help="Chromosomal region")
    filter_parser.set_defaults(func=cmd_filter)

    trio_parser = vcf_subs.add_parser(
        "trio", parents=[base_parser], help=CLI_HELP["cmd_trio"]
    )
    trio_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help=CLI_HELP["arg_vcf_input"],
    )
    trio_parser.add_argument(
        "--mother",
        default=os.environ.get("WGSE_MOTHER_VCF"),
        help=CLI_HELP["arg_mother"],
    )
    trio_parser.add_argument(
        "--father",
        default=os.environ.get("WGSE_FATHER_VCF"),
        help=CLI_HELP["arg_father"],
    )
    trio_parser.add_argument("--proband", help="VCF file for the child")
    trio_parser.add_argument(
        "--mode",
        choices=["denovo", "recessive", "comphet", "all"],
        default="denovo",
        help="Inheritance mode to filter for",
    )
    trio_parser.add_argument("-r", "--region", help="Chromosomal region")
    trio_parser.set_defaults(func=cmd_trio)

    cnv_parser = vcf_subs.add_parser(
        "cnv", parents=[base_parser], help=CLI_HELP["cmd_cnv"]
    )
    cnv_parser.add_argument("-r", "--region", help="Chromosomal region")
    cnv_parser.add_argument(
        "-M", "--map", help="Mappability map file (required for delly cnv)"
    )
    cnv_parser.add_argument("--ploidy", help="Predefined ploidy name or value")
    cnv_parser.set_defaults(func=cmd_cnv)

    sv_parser = vcf_subs.add_parser(
        "sv", parents=[base_parser], help=CLI_HELP["cmd_sv"]
    )
    sv_parser.add_argument("-r", "--region", help="Chromosomal region")
    sv_parser.set_defaults(func=cmd_sv)

    freebayes_parser = vcf_subs.add_parser(
        "freebayes", parents=[base_parser], help=CLI_HELP["cmd_freebayes"]
    )
    freebayes_parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)"
    )
    freebayes_parser.set_defaults(func=cmd_freebayes)

    gatk_parser = vcf_subs.add_parser(
        "gatk", parents=[base_parser], help=CLI_HELP["cmd_gatk"]
    )
    gatk_parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM)")
    gatk_parser.set_defaults(func=cmd_gatk)

    deepvariant_parser = vcf_subs.add_parser(
        "deepvariant", parents=[base_parser], help=CLI_HELP["cmd_deepvariant"]
    )
    deepvariant_parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM)"
    )
    deepvariant_parser.add_argument(
        "--wes", action="store_true", help="Set model type to WES (default: WGS)"
    )
    deepvariant_parser.add_argument(
        "--checkpoint", help="Path to DeepVariant model checkpoint"
    )
    deepvariant_parser.set_defaults(func=cmd_deepvariant)

    clinvar_parser = vcf_subs.add_parser(
        "clinvar",
        parents=[base_parser],
        help="Annotate VCF with ClinVar pathogenicity data.",
    )
    clinvar_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    clinvar_parser.add_argument("--clinvar-file", help="Path to ClinVar VCF data file.")
    clinvar_parser.set_defaults(func=cmd_clinvar)

    revel_parser = vcf_subs.add_parser(
        "revel",
        parents=[base_parser],
        help="Annotate VCF with REVEL pathogenicity scores.",
    )
    revel_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    revel_parser.add_argument(
        "--revel-file", help="Path to REVEL TSV or VCF data file."
    )
    revel_parser.add_argument(
        "--min-score",
        type=float,
        help="Minimum REVEL score to filter for (e.g., 0.5).",
    )
    revel_parser.set_defaults(func=cmd_revel)

    phylop_parser = vcf_subs.add_parser(
        "phylop",
        parents=[base_parser],
        help="Annotate VCF with PhyloP conservation scores.",
    )
    phylop_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    phylop_parser.add_argument(
        "--phylop-file", help="Path to PhyloP TSV or VCF data file."
    )
    phylop_parser.add_argument(
        "--min-score",
        type=float,
        help="Minimum PhyloP score to filter for (e.g., 2.0).",
    )
    phylop_parser.set_defaults(func=cmd_phylop)

    gnomad_parser = vcf_subs.add_parser(
        "gnomad",
        parents=[base_parser],
        help="Annotate VCF with gnomAD population frequencies.",
    )
    gnomad_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    gnomad_parser.add_argument("--gnomad-file", help="Path to gnomAD VCF data file.")
    gnomad_parser.add_argument(
        "--max-af",
        type=float,
        help="Maximum Allele Frequency to filter for (e.g., 0.01 for 1%%).",
    )
    gnomad_parser.set_defaults(func=cmd_gnomad)

    spliceai_parser = vcf_subs.add_parser(
        "spliceai",
        parents=[base_parser],
        help="Annotate VCF with SpliceAI splicing scores.",
    )
    spliceai_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    spliceai_parser.add_argument(
        "--spliceai-file", help="Path to SpliceAI VCF data file."
    )
    spliceai_parser.set_defaults(func=cmd_spliceai)

    alphamissense_parser = vcf_subs.add_parser(
        "alphamissense",
        parents=[base_parser],
        help="Annotate VCF with AlphaMissense pathogenicity scores.",
    )
    alphamissense_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    alphamissense_parser.add_argument(
        "--am-file", help="Path to AlphaMissense VCF data file."
    )
    alphamissense_parser.add_argument(
        "--min-score",
        type=float,
        help="Minimum AlphaMissense score to filter for (e.g., 0.5).",
    )
    alphamissense_parser.set_defaults(func=cmd_alphamissense)

    pharmgkb_parser = vcf_subs.add_parser(
        "pharmgkb",
        parents=[base_parser],
        help="Annotate VCF with PharmGKB drug metabolism data.",
    )
    pharmgkb_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    pharmgkb_parser.add_argument(
        "--pharmgkb-file", help="Path to PharmGKB VCF or data file."
    )
    pharmgkb_parser.set_defaults(func=cmd_pharmgkb)

    chain_annotate_parser = vcf_subs.add_parser(
        "chain-annotate",
        parents=[base_parser],
        help="Sequentially apply multiple annotations to a single VCF.",
    )
    chain_annotate_parser.add_argument(
        "--vcf-input", help="Optional override for VCF input file."
    )
    chain_annotate_parser.add_argument(
        "--annotations",
        default="clinvar,revel,phylop,gnomad,vep",
        help="Comma-separated list of annotations to apply in order (default: clinvar,revel,phylop,gnomad,vep).",
    )
    chain_annotate_parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="Keep intermediate VCF files generated during the chain process.",
    )
    chain_annotate_parser.set_defaults(func=cmd_chain_annotate)


def get_base_args(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])

    # Support multiple input argument names for different VCF commands
    input_file = (
        getattr(args, "vcf_input", None)
        or getattr(args, "input", None)
        or getattr(args, "proband", None)
    )

    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        return None

    logging.debug(f"Input file: {os.path.abspath(input_file)}")

    threads, _ = get_resource_defaults(args.threads, None)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    md5_sig = calculate_bam_md5(input_file, None)
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)

    if not hasattr(args, "ploidy") or args.ploidy is None:
        if not hasattr(args, "ploidy_file") or args.ploidy_file is None:
            args.ploidy_file = lib.ploidy_file

    resolved_ref = lib.fasta
    logging.debug(f"Resolved reference: {resolved_ref}")

    paths_to_check = {"--input": input_file}
    if resolved_ref:
        paths_to_check["--ref"] = resolved_ref

    if not verify_paths_exist(paths_to_check):
        return None

    if not resolved_ref or not os.path.isfile(resolved_ref):
        logging.error(LOG_MESSAGES["ref_required_for"].format(task="variant calling"))
        return None
    return threads, outdir, resolved_ref, lib


def cmd_snp(args):
    verify_dependencies(["bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return

    threads, outdir, ref, lib = base

    print_warning("ButtonSNPVCF", threads=threads)

    out_vcf = os.path.join(outdir, "snps.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_snps"].format(output=out_vcf))
    region_args = ["-r", args.region] if args.region else []

    ploidy_args = []
    if args.ploidy_file:
        if not verify_paths_exist({"--ploidy-file": args.ploidy_file}):
            return
        ploidy_args = ["--ploidy-file", args.ploidy_file]
    elif args.ploidy:
        ploidy_args = ["--ploidy", args.ploidy]
    else:
        logging.error(
            "Ploidy (--ploidy or --ploidy-file) is required and could not be auto-resolved from --ref."
        )
        return

    bcftools = get_tool_path("bcftools")
    p1 = popen(
        [bcftools, "mpileup", "-B", "-I", "-C", "50", "-f", ref, "-Ou"]
        + region_args
        + [args.input],
        stdout=subprocess.PIPE,
    )
    p2 = popen(
        [bcftools, "call"]
        + ploidy_args
        + [
            "-V",
            "indels",
            "-v",
            "-m",
            "-P",
            "0",
            "--threads",
            threads,
            "-Oz",
            "-o",
            out_vcf,
        ],
        stdin=p1.stdout,
        stderr=subprocess.PIPE,
    )
    if p1.stdout:
        p1.stdout.close()
    _, stderr = p2.communicate()

    if p2.returncode != 0:
        logging.error(f"bcftools call failed with return code {p2.returncode}")
        if stderr:
            logging.error(stderr.decode(errors="replace"))
        return

    ensure_vcf_indexed(out_vcf)


def cmd_indel(args):
    verify_dependencies(["bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return

    threads, outdir, ref, lib = base

    print_warning("ButtonInDelVCF", threads=threads)

    out_vcf = os.path.join(outdir, "indels.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_indels"].format(output=out_vcf))
    region_args = ["-r", args.region] if args.region else []

    ploidy_args = []
    if args.ploidy_file:
        if not verify_paths_exist({"--ploidy-file": args.ploidy_file}):
            return
        ploidy_args = ["--ploidy-file", args.ploidy_file]
    elif args.ploidy:
        ploidy_args = ["--ploidy", args.ploidy]
    else:
        logging.error(
            "Ploidy (--ploidy or --ploidy-file) is required and could not be auto-resolved from --ref."
        )
        return

    bcftools = get_tool_path("bcftools")
    p1 = popen(
        [bcftools, "mpileup", "-B", "-C", "50", "-f", ref, "-Ou"]
        + region_args
        + [args.input],
        stdout=subprocess.PIPE,
    )
    p2 = popen(
        [bcftools, "call"]
        + ploidy_args
        + ["-V", "snps", "-v", "-m", "-P", "0", "--threads", threads, "-Ou"],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p1.stdout:
        p1.stdout.close()
    stdout, stderr = p2.communicate()

    if p2.returncode != 0:
        logging.error(f"bcftools call failed with return code {p2.returncode}")
        if stderr:
            logging.error(stderr.decode(errors="replace"))
        return

    p3 = popen(
        [bcftools, "norm", "-f", ref, "--threads", threads, "-Oz", "-o", out_vcf],
        stdin=subprocess.PIPE,
    )
    p3.communicate(input=stdout)

    if p3.returncode != 0:
        logging.error(f"bcftools norm failed with return code {p3.returncode}")
        return

    ensure_vcf_indexed(out_vcf)


def cmd_annotate(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    logging.debug(f"Input file: {os.path.abspath(input_file)}")

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    out_vcf = os.path.join(outdir, "annotated.vcf.gz")

    ann_vcf = args.ann_vcf
    cols = args.cols

    if not ann_vcf:
        # Try to auto-resolve from reference library
        md5_sig = (
            calculate_bam_md5(input_file, None)
            if input_file.lower().endswith((".bam", ".cram"))
            else None
        )
        lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
        if lib.ref_vcf_tab:
            ann_vcf = lib.ref_vcf_tab
            logging.info(f"Auto-resolved annotation file: {ann_vcf}")
        else:
            logging.error("--ann-vcf is required and could not be auto-resolved.")
            return

    if not cols:
        # Dynamically resolve columns from the annotation file
        if ann_vcf.lower().endswith(
            (".tab", ".tab.gz", ".txt", ".txt.gz", ".csv", ".csv.gz")
        ):
            try:
                import gzip

                open_func = gzip.open if ann_vcf.endswith(".gz") else open
                with open_func(ann_vcf, "rt") as f:
                    header = f.readline().strip()
                    if header.startswith("#"):
                        header = header[1:]
                    cols_in_file = [c.upper() for c in header.split()]
                    # Map common names to bcftools expected names
                    col_map = {
                        "CHROM": "CHROM",
                        "CHR": "CHROM",
                        "#CHROM": "CHROM",
                        "POS": "POS",
                        "ID": "ID",
                        "HG": "INFO/HG",
                        "RSID": "ID",
                    }
                    found_cols = []
                    for col_name in header.split():
                        upper_col = col_name.upper().lstrip("#")
                        if upper_col in col_map:
                            found_cols.append(col_map[upper_col])
                        else:
                            found_cols.append("-")  # Skip unknown columns

                    if "CHROM" in found_cols and "POS" in found_cols:
                        cols = ",".join(found_cols)
                        logging.info(f"Auto-resolved columns from header: {cols}")
            except Exception as e:
                logging.debug(f"Failed to parse tab header: {e}")

        if not cols and ann_vcf.lower().endswith((".vcf", ".vcf.gz")):
            # For VCFs, default to ID and HG if present in header
            try:
                res = subprocess.run(
                    ["bcftools", "view", "-h", ann_vcf], capture_output=True, text=True
                )
                found_cols = ["ID"]
                if "ID=HG" in res.stdout:
                    found_cols.append("INFO/HG")
                cols = ",".join(found_cols)
                logging.info(f"Auto-resolved VCF columns: {cols}")
            except Exception:
                pass

    if not cols:
        # Fallback to a safe default if still not resolved
        cols = "ID"
        logging.info(f"Using default annotation column: {cols}")

    if not verify_paths_exist({"--input": input_file, "--ann-vcf": ann_vcf}):
        return

    # Ensure inputs are bgzipped and indexed
    input_vcf = ensure_vcf_prepared(input_file)
    ann_vcf = ensure_vcf_prepared(ann_vcf)

    logging.info(LOG_MESSAGES["vcf_annotating"].format(input=input_vcf, output=out_vcf))
    try:
        subprocess.run(
            [
                "bcftools",
                "annotate",
                "-a",
                ann_vcf,
                "-c",
                cols,
                "-Oz",
                "-o",
                out_vcf,
                input_vcf,
            ],
            check=True,
        )
        ensure_vcf_indexed(out_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"❌: Annotation failed: {e}")


def cmd_filter(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    if not verify_paths_exist({"--input": input_file}):
        return

    logging.debug(f"Input file: {os.path.abspath(input_file)}")

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    out_vcf = os.path.join(outdir, "filtered.vcf.gz")

    # Resolve reference if needed for gap filtering or gene resolution
    md5_sig = calculate_bam_md5(input_file, None)
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    logging.debug(f"Resolved reference: {lib.fasta}")

    # Gene-based region resolution
    region = args.region
    if args.gene:
        from wgsextract_cli.core.gene_map import GeneMap

        gm = GeneMap(
            lib.root if lib.root else os.path.dirname(os.path.abspath(input_file))
        )
        resolved_region = gm.get_coords(args.gene, lib.build or "hg38")

        if resolved_region:
            logging.info(f"Resolved gene {args.gene} to {resolved_region}")
            region = resolved_region
        else:
            logging.error(f"Could not resolve gene name: {args.gene}")
            return

    region_args = ["-r", region] if region else []
    expr_args = ["-i", args.expr] if args.expr else []

    # Gap-aware filtering
    gaps_bed = None
    exclude_args = []
    if getattr(args, "exclude_near_gaps", False):
        if lib.fasta:
            gaps_bed = get_gaps_bed(lib.fasta)
            if gaps_bed:
                logging.info(f"Using gaps BED for exclusion: {gaps_bed}")
                exclude_args = ["-T", f"^{gaps_bed}"]
            else:
                logging.warning(
                    "Gap exclusion requested but Count Ns output (_nbin.csv) not found."
                )
        else:
            logging.warning(
                "Gap exclusion requested but reference genome not resolved."
            )

    input_vcf = ensure_vcf_prepared(input_file)
    logging.info(LOG_MESSAGES["vcf_filtering"].format(input=input_vcf, output=out_vcf))
    try:
        subprocess.run(
            ["bcftools", "view"]
            + region_args
            + expr_args
            + exclude_args
            + ["-Oz", "-o", out_vcf, input_vcf],
            check=True,
        )
        ensure_vcf_indexed(out_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"❌: Filtering failed: {e}")
    finally:
        if gaps_bed and os.path.exists(gaps_bed):
            os.remove(gaps_bed)


def get_gaps_bed(ref_path):
    """Try to locate and convert _nbin.csv to a temporary BED file."""
    import re

    prefix = re.sub(r"\.(fasta|fna|fa)(\.gz)?$", "", ref_path)
    nbin_file = prefix + "_nbin.csv"
    if not os.path.exists(nbin_file):
        return None

    import tempfile

    # Use a secure way to create a temp file
    fd, bed_path = tempfile.mkstemp(suffix=".bed")
    try:
        with os.fdopen(fd, "w") as f_out:
            with open(nbin_file) as f_in:
                # Assume format: chrom, start, end (maybe with header)
                for line in f_in:
                    parts = line.strip().split(",")
                    if len(parts) >= 3:
                        try:
                            chrom, start, end = parts[0], int(parts[1]), int(parts[2])
                            f_out.write(f"{chrom}\t{start}\t{end}\n")
                        except ValueError:
                            continue  # Header or invalid row
        return bed_path
    except Exception as e:
        logging.debug(f"Failed to create gaps BED: {e}")
        if os.path.exists(bed_path):
            os.remove(bed_path)
        return None


def cmd_trio(args):
    from wgsextract_cli.core.utils import (
        get_vcf_samples,
        normalize_vcf_chromosomes,
    )

    verify_dependencies(["bcftools", "tabix"])

    proband = args.proband if args.proband else args.vcf_input
    mother = args.mother
    father = args.father

    if not proband or not mother or not father:
        logging.error("Proband, Mother, and Father VCFs are all required.")
        return

    if not verify_paths_exist(
        {"--proband": proband, "--mother": mother, "--father": father}
    ):
        return

    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(proband))

    # 1. Prepare and Normalize
    p_vcf = ensure_vcf_prepared(proband)
    m_vcf = ensure_vcf_prepared(mother)
    f_vcf = ensure_vcf_prepared(father)

    # Get chrom style from proband
    try:
        res = subprocess.run(
            ["bcftools", "index", "-s", p_vcf], capture_output=True, text=True
        )
        target_chroms = [l.split("\t")[0] for l in res.stdout.strip().split("\n")]
    except Exception:
        target_chroms = ["chr1"]  # Default to chr

    m_vcf_norm = normalize_vcf_chromosomes(m_vcf, target_chroms)
    f_vcf_norm = normalize_vcf_chromosomes(f_vcf, target_chroms)

    # 2. Merge
    merged_vcf = os.path.join(outdir, "merged_trio_tmp.vcf.gz")
    region_args = ["-r", args.region] if getattr(args, "region", None) else []
    try:
        subprocess.run(
            [
                "bcftools",
                "merge",
                "--force-samples",
                "-Oz",
                "-o",
                merged_vcf,
            ]
            + region_args
            + [
                p_vcf,
                m_vcf_norm,
                f_vcf_norm,
            ],
            check=True,
        )
        ensure_vcf_indexed(merged_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"❌: VCF merge failed: {e}")
        return

    # 3. Identify sample order
    samples = get_vcf_samples(merged_vcf)
    # Map roles to indices
    p_idx, m_idx, f_idx = 0, 1, 2  # Defaults based on merge order

    def find_sample_idx(path, default):
        s_list = get_vcf_samples(path)
        if not s_list:
            return default
        name = s_list[0]
        try:
            return samples.index(name)
        except ValueError:
            # Try fuzzy match
            for i, s in enumerate(samples):
                if name in s or s in name:
                    return i
            return default

    p_idx = find_sample_idx(p_vcf, 0)
    m_idx = find_sample_idx(m_vcf_norm, 1)
    f_idx = find_sample_idx(f_vcf_norm, 2)

    modes = [args.mode] if args.mode != "all" else ["denovo", "recessive", "comphet"]

    for mode in modes:
        out_vcf = os.path.join(outdir, f"trio_{mode}.vcf.gz")
        logging.info(
            LOG_MESSAGES["vcf_trio_analysis"].format(mode=mode, output=out_vcf)
        )

        filter_expr = ""
        if mode == "denovo":
            # Child is het, parents are ref OR missing
            filter_expr = f'GT[{p_idx}]="het" && (GT[{m_idx}]="ref" || GT[{m_idx}]=".") && (GT[{f_idx}]="ref" || GT[{f_idx}]=".")'
        elif mode == "recessive":
            # Child is hom-alt, parents are het
            filter_expr = f'GT[{p_idx}]="hom" && GT[{m_idx}]="het" && GT[{f_idx}]="het"'
        elif mode == "comphet":
            # Simplified: Child is het, one parent is het, other is ref/missing
            filter_expr = f'GT[{p_idx}]="het" && ( (GT[{m_idx}]="het" && (GT[{f_idx}]="ref" || GT[{f_idx}]=".")) || ((GT[{m_idx}]="ref" || GT[{m_idx}]=".") && GT[{f_idx}]="het") )'

        try:
            subprocess.run(
                [
                    "bcftools",
                    "view",
                    "-i",
                    filter_expr,
                    "-Oz",
                    "-o",
                    out_vcf,
                    merged_vcf,
                ],
                check=True,
            )
            ensure_vcf_indexed(out_vcf)
            logging.info(LOG_MESSAGES["vcf_trio_complete"].format(output=out_vcf))

            # Basic summary
            try:
                # Count total
                total_res = subprocess.run(
                    ["bcftools", "view", "-H", out_vcf], capture_output=True, text=True
                )
                total_count = total_res.stdout.count("\n")

                # Check if CSQ exists in header
                has_csq = False
                header_res = subprocess.run(
                    ["bcftools", "view", "-h", out_vcf], capture_output=True, text=True
                )
                if "ID=CSQ" in header_res.stdout:
                    has_csq = True

                summary_msg = (
                    f"✅: {mode.upper()} results: {total_count} total variants"
                )

                if has_csq:
                    # Count high impact
                    high_res = subprocess.run(
                        ["bcftools", "view", "-H", "-i", 'CSQ~"HIGH"', out_vcf],
                        capture_output=True,
                        text=True,
                    )
                    high_count = high_res.stdout.count("\n")
                    summary_msg += f", {high_count} HIGH impact"

                logging.info(summary_msg)
            except Exception:
                pass

        except subprocess.CalledProcessError as e:
            logging.error(f"❌: Filtering for {mode} failed: {e}")

    # Cleanup
    if os.path.exists(merged_vcf):
        os.remove(merged_vcf)
        if os.path.exists(merged_vcf + ".tbi"):
            os.remove(merged_vcf + ".tbi")
        if os.path.exists(merged_vcf + ".csi"):
            os.remove(merged_vcf + ".csi")

    if m_vcf_norm != m_vcf and os.path.exists(m_vcf_norm):
        os.remove(m_vcf_norm)
        if os.path.exists(m_vcf_norm + ".tbi"):
            os.remove(m_vcf_norm + ".tbi")
    if f_vcf_norm != f_vcf and os.path.exists(f_vcf_norm):
        os.remove(f_vcf_norm)
        if os.path.exists(f_vcf_norm + ".tbi"):
            os.remove(f_vcf_norm + ".tbi")


def cmd_cnv(args):
    verify_dependencies(["delly", "bcftools", "tabix", "samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_bcf = os.path.join(outdir, "cnv.bcf")
    out_vcf = os.path.join(outdir, "cnv.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_cnv"].format(output=out_vcf))

    # Auto-resolve mappability map if possible
    map_file = (
        args.map
        if getattr(args, "map", None)
        else getattr(lib, "mappability_map", None)
    )

    if not map_file or not os.path.exists(map_file):
        logging.error("❌: Mappability map (-M/--map) is required for delly cnv.")
        logging.error("     You can download standard maps (e.g., hg38.map.gz) from:")
        logging.error("     https://github.com/dellytools/delly/tree/master/exclude")
        logging.error("     Or provide a custom .map file.")
        sys.exit(1)

    map_args = ["-m", map_file]
    if getattr(args, "ploidy", None):
        map_args.extend(["-y", args.ploidy])

    temp_bam = None
    input_file = args.input

    if getattr(args, "region", None):
        import tempfile

        fd, temp_bam = tempfile.mkstemp(suffix=".bam", dir=outdir)
        os.close(fd)
        logging.info(f"Extracting region {args.region} to temporary BAM...")
        try:
            samtools = get_tool_path("samtools")
            view_cmd = [
                samtools,
                "view",
                "-bh",
            ]
            if args.input.lower().endswith(".cram"):
                view_cmd.extend(["-T", ref])

            view_cmd.extend(
                [
                    args.input,
                    args.region,
                    "-o",
                    temp_bam,
                ]
            )
            run_command(view_cmd)
            run_command([samtools, "index", temp_bam])
            input_file = temp_bam
        except Exception as e:
            logging.error(f"Failed to extract region: {e}")
            if os.path.exists(temp_bam):
                os.remove(temp_bam)
            return

    try:
        # delly cnv -g ref.fa -o cnv.bcf input.bam
        delly = get_tool_path("delly")
        bcftools = get_tool_path("bcftools")
        cmd = [delly, "cnv", "-g", ref, "-o", out_bcf] + map_args + [input_file]
        run_command(cmd)
        # convert bcf to vcf.gz
        run_command([bcftools, "view", "-Oz", "-o", out_vcf, out_bcf])
        ensure_vcf_indexed(out_vcf)
        if os.path.exists(out_bcf):
            os.remove(out_bcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"CNV calling failed: {e}")
        if e.returncode < 0:
            import signal

            if abs(e.returncode) == signal.SIGSEGV:
                logging.error("❌: Delly segfaulted (Segmentation Fault).")
                logging.error(
                    "     This is common on macOS due to incompatible shared libraries (boost/htslib) in some environments."
                )
                logging.error(
                    "     Hint: Try 'brew install delly' or run in a Linux container."
                )
        else:
            logging.error(
                "Hint: If using macOS, ensure 'delly' and 'boost' are correctly installed via Homebrew."
            )
        sys.exit(e.returncode)
    finally:
        if temp_bam and os.path.exists(temp_bam):
            os.remove(temp_bam)
            if os.path.exists(temp_bam + ".bai"):
                os.remove(temp_bam + ".bai")


def cmd_sv(args):
    verify_dependencies(["delly", "bcftools", "tabix", "samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_bcf = os.path.join(outdir, "sv.bcf")
    out_vcf = os.path.join(outdir, "sv.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_sv"].format(output=out_vcf))

    temp_bam = None
    input_file = args.input

    if getattr(args, "region", None):
        import tempfile

        fd, temp_bam = tempfile.mkstemp(suffix=".bam", dir=outdir)
        os.close(fd)
        logging.info(f"Extracting region {args.region} to temporary BAM...")
        try:
            samtools = get_tool_path("samtools")
            view_cmd = [
                samtools,
                "view",
                "-bh",
            ]
            if args.input.lower().endswith(".cram"):
                view_cmd.extend(["-T", ref])

            view_cmd.extend(
                [
                    args.input,
                    args.region,
                    "-o",
                    temp_bam,
                ]
            )
            run_command(view_cmd)
            run_command([samtools, "index", temp_bam])
            input_file = temp_bam
        except Exception as e:
            logging.error(f"Failed to extract region: {e}")
            if os.path.exists(temp_bam):
                os.remove(temp_bam)
            return

    try:
        # delly call -g ref.fa -o sv.bcf input.bam
        delly = get_tool_path("delly")
        bcftools = get_tool_path("bcftools")
        cmd = [delly, "call", "-g", ref, "-o", out_bcf, input_file]
        run_command(cmd)
        # convert bcf to vcf.gz
        run_command([bcftools, "view", "-Oz", "-o", out_vcf, out_bcf])
        ensure_vcf_indexed(out_vcf)
        if os.path.exists(out_bcf):
            os.remove(out_bcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"SV calling failed: {e}")
        logging.error(
            "Hint: If using macOS, ensure 'delly' and 'boost' are correctly installed via Homebrew."
        )
        sys.exit(e.returncode)
    finally:
        if temp_bam and os.path.exists(temp_bam):
            os.remove(temp_bam)
            if os.path.exists(temp_bam + ".bai"):
                os.remove(temp_bam + ".bai")


def _exit_if_missing(file_path, message_key, ann_name=None):
    if not file_path:
        msg = LOG_MESSAGES.get(message_key, f"Missing data file for {ann_name}")
        logging.error(f"REQUIRED DATA MISSING: {msg}")
        logging.info(
            f"To fix this, run: wgsextract ref {ann_name or message_key.split('_')[1]}"
        )
        sys.exit(2)  # Use exit code 2 to indicate missing data


def cmd_clinvar(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(LOG_MESSAGES["vcf_clinvar_start"].format(input=input_file))

    # Resolve ClinVar VCF
    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    clinvar_vcf = args.clinvar_file if args.clinvar_file else lib.clinvar_vcf

    _exit_if_missing(clinvar_vcf, "vcf_clinvar_missing", "clinvar")

    logging.info(LOG_MESSAGES["vcf_clinvar_resolve"].format(path=clinvar_vcf))

    # 1. Prepare Inputs
    input_vcf = ensure_vcf_prepared(input_file)
    clinvar_prepared = ensure_vcf_prepared(clinvar_vcf)

    # 2. Match chromosome styles (chr1 vs 1)
    from wgsextract_cli.core.utils import normalize_vcf_chromosomes

    try:
        res_c = subprocess.run(
            ["bcftools", "index", "-s", clinvar_prepared],
            capture_output=True,
            text=True,
        )
        c_chroms = [l.split("\t")[0] for l in res_c.stdout.strip().split("\n")]
        normalized_input = normalize_vcf_chromosomes(input_vcf, c_chroms)
    except Exception:
        normalized_input = input_vcf

    # 3. Annotate with ClinVar
    # We transfer CLNSIG (Significance) and CLNDN (Disease Name)
    ann_out = os.path.join(outdir, "clinvar_annotated.vcf.gz")
    try:
        run_command(
            [
                "bcftools",
                "annotate",
                "-a",
                clinvar_prepared,
                "-c",
                "CLNSIG,CLNDN",
                "-Oz",
                "-o",
                ann_out,
                normalized_input,
            ],
            capture_output=True,
        )
        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"ClinVar annotation failed: {e}")
        sys.exit(1)
    finally:
        if normalized_input != input_vcf and os.path.exists(normalized_input):
            os.remove(normalized_input)

    # 4. Filter for Pathogenic
    path_out = os.path.join(outdir, "clinvar_pathogenic.vcf.gz")
    logging.info(LOG_MESSAGES["vcf_clinvar_filtering"].format(output=path_out))
    try:
        # Filter for Pathogenic or Likely_pathogenic in CLNSIG
        # The exact string can vary slightly, so we use a regex/substring match
        filter_expr = 'CLNSIG ~ "Pathogenic" || CLNSIG ~ "Likely_pathogenic"'
        run_command(
            ["bcftools", "filter", "-i", filter_expr, "-Oz", "-o", path_out, ann_out],
            capture_output=True,
        )
        ensure_vcf_indexed(path_out)
        logging.info(LOG_MESSAGES["vcf_clinvar_done"].format(output=path_out))
    except Exception as e:
        logging.error(f"ClinVar filtering failed: {e}")


def cmd_revel(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(LOG_MESSAGES["vcf_revel_start"].format(input=input_file))

    # Resolve REVEL data file
    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    revel_file = args.revel_file if args.revel_file else lib.revel_file

    _exit_if_missing(revel_file, "vcf_revel_missing", "revel")

    logging.info(LOG_MESSAGES["vcf_revel_resolve"].format(path=revel_file))

    # 1. Prepare Inputs
    input_vcf = ensure_vcf_prepared(input_file)
    revel_vcf = ensure_vcf_prepared(revel_file)

    # 2. Match chromosome styles (chr1 vs 1)
    normalized_input = input_vcf
    needs_cleanup = False
    try:
        res_v = subprocess.run(
            ["bcftools", "index", "-s", input_vcf], capture_output=True, text=True
        )
        v_chroms = [l.split("\t")[0] for l in res_v.stdout.strip().split("\n")]

        if revel_vcf.lower().endswith((".vcf", ".vcf.gz")):
            res_r = subprocess.run(
                ["bcftools", "index", "-s", revel_vcf], capture_output=True, text=True
            )
            r_chroms = [l.split("\t")[0] for l in res_r.stdout.strip().split("\n")]
        else:
            res_r = subprocess.run(
                ["tabix", "-l", revel_vcf], capture_output=True, text=True
            )
            r_chroms = res_r.stdout.strip().split("\n")

        v_has_chr = any(c.startswith("chr") for c in v_chroms)
        r_has_chr = any(c.startswith("chr") for c in r_chroms if c)

        if v_has_chr != r_has_chr:
            import tempfile

            fd, map_path = tempfile.mkstemp(suffix=".map", dir=outdir)
            with os.fdopen(fd, "w") as f:
                for vc in v_chroms:
                    if v_has_chr and not r_has_chr:
                        rc = vc[3:] if vc.startswith("chr") else vc
                        if rc == "MT":
                            rc = "M"
                        f.write(f"{vc} {rc}\n")
                    elif not v_has_chr and r_has_chr:
                        rc = "chr" + vc
                        if rc == "chrMT":
                            rc = "chrM"
                        f.write(f"{vc} {rc}\n")

            norm_out = os.path.join(outdir, "input_revel_norm.vcf.gz")
            logging.info(
                f"Normalizing chromosome naming for REVEL: {'chr1 -> 1' if v_has_chr else '1 -> chr1'}"
            )
            subprocess.run(
                [
                    "bcftools",
                    "annotate",
                    "--rename-chrs",
                    map_path,
                    "-Oz",
                    "-o",
                    norm_out,
                    input_vcf,
                ],
                check=True,
            )
            ensure_vcf_indexed(norm_out)
            os.remove(map_path)
            normalized_input = norm_out
            needs_cleanup = True
    except Exception as e:
        logging.debug(f"Chromosome normalization failed: {e}")

    # 3. Annotate with REVEL
    ann_out = os.path.join(outdir, "revel_annotated.vcf.gz")
    header_tmp = None
    try:
        # Annovar REVEL TSV: #Chr, Start, End, Ref, Alt, REVEL
        cols = "CHROM,POS,-,REF,ALT,INFO/REVEL"
        annotate_args = [
            "bcftools",
            "annotate",
            "-a",
            revel_vcf,
            "-Oz",
            "-o",
            ann_out,
        ]

        if revel_vcf.lower().endswith((".vcf", ".vcf.gz")):
            annotate_args.extend(["-c", "INFO/REVEL"])
        else:
            import tempfile

            fd, header_tmp = tempfile.mkstemp(suffix=".hdr", dir=outdir)
            with os.fdopen(fd, "w") as f:
                f.write(
                    '##INFO=<ID=REVEL,Number=1,Type=Float,Description="REVEL score">\n'
                )
            annotate_args.extend(["-c", cols, "-h", header_tmp])

        annotate_args.append(normalized_input)
        run_command(annotate_args, capture_output=True)
        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"REVEL annotation failed: {e}")
        sys.exit(1)
    finally:
        if header_tmp and os.path.exists(header_tmp):
            os.remove(header_tmp)
        if needs_cleanup and os.path.exists(normalized_input):
            os.remove(normalized_input)
            if os.path.exists(normalized_input + ".tbi"):
                os.remove(normalized_input + ".tbi")

    # 4. Optional Filtering
    if args.min_score is not None:
        path_out = os.path.join(outdir, f"revel_gt_{args.min_score}.vcf.gz")
        logging.info(
            LOG_MESSAGES["vcf_revel_filtering"].format(
                min_score=args.min_score, output=path_out
            )
        )
        try:
            filter_expr = f"REVEL >= {args.min_score}"
            run_command(
                [
                    "bcftools",
                    "filter",
                    "-i",
                    filter_expr,
                    "-Oz",
                    "-o",
                    path_out,
                    ann_out,
                ],
                capture_output=True,
            )
            ensure_vcf_indexed(path_out)
            logging.info(LOG_MESSAGES["vcf_revel_done"].format(output=path_out))
        except Exception as e:
            logging.error(f"REVEL filtering failed: {e}")
    else:
        logging.info(LOG_MESSAGES["vcf_revel_done"].format(output=ann_out))


def cmd_phylop(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(LOG_MESSAGES["vcf_phylop_start"].format(input=input_file))

    # Resolve PhyloP data file
    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    phylop_file = args.phylop_file if args.phylop_file else lib.phylop_file

    _exit_if_missing(phylop_file, "vcf_phylop_missing", "phylop")

    logging.info(LOG_MESSAGES["vcf_phylop_resolve"].format(path=phylop_file))

    # 1. Prepare Inputs
    input_vcf = ensure_vcf_prepared(input_file)
    phylop_vcf = ensure_vcf_prepared(phylop_file)

    # 2. Match chromosome styles (chr1 vs 1)
    normalized_input = input_vcf
    needs_cleanup = False
    try:
        res_v = subprocess.run(
            ["bcftools", "index", "-s", input_vcf], capture_output=True, text=True
        )
        v_chroms = [l.split("\t")[0] for l in res_v.stdout.strip().split("\n")]

        if phylop_vcf.lower().endswith((".vcf", ".vcf.gz")):
            res_p = subprocess.run(
                ["bcftools", "index", "-s", phylop_vcf], capture_output=True, text=True
            )
            p_chroms = [l.split("\t")[0] for l in res_p.stdout.strip().split("\n")]
        else:
            res_p = subprocess.run(
                ["tabix", "-l", phylop_vcf], capture_output=True, text=True
            )
            p_chroms = res_p.stdout.strip().split("\n")

        v_has_chr = any(c.startswith("chr") for c in v_chroms)
        p_has_chr = any(c.startswith("chr") for c in p_chroms if c)

        if v_has_chr != p_has_chr:
            import tempfile

            fd, map_path = tempfile.mkstemp(suffix=".map", dir=outdir)
            with os.fdopen(fd, "w") as f:
                for vc in v_chroms:
                    if v_has_chr and not p_has_chr:
                        pc = vc[3:] if vc.startswith("chr") else vc
                        if pc == "MT":
                            pc = "M"
                        f.write(f"{vc} {pc}\n")
                    elif not v_has_chr and p_has_chr:
                        pc = "chr" + vc
                        if pc == "chrMT":
                            pc = "chrM"
                        f.write(f"{vc} {pc}\n")

            norm_out = os.path.join(outdir, "input_phylop_norm.vcf.gz")
            logging.info(
                f"Normalizing chromosome naming for PhyloP: {'chr1 -> 1' if v_has_chr else '1 -> chr1'}"
            )
            subprocess.run(
                [
                    "bcftools",
                    "annotate",
                    "--rename-chrs",
                    map_path,
                    "-Oz",
                    "-o",
                    norm_out,
                    input_vcf,
                ],
                check=True,
            )
            ensure_vcf_indexed(norm_out)
            os.remove(map_path)
            normalized_input = norm_out
            needs_cleanup = True
    except Exception as e:
        logging.debug(f"Chromosome normalization failed: {e}")

    # 3. Annotate with PhyloP
    ann_out = os.path.join(outdir, "phylop_annotated.vcf.gz")
    header_tmp = None
    try:
        # Annovar PhyloP TSV: #Chr, Start, End, Score
        # We want CHROM=1, POS=2, Score=4
        cols = "CHROM,POS,-,INFO/PHYLOP"
        annotate_args = [
            "bcftools",
            "annotate",
            "-a",
            phylop_vcf,
            "-Oz",
            "-o",
            ann_out,
        ]

        if phylop_vcf.lower().endswith((".vcf", ".vcf.gz")):
            annotate_args.extend(["-c", "INFO/PHYLOP"])
        else:
            import tempfile

            fd, header_tmp = tempfile.mkstemp(suffix=".hdr", dir=outdir)
            with os.fdopen(fd, "w") as f:
                f.write(
                    '##INFO=<ID=PHYLOP,Number=1,Type=Float,Description="PhyloP conservation score">\n'
                )
            annotate_args.extend(["-c", cols, "-h", header_tmp])

        annotate_args.append(normalized_input)
        run_command(annotate_args, capture_output=True)
        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"PhyloP annotation failed: {e}")
        sys.exit(1)
    finally:
        if header_tmp and os.path.exists(header_tmp):
            os.remove(header_tmp)
        if needs_cleanup and os.path.exists(normalized_input):
            os.remove(normalized_input)
            if os.path.exists(normalized_input + ".tbi"):
                os.remove(normalized_input + ".tbi")

    # 4. Optional Filtering
    if args.min_score is not None:
        path_out = os.path.join(outdir, f"phylop_gt_{args.min_score}.vcf.gz")
        logging.info(
            LOG_MESSAGES["vcf_phylop_filtering"].format(
                min_score=args.min_score, output=path_out
            )
        )
        try:
            filter_expr = f"PHYLOP >= {args.min_score}"
            run_command(
                [
                    "bcftools",
                    "filter",
                    "-i",
                    filter_expr,
                    "-Oz",
                    "-o",
                    path_out,
                    ann_out,
                ],
                capture_output=True,
            )
            ensure_vcf_indexed(path_out)
            logging.info(LOG_MESSAGES["vcf_phylop_done"].format(output=path_out))
        except Exception as e:
            logging.error(f"PhyloP filtering failed: {e}")
    else:
        logging.info(LOG_MESSAGES["vcf_phylop_done"].format(output=ann_out))


def cmd_gnomad(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(f"Annotating VCF with gnomAD data: {input_file}")

    # Resolve gnomAD VCF
    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    gnomad_file = args.gnomad_file if args.gnomad_file else lib.gnomad_vcf

    _exit_if_missing(gnomad_file, "vcf_gnomad_missing", "gnomad")

    logging.info(f"Using gnomAD file: {gnomad_file}")

    # 1. Prepare Inputs
    input_vcf = ensure_vcf_prepared(input_file)
    gnomad_vcf = ensure_vcf_prepared(gnomad_file)

    # 2. Match chromosome styles (chr1 vs 1)
    # Reuse normalization logic if possible, or just call normalize_vcf_chromosomes
    from wgsextract_cli.core.utils import normalize_vcf_chromosomes

    try:
        res_g = subprocess.run(
            ["bcftools", "index", "-s", gnomad_vcf], capture_output=True, text=True
        )
        g_chroms = [l.split("\t")[0] for l in res_g.stdout.strip().split("\n")]
        normalized_input = normalize_vcf_chromosomes(input_vcf, g_chroms)
    except Exception as e:
        logging.debug(f"Chromosome normalization check failed: {e}")
        normalized_input = input_vcf

    # 3. Annotate with gnomAD
    # We'll transfer AF (Allele Frequency) as GNOMAD_AF to avoid collisions
    ann_out = os.path.join(outdir, "gnomad_annotated.vcf.gz")
    header_tmp = None
    try:
        import tempfile

        fd, header_tmp = tempfile.mkstemp(suffix=".hdr", dir=outdir)
        with os.fdopen(fd, "w") as f:
            f.write(
                '##INFO=<ID=GNOMAD_AF,Number=A,Type=Float,Description="gnomAD Allele Frequency">\n'
            )

        run_command(
            [
                "bcftools",
                "annotate",
                "-a",
                gnomad_vcf,
                "-h",
                header_tmp,
                "-c",
                "INFO/GNOMAD_AF:=INFO/AF",
                "-Oz",
                "-o",
                ann_out,
                normalized_input,
            ],
            capture_output=True,
        )
        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"gnomAD annotation failed: {e}")
        sys.exit(1)
    finally:
        if header_tmp and os.path.exists(header_tmp):
            os.remove(header_tmp)
        if normalized_input != input_vcf and os.path.exists(normalized_input):
            os.remove(normalized_input)
            if os.path.exists(normalized_input + ".tbi"):
                os.remove(normalized_input + ".tbi")

    # 4. Optional Filtering
    if args.max_af is not None:
        filter_out = os.path.join(outdir, f"gnomad_af_lt_{args.max_af}.vcf.gz")
        logging.info(
            f"Filtering for variants with gnomAD Allele Frequency < {args.max_af} to {filter_out}"
        )
        try:
            # Note: bcftools filter handles missing values (not in gnomAD) by excluding them by default
            # unless we explicitly ask to keep them. Common practice for 'rare' filtering is
            # to keep anything with AF < threshold OR AF is missing.
            filter_expr = f"GNOMAD_AF < {args.max_af} || GNOMAD_AF='.'"
            run_command(
                [
                    "bcftools",
                    "filter",
                    "-i",
                    filter_expr,
                    "-Oz",
                    "-o",
                    filter_out,
                    ann_out,
                ],
                capture_output=True,
            )
            ensure_vcf_indexed(filter_out)
            logging.info(f"gnomAD filtering complete: {filter_out}")
        except Exception as e:
            logging.error(f"gnomAD filtering failed: {e}")
    else:
        logging.info(LOG_MESSAGES["vcf_gnomad_done"].format(output=ann_out))


def cmd_spliceai(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(f"Annotating VCF with SpliceAI scores: {input_file}")

    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    spliceai_file = args.spliceai_file if args.spliceai_file else lib.spliceai_vcf

    _exit_if_missing(spliceai_file, "vcf_spliceai_missing", "spliceai")

    # 1. Prepare Inputs

    input_vcf = ensure_vcf_prepared(input_file)
    spliceai_vcf = ensure_vcf_prepared(spliceai_file)

    # 2. Match chromosome styles
    from wgsextract_cli.core.utils import normalize_vcf_chromosomes

    try:
        res_s = subprocess.run(
            ["bcftools", "index", "-s", spliceai_vcf], capture_output=True, text=True
        )
        s_chroms = [l.split("\t")[0] for l in res_s.stdout.strip().split("\n")]
        normalized_input = normalize_vcf_chromosomes(input_vcf, s_chroms)
    except Exception:
        normalized_input = input_vcf

    # 3. Annotate with SpliceAI
    ann_out = os.path.join(outdir, "spliceai_annotated.vcf.gz")
    try:
        run_command(
            [
                "bcftools",
                "annotate",
                "-a",
                spliceai_vcf,
                "-c",
                "INFO/SpliceAI",
                "-Oz",
                "-o",
                ann_out,
                normalized_input,
            ],
            capture_output=True,
        )
        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"SpliceAI annotation failed: {e}")
        sys.exit(1)
    finally:
        if normalized_input != input_vcf and os.path.exists(normalized_input):
            os.remove(normalized_input)

    # 4. Finish
    logging.info(LOG_MESSAGES["vcf_spliceai_done"].format(output=ann_out))


def cmd_alphamissense(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(f"Annotating VCF with AlphaMissense scores: {input_file}")

    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    am_file = args.am_file if args.am_file else lib.alphamissense_vcf

    _exit_if_missing(am_file, "vcf_alphamissense_missing", "alphamissense")

    # 1. Prepare Inputs

    input_vcf = ensure_vcf_prepared(input_file)
    am_vcf = ensure_vcf_prepared(am_file)

    # 2. Match chromosome styles
    from wgsextract_cli.core.utils import normalize_vcf_chromosomes

    try:
        res_a = subprocess.run(
            ["bcftools", "index", "-s", am_vcf], capture_output=True, text=True
        )
        a_chroms = [l.split("\t")[0] for l in res_a.stdout.strip().split("\n")]
        normalized_input = normalize_vcf_chromosomes(input_vcf, a_chroms)
    except Exception:
        normalized_input = input_vcf

    # 3. Annotate with AlphaMissense
    ann_out = os.path.join(outdir, "alphamissense_annotated.vcf.gz")
    header_tmp = None
    try:
        if am_vcf.lower().endswith((".vcf", ".vcf.gz", ".vcf.bgz")):
            cols = "INFO/am_pathogenicity,INFO/am_class"
            h_arg = []
        else:
            # TSV: #CHROM  POS     REF     ALT     genome  uniprot_id      transcript_id   protein_variant am_pathogenicity        am_class
            cols = "CHROM,POS,REF,ALT,-,-,-,-,INFO/am_pathogenicity,INFO/am_class"
            import tempfile

            fd, header_tmp = tempfile.mkstemp(suffix=".hdr", dir=outdir)
            with os.fdopen(fd, "w") as f:
                f.write(
                    '##INFO=<ID=am_pathogenicity,Number=1,Type=Float,Description="AlphaMissense pathogenicity score">\n'
                )
                f.write(
                    '##INFO=<ID=am_class,Number=1,Type=String,Description="AlphaMissense classification">\n'
                )
            h_arg = ["-h", header_tmp]

        run_command(
            [
                "bcftools",
                "annotate",
                "-a",
                am_vcf,
                "-c",
                cols,
            ]
            + h_arg
            + [
                "-Oz",
                "-o",
                ann_out,
                normalized_input,
            ],
            capture_output=True,
        )
        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"AlphaMissense annotation failed: {e}")
        sys.exit(1)
    finally:
        if header_tmp and os.path.exists(header_tmp):
            os.remove(header_tmp)
        if normalized_input != input_vcf and os.path.exists(normalized_input):
            os.remove(normalized_input)

    # 4. Optional Filtering
    if args.min_score is not None:
        path_out = os.path.join(outdir, f"alphamissense_gt_{args.min_score}.vcf.gz")
        try:
            run_command(
                [
                    "bcftools",
                    "filter",
                    "-i",
                    f"am_pathogenicity >= {args.min_score}",
                    "-Oz",
                    "-o",
                    path_out,
                    ann_out,
                ],
                capture_output=True,
            )
            ensure_vcf_indexed(path_out)
            logging.info(f"AlphaMissense filtering complete: {path_out}")
        except Exception as e:
            logging.error(f"AlphaMissense filtering failed: {e}")
    else:
        logging.info(LOG_MESSAGES["vcf_alphamissense_done"].format(output=ann_out))


def cmd_pharmgkb(args):
    verify_dependencies(["bcftools", "tabix"])
    log_dependency_info(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.info(f"Annotating VCF with PharmGKB data: {input_file}")

    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)
    pharmgkb_file = args.pharmgkb_file if args.pharmgkb_file else lib.pharmgkb_vcf

    _exit_if_missing(pharmgkb_file, "vcf_pharmgkb_missing", "pharmgkb")

    # 1. Prepare Inputs

    input_vcf = ensure_vcf_prepared(input_file)
    pharmgkb_vcf = ensure_vcf_prepared(pharmgkb_file)

    # 2. Match chromosome styles
    from wgsextract_cli.core.utils import normalize_vcf_chromosomes

    try:
        res_p = subprocess.run(
            ["bcftools", "index", "-s", pharmgkb_vcf], capture_output=True, text=True
        )
        p_chroms = [l.split("\t")[0] for l in res_p.stdout.strip().split("\n")]
        normalized_input = normalize_vcf_chromosomes(input_vcf, p_chroms)
    except Exception:
        normalized_input = input_vcf

    # 3. Annotate with PharmGKB
    ann_out = os.path.join(outdir, "pharmgkb_annotated.vcf.gz")
    try:
        # Transfer all INFO fields from PharmGKB
        run_command(
            [
                "bcftools",
                "annotate",
                "-a",
                pharmgkb_vcf,
                "-c",
                "PHARMGKB",
                "-Oz",
                "-o",
                ann_out,
                normalized_input,
            ],
            capture_output=True,
        )

        ensure_vcf_indexed(ann_out)
    except Exception as e:
        logging.error(f"PharmGKB annotation failed: {e}")
        sys.exit(1)
    finally:
        if normalized_input != input_vcf and os.path.exists(normalized_input):
            os.remove(normalized_input)

    logging.info(f"PharmGKB annotation complete: {ann_out}")


def cmd_freebayes(args):
    verify_dependencies(["freebayes", "bcftools", "tabix", "samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_vcf = os.path.join(outdir, "freebayes.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_freebayes"].format(output=out_vcf))
    region_args = ["-r", args.region] if args.region else []

    # Freebayes requires an uncompressed reference sequence.
    # If the reference is .gz, we must decompress it temporarily.
    temp_ref = None
    use_ref = ref

    if ref.lower().endswith(".gz"):
        logging.info(
            "Freebayes requires an uncompressed reference. Decompressing temporarily..."
        )
        import tempfile

        # Create temp file in outdir to ensure enough space
        fd, temp_ref = tempfile.mkstemp(suffix=".fa", dir=outdir)
        os.close(fd)
        try:
            with open(temp_ref, "wb") as f_out:
                subprocess.run(["gunzip", "-c", ref], stdout=f_out, check=True)
            # Index the temp ref
            logging.info("Indexing temporary reference...")
            subprocess.run(["samtools", "faidx", temp_ref], check=True)
            use_ref = temp_ref
        except Exception as e:
            logging.error(f"Failed to prepare uncompressed reference: {e}")
            if temp_ref and os.path.exists(temp_ref):
                os.remove(temp_ref)
                if os.path.exists(temp_ref + ".fai"):
                    os.remove(temp_ref + ".fai")
            return

    # Check if input is CRAM
    is_cram = args.input.lower().endswith(".cram")

    try:
        freebayes = get_tool_path("freebayes")
        bcftools = get_tool_path("bcftools")
        samtools = get_tool_path("samtools")

        if is_cram:
            # freebayes doesn't always handle CRAM perfectly via stdin
            view_cmd = [samtools, "view", "-uh", "-T", use_ref, args.input]
            if args.region:
                view_cmd.extend(
                    ["-r", args.region] if "-r" not in region_args else region_args
                )

            p_view = popen(view_cmd, stdout=subprocess.PIPE)
            p_fb = popen(
                [freebayes, "-f", use_ref, "--stdin"],
                stdin=p_view.stdout,
                stdout=subprocess.PIPE,
            )
            p_vcf = popen([bcftools, "view", "-Oz", "-o", out_vcf], stdin=p_fb.stdout)

            if p_view.stdout:
                p_view.stdout.close()
            if p_fb.stdout:
                p_fb.stdout.close()
            _, stderr = p_vcf.communicate()

            if p_vcf.returncode != 0:
                logging.error(
                    f"Freebayes/bcftools pipeline failed with return code {p_vcf.returncode}"
                )
                if stderr:
                    logging.error(stderr.decode(errors="replace"))
        else:
            # BAM handling
            p1 = popen(
                [freebayes, "-f", use_ref] + region_args + [args.input],
                stdout=subprocess.PIPE,
            )
            p2 = popen(
                [bcftools, "view", "-Oz", "-o", out_vcf],
                stdin=p1.stdout,
                stderr=subprocess.PIPE,
            )
            if p1.stdout:
                p1.stdout.close()
            _, stderr = p2.communicate()

            if p2.returncode != 0:
                logging.error(
                    f"Freebayes/bcftools failed with return code {p2.returncode}"
                )
                if stderr:
                    logging.error(stderr.decode(errors="replace"))

        ensure_vcf_indexed(out_vcf)
    except Exception as e:
        logging.error(f"Freebayes failed: {e}")
    finally:
        # Clean up temp reference
        if temp_ref and os.path.exists(temp_ref):
            logging.info("Cleaning up temporary reference...")
            os.remove(temp_ref)
            if os.path.exists(temp_ref + ".fai"):
                os.remove(temp_ref + ".fai")


def cmd_gatk(args):
    verify_dependencies(["gatk", "samtools"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_vcf = os.path.join(outdir, "gatk.vcf.gz")

    # GATK requires a .dict file
    if not lib.dict_file:
        logging.info(LOG_MESSAGES["vcf_generating_dict"])
        dict_file = (
            ref.replace(".fa.gz", ".dict")
            .replace(".fasta.gz", ".dict")
            .replace(".fa", ".dict")
            .replace(".fasta", ".dict")
        )
        try:
            subprocess.run(["samtools", "dict", "-o", dict_file, ref], check=True)
            lib.dict_file = dict_file
        except Exception as e:
            logging.error(f"Failed to generate .dict file: {e}")
            return

    logging.info(LOG_MESSAGES["vcf_calling_gatk"].format(output=out_vcf))
    region_args = ["-L", args.region] if args.region else []

    try:
        from wgsextract_cli.core.dependencies import get_tool_path

        gatk_tool = get_tool_path("gatk")
        # Use system gatk binary
        cmd = [
            gatk_tool,
            "HaplotypeCaller",
            "-R",
            ref,
            "-I",
            args.input,
            "-O",
            out_vcf,
        ] + region_args
        run_command(cmd)
        ensure_vcf_indexed(out_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"GATK failed: {e}")
        if args.input.lower().endswith(".cram"):
            logging.error(
                "Hint: Older GATK versions do not support CRAM version 3.1. "
                "If this failed with a CRAM error, please convert to BAM or upgrade GATK."
            )
        sys.exit(e.returncode)


def cmd_deepvariant(args):
    import shlex

    # DeepVariant can be run via:
    # 1. Official 'run_deepvariant' wrapper
    # 2. Bioconda 'dv_make_examples.py' + 'dv_call_variants.py' + 'dv_postprocess_variants.py'

    executable = shutil.which("run_deepvariant")
    use_bioconda = False

    if not executable:
        executable = shutil.which("dv_make_examples.py")
        if executable:
            use_bioconda = True
            logging.info("Found Bioconda DeepVariant scripts.")
        else:
            logging.error(
                "DeepVariant not found. Please install it or ensure it is in your PATH."
            )
            return

    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_vcf = os.path.join(outdir, "deepvariant.vcf.gz")
    intermediate_vcf = os.path.join(outdir, "deepvariant.vcf")

    logging.info(LOG_MESSAGES["vcf_calling_deepvariant"].format(output=out_vcf))

    model_type = "WGS" if not args.wes else "WES"
    region_args = ["--regions", args.region] if args.region else []

    try:
        if use_bioconda:
            # 0. Prepare clean environment for conda run
            clean_env = os.environ.copy()
            dv_bin_dir = os.path.dirname(executable)
            # Remove virtualenv stuff that interferes with conda internal python
            clean_env.pop("VIRTUAL_ENV", None)
            clean_env.pop("PYTHONPATH", None)
            # Put Bioconda at the front
            clean_env["PATH"] = dv_bin_dir + os.pathsep + clean_env.get("PATH", "")

            # Multi-step pipeline for Bioconda
            examples = os.path.join(outdir, "dv_examples.tfrecord.gz")
            call_vcf = os.path.join(outdir, "dv_calls.tfrecord.gz")
            log_dir = os.path.join(outdir, "dv_logs")
            os.makedirs(log_dir, exist_ok=True)

            # Get sample name from BAM
            sample_name = "sample"
            try:
                res = subprocess.run(
                    ["samtools", "view", "-H", args.input],
                    capture_output=True,
                    text=True,
                    env=clean_env,
                )
                for line in res.stdout.splitlines():
                    if line.startswith("@RG"):
                        for part in line.split("\t"):
                            if part.startswith("SM:"):
                                sample_name = part[3:]
                                break
            except Exception:
                pass

            # 1. Make Examples
            logging.info("DeepVariant Step 1/3: Making examples...")
            make_cmd_inner = [
                "dv_make_examples.py",
                "--cores",
                str(threads),
                "--ref",
                ref,
                "--reads",
                args.input,
                "--sample",
                sample_name,
                "--examples",
                examples,
                "--logdir",
                log_dir,
            ] + region_args

            subprocess.run(
                [
                    "conda",
                    "run",
                    "-n",
                    "wgse",
                    "--no-capture-output",
                    "bash",
                    "-c",
                    f"{' '.join(map(shlex.quote, make_cmd_inner))} < /dev/null",
                ],
                env=clean_env,
                check=True,
            )
            # 2. Call Variants
            logging.info("DeepVariant Step 2/3: Calling variants...")
            call_cmd_inner = [
                "dv_call_variants.py",
                "--cores",
                str(threads),
                "--examples",
                examples,
                "--outfile",
                call_vcf,
                "--sample",
                sample_name,
                "--model",
                model_type.lower(),
            ]
            if args.checkpoint:
                call_cmd_inner.extend(["--checkpoint", args.checkpoint])

            subprocess.run(
                [
                    "conda",
                    "run",
                    "-n",
                    "wgse",
                    "--no-capture-output",
                    "bash",
                    "-c",
                    f"{' '.join(map(shlex.quote, call_cmd_inner))} < /dev/null",
                ],
                env=clean_env,
                check=True,
            )
            # 3. Postprocess
            logging.info("DeepVariant Step 3/3: Postprocessing...")
            post_cmd_inner = [
                "dv_postprocess_variants.py",
                "--ref",
                ref,
                "--infile",
                call_vcf,
                "--outfile",
                intermediate_vcf,
            ]
            subprocess.run(
                [
                    "conda",
                    "run",
                    "-n",
                    "wgse",
                    "--no-capture-output",
                    "bash",
                    "-c",
                    f"{' '.join(map(shlex.quote, post_cmd_inner))} < /dev/null",
                ],
                env=clean_env,
                check=True,
            )
            # Cleanup intermediate tfrecords
            for f in os.listdir(outdir):
                if f.startswith("dv_examples.tfrecord") or f == "dv_calls.tfrecord.gz":
                    try:
                        os.remove(os.path.join(outdir, f))
                    except Exception:
                        pass
        else:
            # Single wrapper
            cmd = [
                "run_deepvariant",
                "--model_type",
                model_type,
                "--ref",
                ref,
                "--reads",
                args.input,
                "--output_vcf",
                intermediate_vcf,
                "--num_shards",
                threads,
            ] + region_args
            subprocess.run(cmd, check=True)

        # DeepVariant outputs plain VCF, we compress it
        if os.path.exists(intermediate_vcf):
            subprocess.run(["bgzip", "-f", intermediate_vcf], check=True)
            ensure_vcf_indexed(out_vcf)
        else:
            logging.error("DeepVariant failed to produce output VCF.")

    except Exception as e:
        logging.error(f"DeepVariant failed: {e}")
        sys.exit(1)


def cmd_chain_annotate(args):
    import shutil

    verify_dependencies(["bcftools", "tabix"])
    input_file = args.input if args.input else args.vcf_input
    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    annotations = [a.strip().lower() for a in args.annotations.split(",") if a.strip()]

    if not annotations:
        logging.error("No valid annotations provided in --annotations.")
        return

    logging.info(f"Starting chained annotation with: {', '.join(annotations)}")

    md5_sig = (
        calculate_bam_md5(input_file, None)
        if input_file.lower().endswith((".bam", ".cram"))
        else None
    )
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=input_file)

    current_input = ensure_vcf_prepared(input_file)
    intermediate_files = []

    try:
        for i, ann in enumerate(annotations):
            step_outdir = os.path.join(outdir, f"chain_step_{i + 1}_{ann}")
            os.makedirs(step_outdir, exist_ok=True)

            # Print status directly to terminal so user sees progress during silenced runs
            print(f"  ➡️  Step [{i + 1}/{len(annotations)}]: Running '{ann}'...")

            # Pre-check tool availability
            from wgsextract_cli.core.dependencies import get_tool_path

            tool_to_check = (
                "vep" if ann == "vep" else "bcftools"
            )  # most others use bcftools
            if not get_tool_path(tool_to_check):
                logging.warning(
                    f"Skipping '{ann}': Tool '{tool_to_check}' not installed."
                )
                continue

            # Pre-check data availability
            missing_data = False
            if ann == "clinvar" and not lib.clinvar_vcf:
                missing_data = True
            elif ann == "revel" and not lib.revel_file:
                missing_data = True
            elif ann == "phylop" and not lib.phylop_file:
                missing_data = True
            elif ann == "gnomad" and not lib.gnomad_vcf:
                missing_data = True
            elif ann == "spliceai" and not lib.spliceai_vcf:
                missing_data = True
            elif ann == "alphamissense" and not lib.alphamissense_vcf:
                missing_data = True
            elif ann == "pharmgkb" and not lib.pharmgkb_vcf:
                missing_data = True
            elif ann == "vep" and not lib.vep_cache:
                # VEP can run in online mode, but for chain-annotate we generally want the cache
                # Only skip if offline cache is missing? The user mentioned "haven't downloaded due to size".
                # Let's just warn if cache is missing but maybe don't skip yet?
                # Actually, the user wants a clean one-line skipped message.
                missing_data = True

            if missing_data:
                logging.warning(
                    f"Skipping '{ann}': Required reference data not found. Run 'wgsextract ref {ann}' to download."
                )
                continue

            logging.info(f"[{i + 1}/{len(annotations)}] Running '{ann}' annotation...")

            cmd = ["uv", "run", "wgsextract"]

            if ann == "vep":
                cmd.extend(["vep", "run"])
            elif ann in [
                "clinvar",
                "revel",
                "phylop",
                "gnomad",
                "spliceai",
                "alphamissense",
                "pharmgkb",
            ]:
                cmd.extend(["vcf", ann])
            else:
                logging.warning(f"Unknown annotation type '{ann}', skipping.")
                continue

            cmd.extend(["--input", current_input, "--outdir", step_outdir])

            if args.ref:
                cmd.extend(["--ref", args.ref])

            try:
                # Capture output to prevent spam during chained annotation
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as e:
                logging.warning(f"Annotation step '{ann}' failed. Skipping.")
                if e.stderr:
                    for line in e.stderr.strip().split("\n"):
                        logging.error(f"  [{ann} ERROR] {line}")
                if e.stdout:
                    for line in e.stdout.strip().split("\n"):
                        logging.debug(f"  [{ann} STDOUT] {line}")
                # Cleanup step directory if it failed
                if os.path.exists(step_outdir):
                    shutil.rmtree(step_outdir, ignore_errors=True)
                continue

            # Find the output VCF from this step
            out_files = [
                f
                for f in os.listdir(step_outdir)
                if f.endswith(".vcf.gz")
                and not f.endswith(".norm.vcf.gz")
                and "gt_" not in f
            ]

            if not out_files:
                logging.warning(f"No VCF output found for step '{ann}'. Skipping.")
                if res.stderr:
                    for line in res.stderr.strip().split("\n"):
                        logging.warning(f"  [{ann} STDERR] {line}")
                if os.path.exists(step_outdir):
                    shutil.rmtree(step_outdir, ignore_errors=True)
                continue

            # Assume the newest VCF is the result
            out_files_paths = [os.path.join(step_outdir, f) for f in out_files]
            latest_out = max(out_files_paths, key=os.path.getmtime)

            intermediate_files.append(latest_out)
            current_input = latest_out
            logging.info(f"Step '{ann}' completed. Intermediate file: {latest_out}")

        # Finalize
        final_out = os.path.join(outdir, "chain_annotated.vcf.gz")

        shutil.copy2(current_input, final_out)
        if os.path.exists(current_input + ".tbi"):
            shutil.copy2(current_input + ".tbi", final_out + ".tbi")

        logging.info(f"✅ Chain annotation complete: {final_out}")

    finally:
        if not getattr(args, "keep_intermediates", False):
            logging.info("Cleaning up intermediate files...")
            for i, ann in enumerate(annotations):
                step_outdir = os.path.join(outdir, f"chain_step_{i + 1}_{ann}")
                if os.path.exists(step_outdir):
                    shutil.rmtree(step_outdir, ignore_errors=True)
