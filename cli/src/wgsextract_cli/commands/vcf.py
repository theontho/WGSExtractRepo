import logging
import os
import shutil
import subprocess
import sys

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    ensure_vcf_indexed,
    ensure_vcf_prepared,
    get_resource_defaults,
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
    trio_parser.set_defaults(func=cmd_trio)
    trio_parser.add_argument(
        "--mode",
        choices=["denovo", "recessive", "comphet"],
        default="denovo",
        help="Inheritance mode to filter for",
    )

    cnv_parser = vcf_subs.add_parser(
        "cnv", parents=[base_parser], help=CLI_HELP["cmd_cnv"]
    )

    cnv_parser.set_defaults(func=cmd_cnv)

    sv_parser = vcf_subs.add_parser(
        "sv", parents=[base_parser], help=CLI_HELP["cmd_sv"]
    )
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
    deepvariant_parser.set_defaults(func=cmd_deepvariant)

    qc_parser = vcf_subs.add_parser(
        "qc", parents=[base_parser], help=CLI_HELP["cmd_vcf-qc"]
    )
    qc_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help=CLI_HELP["arg_vcf_input"],
    )
    qc_parser.set_defaults(func=cmd_qc)


def get_base_args(args):
    # Support multiple input argument names for different VCF commands
    input_file = (
        getattr(args, "vcf_input", None)
        or getattr(args, "input", None)
        or getattr(args, "proband", None)
    )

    if not input_file:
        logging.error(LOG_MESSAGES["input_required"])
        return None
    threads, _ = get_resource_defaults(args.threads, None)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )

    md5_sig = calculate_bam_md5(input_file, None)
    lib = ReferenceLibrary(args.ref, md5_sig)

    if not hasattr(args, "ploidy") or args.ploidy is None:
        if not hasattr(args, "ploidy_file") or args.ploidy_file is None:
            args.ploidy_file = lib.ploidy_file

    resolved_ref = lib.fasta

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

    p1 = subprocess.Popen(
        ["bcftools", "mpileup", "-B", "-I", "-C", "50", "-f", ref, "-Ou"]
        + region_args
        + [args.input],
        stdout=subprocess.PIPE,
    )
    p2 = subprocess.Popen(
        ["bcftools", "call"]
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
            logging.error(stderr.decode())
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

    p1 = subprocess.Popen(
        ["bcftools", "mpileup", "-B", "-I", "-C", "50", "-f", ref, "-Ou"]
        + region_args
        + [args.input],
        stdout=subprocess.PIPE,
    )
    p2 = subprocess.Popen(
        ["bcftools", "call"]
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
            logging.error(stderr.decode())
        return

    p3 = subprocess.Popen(
        ["bcftools", "norm", "-f", ref, "--threads", threads, "-Oz", "-o", out_vcf],
        stdin=subprocess.PIPE,
    )
    p3.communicate(input=stdout)

    if p3.returncode != 0:
        logging.error(f"bcftools norm failed with return code {p3.returncode}")
        return

    ensure_vcf_indexed(out_vcf)


def cmd_annotate(args):
    verify_dependencies(["bcftools", "tabix"])
    input_file = args.vcf_input if args.vcf_input else args.input
    if not input_file:
        return logging.error(LOG_MESSAGES["input_required"])

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
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
        lib = ReferenceLibrary(args.ref, md5_sig)
        if lib.ref_vcf_tab:
            ann_vcf = lib.ref_vcf_tab
            if not cols:
                # Default columns for All_SNPs tab files: ID,INFO/HG
                cols = "ID,INFO/HG"
            logging.info(f"Auto-resolved annotation file: {ann_vcf}")
        else:
            logging.error("--ann-vcf is required and could not be auto-resolved.")
            return

    if not cols:
        logging.error("--cols is required (e.g., ID,INFO/HG).")
        return

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
    input_file = args.vcf_input if args.vcf_input else args.input
    if not input_file:
        return logging.error(LOG_MESSAGES["input_required"])

    if not verify_paths_exist({"--input": input_file}):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    out_vcf = os.path.join(outdir, "filtered.vcf.gz")

    # Resolve reference if needed for gap filtering or gene resolution
    md5_sig = calculate_bam_md5(input_file, None)
    lib = ReferenceLibrary(args.ref, md5_sig)

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
    out_vcf = os.path.join(outdir, f"trio_{args.mode}.vcf.gz")

    logging.info(
        LOG_MESSAGES["vcf_trio_analysis"].format(mode=args.mode, output=out_vcf)
    )

    # 1. Prepare and Merge the three VCFs
    p_vcf = ensure_vcf_prepared(proband)
    m_vcf = ensure_vcf_prepared(mother)
    f_vcf = ensure_vcf_prepared(father)

    merged_vcf = os.path.join(outdir, "merged_trio.vcf.gz")
    try:
        subprocess.run(
            [
                "bcftools",
                "merge",
                "--force-samples",
                "-Oz",
                "-o",
                merged_vcf,
                p_vcf,
                m_vcf,
                f_vcf,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"❌: VCF merge failed: {e}")
        return

    # 2. Apply Inheritance Filters
    # [0] = proband, [1] = mother, [2] = father
    filter_expr = ""
    if args.mode == "denovo":
        # Child is het, parents are ref
        filter_expr = 'GT[0]="het" && GT[1]="ref" && GT[2]="ref"'
    elif args.mode == "recessive":
        # Child is hom-alt, parents are het
        filter_expr = 'GT[0]="hom" && GT[1]="het" && GT[2]="het"'
    elif args.mode == "comphet":
        # Simplified: Child is het, one parent is het, other is ref
        filter_expr = 'GT[0]="het" && ( (GT[1]="het" && GT[2]="ref") || (GT[1]="ref" && GT[2]="het") )'

    try:
        subprocess.run(
            ["bcftools", "view", "-i", filter_expr, "-Oz", "-o", out_vcf, merged_vcf],
            check=True,
        )
        ensure_vcf_indexed(out_vcf)
        logging.info(LOG_MESSAGES["vcf_trio_complete"].format(output=out_vcf))
    finally:
        if os.path.exists(merged_vcf):
            os.remove(merged_vcf)


def cmd_qc(args):
    verify_dependencies(["bcftools"])
    input_file = args.vcf_input if args.vcf_input else args.input
    if not input_file:
        logging.error("--input is required.")
        return

    if not verify_paths_exist({"--input": input_file}):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    base_name = os.path.basename(input_file)
    out_stats = os.path.join(outdir, f"{base_name}.vcfstats.txt")

    logging.info(LOG_MESSAGES["vcf_stats"].format(input=input_file, output=out_stats))
    try:
        with open(out_stats, "w") as f:
            subprocess.run(["bcftools", "stats", input_file], stdout=f, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"VCF stats failed: {e}")


def cmd_cnv(args):
    verify_dependencies(["delly", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_bcf = os.path.join(outdir, "cnv.bcf")
    out_vcf = os.path.join(outdir, "cnv.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_cnv"].format(output=out_vcf))
    try:
        # delly cnv -g ref.fa -o cnv.bcf input.bam
        # For CRAM files, delly needs the reference via -g (which we have)
        subprocess.run(
            ["delly", "cnv", "-g", ref, "-o", out_bcf, args.input], check=True
        )
        # convert bcf to vcf.gz
        subprocess.run(["bcftools", "view", "-Oz", "-o", out_vcf, out_bcf], check=True)
        ensure_vcf_indexed(out_vcf)
        if os.path.exists(out_bcf):
            os.remove(out_bcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"CNV calling failed: {e}")
        logging.error(
            "Hint: If using macOS, ensure 'delly' and 'boost' are correctly installed via Homebrew."
        )
        sys.exit(e.returncode)


def cmd_sv(args):
    verify_dependencies(["delly", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_bcf = os.path.join(outdir, "sv.bcf")
    out_vcf = os.path.join(outdir, "sv.vcf.gz")

    logging.info(LOG_MESSAGES["vcf_calling_sv"].format(output=out_vcf))
    try:
        # delly call -g ref.fa -o sv.bcf input.bam
        subprocess.run(
            ["delly", "call", "-g", ref, "-o", out_bcf, args.input], check=True
        )
        # convert bcf to vcf.gz
        subprocess.run(["bcftools", "view", "-Oz", "-o", out_vcf, out_bcf], check=True)
        ensure_vcf_indexed(out_vcf)
        if os.path.exists(out_bcf):
            os.remove(out_bcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"SV calling failed: {e}")
        logging.error(
            "Hint: If using macOS, ensure 'delly' and 'boost' are correctly installed via Homebrew."
        )
        sys.exit(e.returncode)


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
        if is_cram:
            # freebayes doesn't always handle CRAM perfectly via stdin
            view_cmd = ["samtools", "view", "-uh", "-T", use_ref, args.input]
            if args.region:
                view_cmd.extend(
                    ["-r", args.region] if "-r" not in region_args else region_args
                )

            p_view = subprocess.Popen(view_cmd, stdout=subprocess.PIPE)
            p_fb = subprocess.Popen(
                ["freebayes", "-f", use_ref, "--stdin"],
                stdin=p_view.stdout,
                stdout=subprocess.PIPE,
            )
            p_vcf = subprocess.Popen(
                ["bcftools", "view", "-Oz", "-o", out_vcf], stdin=p_fb.stdout
            )

            if p_view.stdout:
                p_view.stdout.close()
            if p_fb.stdout:
                p_fb.stdout.close()
            p_vcf.communicate()

            if p_vcf.returncode != 0:
                logging.error(
                    f"Freebayes/bcftools pipeline failed with return code {p_vcf.returncode}"
                )
        else:
            # BAM handling
            p1 = subprocess.Popen(
                ["freebayes", "-f", use_ref] + region_args + [args.input],
                stdout=subprocess.PIPE,
            )
            p2 = subprocess.Popen(
                ["bcftools", "view", "-Oz", "-o", out_vcf], stdin=p1.stdout
            )
            if p1.stdout:
                p1.stdout.close()
            p2.communicate()

            if p2.returncode != 0:
                logging.error(
                    f"Freebayes/bcftools failed with return code {p2.returncode}"
                )

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
        # Use system gatk binary
        cmd = [
            "gatk",
            "HaplotypeCaller",
            "-R",
            ref,
            "-I",
            args.input,
            "-O",
            out_vcf,
        ] + region_args
        subprocess.run(cmd, check=True)
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
    # DeepVariant can be run via:
    # 1. Official 'run_deepvariant' wrapper
    # 2. Bioconda 'dv_make_examples.py' + 'dv_call_variants.py' + 'dv_postprocess_variants.py'

    executable = shutil.which("run_deepvariant")
    use_bioconda = False

    if not executable:
        if shutil.which("dv_make_examples.py"):
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

    model_type = "WGS"
    if args.wes:
        model_type = "WES"

    region_args = ["--regions", args.region] if args.region else []

    try:
        if use_bioconda:
            # Multi-step pipeline for Bioconda
            examples = os.path.join(outdir, "dv_examples.tfrecord@" + threads + ".gz")
            call_vcf = os.path.join(outdir, "dv_calls.tfrecord.gz")

            # 1. Make Examples
            run_command(
                [
                    "dv_make_examples.py",
                    "--mode",
                    "calling",
                    "--ref",
                    ref,
                    "--reads",
                    args.input,
                    "--examples",
                    examples,
                ]
                + region_args
            )
            # 2. Call Variants
            run_command(
                [
                    "dv_call_variants.py",
                    "--examples",
                    examples,
                    "--outfile",
                    call_vcf,
                    "--checkpoint",
                    "TBD",
                ]
            )  # Need to find checkpoints
            # 3. Postprocess
            run_command(
                [
                    "dv_postprocess_variants.py",
                    "--ref",
                    ref,
                    "--infile",
                    call_vcf,
                    "--outfile",
                    intermediate_vcf,
                ]
            )
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
        subprocess.run(["bgzip", "-f", intermediate_vcf], check=True)
        ensure_vcf_indexed(out_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"DeepVariant failed: {e}")
        sys.exit(e.returncode)
