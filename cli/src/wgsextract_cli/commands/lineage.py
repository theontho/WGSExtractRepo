import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import (
    get_tool_path,
    log_dependency_info,
    verify_dependencies,
)
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    get_chr_name,
    get_resource_defaults,
    get_vcf_build,
    get_vcf_chr_name,
    popen,
    run_command,
    verify_paths_exist,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser("lineage", help="Executes Yleaf or Haplogrep.")
    lin_subs = parser.add_subparsers(dest="lin_cmd", required=True)

    ydna_parser = lin_subs.add_parser(
        "y-haplogroup", parents=[base_parser], help=CLI_HELP["cmd_lineage-y-haplogroup"]
    )
    ydna_parser.add_argument(
        "--yleaf-path", help="Path to yleaf.py (optional if in PATH)"
    )
    ydna_parser.add_argument("--pos-file", help="Yleaf position file (optional)")
    ydna_parser.add_argument(
        "--extra-args", help="Extra arguments to pass to Yleaf (e.g. -force)"
    )
    ydna_parser.set_defaults(func=cmd_ydna)

    mtdna_parser = lin_subs.add_parser(
        "mt-haplogroup",
        parents=[base_parser],
        help=CLI_HELP["cmd_lineage-mt-haplogroup"],
    )
    mtdna_parser.add_argument(
        "--haplogrep-path",
        help="Path to haplogrep executable or JAR (optional if in PATH)",
    )
    mtdna_parser.set_defaults(func=cmd_mtdna)


def update_yleaf_config(yleaf_path, ref_path, build):
    """
    Attempts to update yleaf's config.txt to point to the local reference library.
    """
    try:
        if not yleaf_path or not ref_path:
            return

        # 1. Identify where config.txt lives.
        # It usually lives in the same folder as Yleaf.py in site-packages
        # or relative to the executable if it's a wrapper.
        yleaf_dir = None
        if os.path.isfile(yleaf_path):
            # Check if it's in a bin folder of a conda env
            if "/bin/yleaf" in yleaf_path:
                # Look for site-packages path
                env_root = yleaf_path.split("/bin/yleaf")[0]
                # Walk to find yleaf/config.txt
                for d, _, files in os.walk(env_root):
                    if "config.txt" in files and "yleaf" in d:
                        yleaf_dir = d
                        break
            else:
                yleaf_dir = os.path.dirname(yleaf_path)

        if not yleaf_dir:
            return

        config_path = os.path.join(yleaf_dir, "config.txt")
        if not os.path.exists(config_path):
            # Try one level up if in a sub-package
            config_path = os.path.join(os.path.dirname(yleaf_dir), "config.txt")
            if not os.path.exists(config_path):
                return

        # 2. Resolve the actual FASTA file from the reference library
        lib = ReferenceLibrary(ref_path)
        # Search explicitly for the build requested if not direct file
        fasta_path = None
        if os.path.isfile(ref_path):
            fasta_path = ref_path
        else:
            # Look for hg38 or hg19 specific fasta in the root
            for f in os.listdir(ref_path):
                f_up = f.upper()
                if build.upper() in f_up and f.endswith(
                    (".fa", ".fasta", ".fna", ".fa.gz", ".fasta.gz", ".fna.gz")
                ):
                    fasta_path = os.path.join(ref_path, f)
                    break

        if not fasta_path:
            fasta_path = lib.fasta

        if not fasta_path:
            return

        # 3. Read and update the config
        with open(config_path) as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if build == "hg19" and line.startswith("full hg19 genome fasta location"):
                new_lines.append(f"full hg19 genome fasta location = {fasta_path}\n")
            elif build == "hg38" and line.startswith("full hg38 genome fasta location"):
                new_lines.append(f"full hg38 genome fasta location = {fasta_path}\n")
            else:
                new_lines.append(line)

        with open(config_path, "w") as f:
            f.writelines(new_lines)

        logging.info(f"Updated yleaf config.txt to use reference: {fasta_path}")

    except Exception as e:
        logging.debug(f"Failed to update yleaf config: {e}")


