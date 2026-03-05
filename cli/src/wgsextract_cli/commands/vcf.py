import logging
import os
import shutil
import subprocess

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.help_texts import HELP_TEXTS
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    ensure_vcf_indexed,
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
        "snp", parents=[base_parser], help=HELP_TEXTS["snp"]
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
        "indel", parents=[base_parser], help=HELP_TEXTS["indel"]
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
        "annotate", parents=[base_parser], help=HELP_TEXTS["annotate"]
    )
    annotate_parser.add_argument(
        "--ann-vcf", help="Annotation VCF file (auto-resolved from --ref if possible)"
    )
    annotate_parser.add_argument("--cols", help="Columns to annotate (e.g. ID,INFO/HG)")
    annotate_parser.set_defaults(func=cmd_annotate)

    filter_parser = vcf_subs.add_parser(
        "filter", parents=[base_parser], help=HELP_TEXTS["filter"]
    )
    filter_parser.add_argument(
        "--expr", help="bcftools filter expression (e.g. 'QUAL>30')"
    )
    filter_parser.add_argument("--gene", help="Filter by Gene Name (e.g. BRCA1, KCNQ2)")
    filter_parser.add_argument("-r", "--region", help="Chromosomal region")
    filter_parser.set_defaults(func=cmd_filter)

    trio_parser = vcf_subs.add_parser(
        "trio", parents=[base_parser], help=HELP_TEXTS["trio"]
    )
    trio_parser.add_argument("--proband", required=True, help="VCF file for the child")
    trio_parser.add_argument("--mother", required=True, help="VCF file for the mother")
    trio_parser.add_argument("--father", required=True, help="VCF file for the father")
    trio_parser.add_argument(
        "--mode",
        choices=["denovo", "recessive", "comphet"],
        default="denovo",
        help="Inheritance mode to filter for",
    )
    trio_parser.set_defaults(func=cmd_trio)

    cnv_parser = vcf_subs.add_parser(
        "cnv", parents=[base_parser], help=HELP_TEXTS["cnv"]
    )
    cnv_parser.set_defaults(func=cmd_cnv)

    sv_parser = vcf_subs.add_parser("sv", parents=[base_parser], help=HELP_TEXTS["sv"])
    sv_parser.set_defaults(func=cmd_sv)

    freebayes_parser = vcf_subs.add_parser(
        "freebayes", parents=[base_parser], help=HELP_TEXTS["freebayes"]
    )
    freebayes_parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)"
    )
    freebayes_parser.set_defaults(func=cmd_freebayes)

    gatk_parser = vcf_subs.add_parser(
        "gatk", parents=[base_parser], help=HELP_TEXTS["gatk"]
    )
    gatk_parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM)")
    gatk_parser.set_defaults(func=cmd_gatk)

    deepvariant_parser = vcf_subs.add_parser(
        "deepvariant", parents=[base_parser], help=HELP_TEXTS["deepvariant"]
    )
    deepvariant_parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM)"
    )
    deepvariant_parser.add_argument(
        "--wes", action="store_true", help="Set model type to WES (default: WGS)"
    )
    deepvariant_parser.set_defaults(func=cmd_deepvariant)

    qc_parser = vcf_subs.add_parser(
        "qc", parents=[base_parser], help=HELP_TEXTS["vcf-qc"]
    )
    qc_parser.set_defaults(func=cmd_qc)


def get_base_args(args):
    # For trio, input comes from --proband
    input_file = getattr(args, "input", None) or getattr(args, "proband", None)

    if not input_file:
        logging.error("--input is required.")
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
        logging.error("--ref is required (and must be a file) for variant calling.")
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

    logging.info(f"Calling SNPs to {out_vcf}")
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

    logging.info(f"Calling InDels to {out_vcf}")
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
    if not args.input:
        return logging.error("--input is required.")

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    out_vcf = os.path.join(outdir, "annotated.vcf.gz")

    ann_vcf = args.ann_vcf
    cols = args.cols

    if not ann_vcf:
        # Try to auto-resolve from reference library
        md5_sig = (
            calculate_bam_md5(args.input, None)
            if args.input.lower().endswith((".bam", ".cram"))
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

    if not verify_paths_exist({"--input": args.input, "--ann-vcf": ann_vcf}):
        return

    ensure_vcf_indexed(args.input)
    ensure_vcf_indexed(ann_vcf)

    logging.info(f"Annotating {args.input} to {out_vcf}")
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
                args.input,
            ],
            check=True,
        )
        ensure_vcf_indexed(out_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"Annotation failed: {e}")