def cmd_ydna(args):
    # Check dependencies
    if not args.yleaf_path:
        verify_dependencies(["yleaf"])
    log_dependency_info(["yleaf"])

    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    yleaf_path = args.yleaf_path or get_tool_path("yleaf")

    if not verify_paths_exist({"--input": args.input, "--yleaf-path": yleaf_path}):
        import sys

        sys.exit(1)

    logging.debug(f"Input file: {os.path.abspath(args.input)}")
    logging.debug(f"Output directory: {os.path.abspath(args.outdir)}")

    # Build detection for -rg
    build = None
    if args.input.lower().endswith((".vcf", ".vcf.gz")):
        build = get_vcf_build(args.input)

    if not build:
        md5_sig = calculate_bam_md5(args.input, None)
        lib = ReferenceLibrary(args.ref, md5_sig)
        build = lib.build or "hg38"

    if build not in ["hg19", "hg38"]:
        logging.warning(f"Build {build} not supported by Yleaf, defaulting to hg38")
        build = "hg38"

    if args.ref:
        logging.debug(f"Resolved reference: {args.ref}")
        update_yleaf_config(yleaf_path, args.ref, build)

    logging.info(LOG_MESSAGES["running_yleaf"].format(input=args.input))
    temp_vcf = None
    try:
        import shlex

        # Check if yleaf_path is a python script or a wrapper
        cmd = shlex.split(yleaf_path)
        if yleaf_path.endswith(".py"):
            cmd = ["python3", yleaf_path]

        # Map input type to flag (Yleaf 3.2.1 style)
        input_ext = args.input.lower()
        input_file = args.input
        if input_ext.endswith(".bam"):
            input_flag = "-bam"
        elif input_ext.endswith(".cram"):
            input_flag = "-cram"
        elif input_ext.endswith((".vcf", ".vcf.gz")):
            input_flag = "-vcf"
            # Filter VCF to main Y chromosome to avoid "Multiple Y-chromosome annotations" error
            chr_y = get_vcf_chr_name(args.input, "Y")
            logging.info(f"Filtering VCF to {chr_y} for Yleaf...")

            # Use a space-free path in /tmp to avoid shell quoting bugs in Yleaf
            import tempfile

            temp_dir = tempfile.mkdtemp(prefix="yleaf_")
            temp_vcf = os.path.join(temp_dir, "input.vcf.gz")

            bcftools = get_tool_path("bcftools")
            bgzip = get_tool_path("bgzip")

            run_command(
                [bcftools, "view", "-r", chr_y, "-Oz", "-o", temp_vcf, args.input]
            )
            # Force lowercase 'chry' in both header and body using sed for maximum compatibility
            # because some bcftools versions might handle --rename-chrs differently with temp files.
            # We use a temp file for sed output then move it back.
            sed_vcf = temp_vcf + ".sed.gz"
            # Note: sed is usually a system tool, but bgzip might be from Pixi
            import shlex

            bgzip_list = shlex.split(bgzip)
            bgzip_bin = bgzip_list[0]
            # If bgzip is 'pixi run -e default bgzip', we need to be careful with redirection
            # But run_command handles it if we pass it as a list.
            # For shell=True pipes, it's harder. Let's use a more robust way.

            # Alternative: use python to do the sed-like replacement to avoid shell escaping issues
            import gzip

            with gzip.open(temp_vcf, "rt") as f_in, gzip.open(sed_vcf, "wt") as f_out:
                for line in f_in:
                    if line.startswith(f"{chr_y}\t"):
                        f_out.write(line.replace(f"{chr_y}\t", "chry\t", 1))
                    elif line.startswith("##contig=<ID=" + chr_y):
                        f_out.write(line.replace("ID=" + chr_y, "ID=chry", 1))
                    else:
                        f_out.write(line)

            os.rename(sed_vcf, temp_vcf)
            run_command([bcftools, "index", "-t", temp_vcf])

            input_file = temp_vcf
            logging.debug(f"Created shell-safe temp_vcf at: {temp_vcf}")
        elif input_ext.endswith((".fastq", ".fastq.gz", ".fq", ".fq.gz")):
            input_flag = "-fastq"
        else:
            # Fallback to -input for older versions
            input_flag = "-input"

        # Use absolute path for outdir to be safe
        outdir_abs = os.path.abspath(args.outdir)
        os.makedirs(outdir_abs, exist_ok=True)

        threads, _ = get_resource_defaults(args.threads, None)
        final_cmd = cmd + [
            input_flag,
            input_file,
            "-rg",
            build,
            "-o",
            outdir_abs,
            "-force",
            "-t",
            str(threads),
        ]

        # Add reference for CRAM if available
        if input_flag == "-cram":
            md5_sig = calculate_bam_md5(args.input, None)
            lib = ReferenceLibrary(args.ref, md5_sig)
            if lib.fasta:
                final_cmd.extend(["-cr", lib.fasta])
            elif args.ref and os.path.isfile(args.ref):
                # If --ref is a direct file, use it as the CRAM reference
                final_cmd.extend(["-cr", args.ref])

        # Add -pos if provided (legacy)
        if args.pos_file:
            final_cmd.extend(["-pos", args.pos_file])

        # Add extra args if provided
        if args.extra_args:
            import shlex

            extra = shlex.split(args.extra_args)
            # Remove -force from extra if it's already there to avoid duplicates
            # though Yleaf likely doesn't mind
            final_cmd.extend([a for a in extra if a != "-force"])

        # Execute and WAIT explicitly
        run_command(final_cmd)
        logging.debug("Yleaf execution finished successfully")

    except Exception as e:
        logging.error(f"Yleaf failed: {e}")
        import sys

        sys.exit(1)
    finally:
        if temp_vcf and os.path.exists(temp_vcf):
            try:
                # If we used a temp_dir in /tmp, remove the whole thing
                temp_dir = os.path.dirname(temp_vcf)
                if "/yleaf_" in temp_dir:
                    import shutil

                    shutil.rmtree(temp_dir)
                else:
                    os.remove(temp_vcf)
                    if os.path.exists(temp_vcf + ".tbi"):
                        os.remove(temp_vcf + ".tbi")
                    if os.path.exists(temp_vcf + ".csi"):
                        os.remove(temp_vcf + ".csi")
            except Exception:
                pass


def cmd_mtdna(args):
    # Check dependencies
    if not args.haplogrep_path:
        verify_dependencies(["haplogrep", "bcftools"])
    log_dependency_info(["haplogrep", "bcftools"])

    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    haplogrep_path = args.haplogrep_path or get_tool_path("haplogrep")

    if not verify_paths_exist(
        {"--input": args.input, "--haplogrep-path": haplogrep_path}
    ):
        import sys

        sys.exit(1)

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    logging.debug(f"Input file: {os.path.abspath(args.input)}")
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    out_file = os.path.join(outdir, "haplogrep_results.txt")

    input_file = args.input
    temp_vcf = None

    try:
        is_vcf = input_file.lower().endswith((".vcf", ".vcf.gz"))
        is_alignment = input_file.lower().endswith((".bam", ".cram"))

        if is_alignment:
            logging.info(
                "Input is alignment. Extracting mitochondrial variants first..."
            )
            temp_vcf = os.path.join(outdir, "temp_haplogrep_input.vcf.gz")

            threads, _ = get_resource_defaults(args.threads, None)
            md5_sig = calculate_bam_md5(input_file, None)
            lib = ReferenceLibrary(args.ref, md5_sig)
            if not lib.fasta:
                logging.error(
                    "Reference genome required to call mitochondrial variants."
                )
                return

            logging.debug(f"Resolved reference: {lib.fasta}")

            cram_opt = ["-T", lib.fasta] if input_file.lower().endswith(".cram") else []
            chr_m = get_chr_name(input_file, "MT", cram_opt)

            # Fast variant calling for MT region
            bcftools = get_tool_path("bcftools")
            p1 = popen(
                [
                    bcftools,
                    "mpileup",
                    "-Ou",
                    "-r",
                    chr_m,
                    "-f",
                    lib.fasta,
                    input_file,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            p2 = popen(
                [bcftools, "call", "-mv", "-Oz", "-o", temp_vcf],
                stdin=p1.stdout,
                stderr=subprocess.DEVNULL,
            )
            if p1.stdout:
                p1.stdout.close()
            p2.communicate()

            if p2.returncode != 0:
                logging.error("Failed to extract mitochondrial variants.")
                return
            input_file = temp_vcf

        elif is_vcf:
            # Filter VCF to chrM to avoid Haplogrep errors on large VCFs
            chr_m = get_vcf_chr_name(input_file, "MT")
            logging.info(f"Filtering VCF to {chr_m} for Haplogrep...")
            temp_vcf = os.path.join(outdir, "temp_haplogrep_filtered.vcf.gz")

            bcftools = get_tool_path("bcftools")
            run_command(
                [bcftools, "view", "-r", chr_m, "-Oz", "-o", temp_vcf, input_file]
            )
            input_file = temp_vcf

        logging.info(LOG_MESSAGES["running_haplogrep"].format(input=input_file))
        # Check if it's a JAR or a wrapper
        if haplogrep_path.endswith(".jar"):
            verify_dependencies(["java"])
            java = get_tool_path("java")
            cmd = [java, "-jar", haplogrep_path]
        else:
            # haplogrep_path might already be a 'pixi run' string
            import shlex

            cmd = shlex.split(haplogrep_path)

        run_command(
            cmd
            + [
                "classify",
                "--format",
                "vcf",
                "--in",
                input_file,
                "--out",
                out_file,
            ]
        )
    except Exception as e:
        logging.error(f"Haplogrep failed: {e}")
        import sys

        sys.exit(1)
    finally:
        if temp_vcf and os.path.exists(temp_vcf):
            try:
                os.remove(temp_vcf)
                if os.path.exists(temp_vcf + ".tbi"):
                    os.remove(temp_vcf + ".tbi")
            except Exception:
                pass