def cmd_filter(args):
    verify_dependencies(["bcftools", "tabix"])
    if not args.input:
        return logging.error("--input is required.")

    if not verify_paths_exist({"--input": args.input}):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    out_vcf = os.path.join(outdir, "filtered.vcf.gz")

    # Gene-based region resolution
    region = args.region
    if args.gene:
        # Deduce build from input
        md5_sig = calculate_bam_md5(args.input, None)
        lib = ReferenceLibrary(args.ref, md5_sig)

        from wgsextract_cli.core.gene_map import GeneMap

        gm = GeneMap(
            lib.root if lib.root else os.path.dirname(os.path.abspath(args.input))
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

    ensure_vcf_indexed(args.input)
    logging.info(f"Filtering {args.input} to {out_vcf}")
    try:
        subprocess.run(
            ["bcftools", "view"]
            + region_args
            + expr_args
            + ["-Oz", "-o", out_vcf, args.input],
            check=True,
        )
        ensure_vcf_indexed(out_vcf)
    except subprocess.CalledProcessError as e:
        logging.error(f"Filtering failed: {e}")


def cmd_trio(args):
    verify_dependencies(["bcftools", "tabix"])
    if not verify_paths_exist(
        {"--proband": args.proband, "--mother": args.mother, "--father": args.father}
    ):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.proband))
    )
    out_vcf = os.path.join(outdir, f"trio_{args.mode}.vcf.gz")

    logging.info(f"Performing Trio Analysis ({args.mode}) to {out_vcf}")

    # 1. Merge the three VCFs (ensures they are indexed)
    for f in [args.proband, args.mother, args.father]:
        ensure_vcf_indexed(f)

    merged_vcf = os.path.join(outdir, "merged_trio.vcf.gz")
    subprocess.run(
        [
            "bcftools",
            "merge",
            "--force-samples",
            "-Oz",
            "-o",
            merged_vcf,
            args.proband,
            args.mother,
            args.father,
        ],
        check=True,
    )

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
        logging.info(f"Trio analysis complete. Results: {out_vcf}")
    finally:
        if os.path.exists(merged_vcf):
            os.remove(merged_vcf)


def cmd_qc(args):
    verify_dependencies(["bcftools"])
    if not args.input:
        logging.error("--input is required.")
        return

    if not verify_paths_exist({"--input": args.input}):
        return

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    out_stats = os.path.join(outdir, "vcf_stats.txt")

    logging.info(f"Running bcftools stats on {args.input} to {out_stats}")
    try:
        with open(out_stats, "w") as f:
            subprocess.run(["bcftools", "stats", args.input], stdout=f, check=True)
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

    logging.info(f"Calling CNVs using delly to {out_vcf}")
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
        raise


def cmd_sv(args):
    verify_dependencies(["delly", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_bcf = os.path.join(outdir, "sv.bcf")
    out_vcf = os.path.join(outdir, "sv.vcf.gz")

    logging.info(f"Calling SVs using delly to {out_vcf}")
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
        raise


def cmd_freebayes(args):
    verify_dependencies(["freebayes", "bcftools", "tabix"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_vcf = os.path.join(outdir, "freebayes.vcf.gz")

    logging.info(f"Calling variants using freebayes to {out_vcf}")
    region_args = ["-r", args.region] if args.region else []

    # Check if input is CRAM
    is_cram = args.input.lower().endswith(".cram")

    try:
        if is_cram:
            # freebayes doesn't always handle CRAM perfectly via stdin or without explicit reference handling in some versions
            # We use samtools view to pipe decompressed BAM to freebayes
            view_cmd = ["samtools", "view", "-uh", "-T", ref, args.input]
            if args.region:
                view_cmd.extend(
                    ["-r", args.region] if "-r" not in region_args else region_args
                )

            p_view = subprocess.Popen(view_cmd, stdout=subprocess.PIPE)
            p_fb = subprocess.Popen(
                ["freebayes", "-f", ref, "--stdin"],
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
                raise subprocess.CalledProcessError(
                    p_vcf.returncode, "freebayes pipeline"
                )
        else:
            # BAM handling
            p1 = subprocess.Popen(
                ["freebayes", "-f", ref] + region_args + [args.input],
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
                raise subprocess.CalledProcessError(p2.returncode, "freebayes")

        ensure_vcf_indexed(out_vcf)
    except Exception as e:
        logging.error(f"Freebayes failed: {e}")
        raise


def cmd_gatk(args):
    from wgsextract_cli.core.dependencies import get_jar_path

    verify_dependencies(["java", "samtools", "gatk-package-4.1.9.0-local.jar"])
    base = get_base_args(args)
    if not base:
        return
    threads, outdir, ref, lib = base

    out_vcf = os.path.join(outdir, "gatk.vcf.gz")
    jar = get_jar_path("gatk-package-4.1.9.0-local.jar")

    # GATK requires a .dict file
    if not lib.dict_file:
        logging.info("GATK .dict file not found. Generating...")
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

    logging.info(f"Calling variants using GATK HaplotypeCaller to {out_vcf}")
    region_args = ["-L", args.region] if args.region else []

    try:
        # Note: -Xmx4g is a safe default for local workstation
        cmd = [
            "java",
            "-Xmx4g",
            "-jar",
            jar,
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
        raise


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

    logging.info(f"Calling variants using DeepVariant to {out_vcf}")

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
        raise
