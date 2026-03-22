import hashlib
import logging
import os
import subprocess
import sys

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.gene_map import are_gene_maps_installed
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.ref_library import (
    GENOME_DATA,
    download_alphamissense,
    download_and_process_genome,
    download_clinvar,
    download_gnomad,
    download_pharmgkb,
    download_phylop,
    download_revel,
    download_spliceai,
    get_available_genomes,
    get_genome_size,
    get_genome_status,
    has_ref_ns,
)
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    resolve_reference,
    verify_paths_exist,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser("ref", help="Reference Data Management commands.")
    ref_subs = parser.add_subparsers(dest="ref_cmd", required=True)

    dl_parser = ref_subs.add_parser(
        "download", parents=[base_parser], help=CLI_HELP["cmd_ref-download"]
    )
    dl_parser.add_argument("--url", required=True, help="URL to download from")
    dl_parser.add_argument("--out", required=True, help="Output FASTA file path")
    dl_parser.set_defaults(func=cmd_download)

    index_parser = ref_subs.add_parser(
        "index", parents=[base_parser], help=CLI_HELP["cmd_ref-index"]
    )
    index_parser.set_defaults(func=cmd_index)

    cntns_parser = ref_subs.add_parser(
        "count-ns", parents=[base_parser], help=CLI_HELP["cmd_ref-count-ns"]
    )
    cntns_parser.set_defaults(func=cmd_count_ns)

    verify_parser = ref_subs.add_parser(
        "verify", parents=[base_parser], help=CLI_HELP["cmd_ref-verify"]
    )
    verify_parser.set_defaults(func=cmd_ref_verify)

    lib_parser = ref_subs.add_parser(
        "library",
        parents=[base_parser],
        help=CLI_HELP["cmd_ref-library"],
    )
    lib_parser.set_defaults(func=cmd_library)

    liblist_parser = ref_subs.add_parser(
        "library-list",
        parents=[base_parser],
        help="List all available reference genomes and their current status.",
    )
    liblist_parser.set_defaults(func=cmd_library_list)

    genemap_parser = ref_subs.add_parser(
        "gene-map", parents=[base_parser], help=CLI_HELP["cmd_ref-gene-map"]
    )
    genemap_parser.add_argument(
        "--delete", action="store_true", help="Delete gene maps instead of downloading"
    )
    genemap_parser.set_defaults(func=cmd_gene_map)

    clinvar_dl_parser = ref_subs.add_parser(
        "clinvar",
        parents=[base_parser],
        help="Download official ClinVar VCF for hg19 and hg38.",
    )
    clinvar_dl_parser.set_defaults(func=cmd_clinvar_dl)

    revel_dl_parser = ref_subs.add_parser(
        "revel",
        parents=[base_parser],
        help="Download REVEL pathogenicity scores for hg19 and hg38.",
    )
    revel_dl_parser.set_defaults(func=cmd_revel_dl)

    phylop_dl_parser = ref_subs.add_parser(
        "phylop",
        parents=[base_parser],
        help="Download PhyloP conservation scores for hg19 and hg38.",
    )
    phylop_dl_parser.set_defaults(func=cmd_phylop_dl)

    gnomad_dl_parser = ref_subs.add_parser(
        "gnomad",
        parents=[base_parser],
        help="Download gnomAD sites VCF for hg19 and hg38.",
    )
    gnomad_dl_parser.set_defaults(func=cmd_gnomad_dl)

    spliceai_dl_parser = ref_subs.add_parser(
        "spliceai",
        parents=[base_parser],
        help="Download SpliceAI precomputed scores for hg19 and hg38.",
    )
    spliceai_dl_parser.set_defaults(func=cmd_spliceai_dl)

    alphamissense_dl_parser = ref_subs.add_parser(
        "alphamissense",
        parents=[base_parser],
        help="Download AlphaMissense scores for hg19 and hg38.",
    )
    alphamissense_dl_parser.set_defaults(func=cmd_alphamissense_dl)

    pharmgkb_dl_parser = ref_subs.add_parser(
        "pharmgkb",
        parents=[base_parser],
        help="Download PharmGKB annotations.",
    )
    pharmgkb_dl_parser.set_defaults(func=cmd_pharmgkb_dl)


def cmd_download(args):
    verify_dependencies(["wget"])
    logging.info(LOG_MESSAGES["ref_downloading"].format(url=args.url, path=args.out))
    try:
        subprocess.run(["wget", "-O", args.out, args.url], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Download failed: {e}")
        sys.exit(1)


def cmd_index(args):
    verify_dependencies(["samtools", "bwa"])
    log_dependency_info(["samtools", "bwa"])
    if not args.ref:
        logging.error("--ref is required.")
        return

    if not verify_paths_exist({"--ref": args.ref}):
        return

    logging.debug(f"Resolved reference: {os.path.abspath(args.ref)}")
    logging.info(LOG_MESSAGES["ref_indexing"].format(path=args.ref))
    try:
        # 1. samtools faidx
        logging.info("Indexing FASTA with samtools faidx...")
        subprocess.run(["samtools", "faidx", args.ref], check=True)

        # 2. samtools dict
        out_dict = args.ref + ".dict"
        # Also create a version without .fa/.fasta if it's there
        out_dict_short = os.path.splitext(args.ref)[0] + ".dict"
        if out_dict_short.endswith(".fna") or out_dict_short.endswith(".fa"):
            out_dict_short = os.path.splitext(out_dict_short)[0] + ".dict"

        logging.info(LOG_MESSAGES["ref_creating_dict"].format(path=out_dict))
        subprocess.run(["samtools", "dict", args.ref, "-o", out_dict], check=True)

        if out_dict != out_dict_short:
            import shutil

            shutil.copy2(out_dict, out_dict_short)

        # 3. bwa index
        logging.info("Indexing FASTA with bwa index (required for alignment)...")
        subprocess.run(["bwa", "index", args.ref], check=True)

        logging.info("Indexing complete.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Indexing failed: {e}")
        sys.exit(1)


def cmd_count_ns(args):
    verify_dependencies(["python3"])
    if not args.ref:
        logging.error("--ref is required.")
        sys.exit(1)

    if not verify_paths_exist({"--ref": args.ref}):
        sys.exit(1)

    prog_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../program")
    )
    script = os.path.join(prog_dir, "countingNs.py")
    if not os.path.exists(script):
        logging.error("countingNs.py script not found.")
        sys.exit(1)

    logging.info(LOG_MESSAGES["analyzing_ns"].format(path=args.ref))
    try:
        temp_gz = None
        # Check if file is gzipped by looking at magic bytes
        is_gzipped = False
        with open(args.ref, "rb") as f:
            if f.read(2) == b"\x1f\x8b":
                is_gzipped = True

        script_ref = args.ref
        if not is_gzipped:
            import tempfile

            logging.info(
                "Input is not gzipped. Creating temporary gzipped version for analysis..."
            )
            # We need the .fa.gz extension for some scripts to be happy, but mostly we just need it gzipped
            temp_gz = tempfile.NamedTemporaryFile(suffix=".fa.gz", delete=False)
            temp_gz_path = temp_gz.name
            temp_gz.close()

            # Use bgzip if available, otherwise gzip
            try:
                subprocess.run(
                    ["bgzip", "-c", args.ref],
                    stdout=open(temp_gz_path, "wb"),
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                subprocess.run(
                    ["gzip", "-c", args.ref],
                    stdout=open(temp_gz_path, "wb"),
                    check=True,
                )

            script_ref = temp_gz_path
            # Match countingNs.py logic for dict file naming
            temp_dict = (
                script_ref.replace(".fasta.gz", "")
                .replace(".fna.gz", "")
                .replace(".fa.gz", "")
                + ".dict"
            )
            orig_dict = args.ref + ".dict"
            if not os.path.exists(orig_dict):
                orig_dict = os.path.splitext(args.ref)[0] + ".dict"

            if os.path.exists(orig_dict):
                import shutil

                shutil.copy2(orig_dict, temp_dict)

        subprocess.run([sys.executable, script, script_ref], check=True)

        if temp_gz:
            os.remove(temp_gz_path)
            # Clean up the temp dict we created
            temp_dict_to_remove = (
                script_ref.replace(".fasta.gz", "")
                .replace(".fna.gz", "")
                .replace(".fa.gz", "")
                + ".dict"
            )
            if os.path.exists(temp_dict_to_remove):
                os.remove(temp_dict_to_remove)
            # Also clean up outputs generated by countingNs.py in the temp dir
            for suffix in ["_ncnt.csv", "_nbin.csv"]:
                out_file = (
                    script_ref.replace(".fasta.gz", "")
                    .replace(".fna.gz", "")
                    .replace(".fa.gz", "")
                    + suffix
                )
                if os.path.exists(out_file):
                    os.remove(out_file)

    except subprocess.CalledProcessError as e:
        logging.error(f"N-counting failed: {e}")
        sys.exit(1)


def cmd_ref_verify(args):
    verify_dependencies(["gzip", "samtools"])
    log_dependency_info(["gzip", "samtools"])
    if not args.ref:
        logging.error("--ref is required.")
        sys.exit(1)

    # Auto-resolve ref if a directory was provided
    resolved_ref = resolve_reference(args.ref, "")
    logging.debug(f"Resolved reference: {resolved_ref}")
    if not os.path.exists(resolved_ref):
        logging.error(f"Reference file not found: {resolved_ref}")
        sys.exit(1)

    logging.info(LOG_MESSAGES["ref_verifying"].format(path=resolved_ref))

    # 1. MD5 Checksum (if known)
    filename = os.path.basename(resolved_ref)
    expected_md5 = None
    for g in GENOME_DATA:
        if g["final"] == filename:
            expected_md5 = g.get("md5")
            break

    if expected_md5:
        logging.info(LOG_MESSAGES["ref_md5_verifying"].format(filename=filename))
        hash_md5 = hashlib.md5()
        try:
            with open(resolved_ref, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            calculated = hash_md5.hexdigest()
            if calculated == expected_md5:
                logging.info(LOG_MESSAGES["ref_md5_ok"])
            else:
                logging.error(LOG_MESSAGES["ref_md5_failed"])
                logging.error(f"Expected: {expected_md5}")
                logging.error(f"Calculated: {calculated}")
                # We continue to show other potential errors (like gzip eof)
        except Exception as e:
            logging.error(f"MD5 verification failed to run: {e}")

    # 2. Check gzip integrity
    if resolved_ref.endswith(".gz"):
        logging.info(LOG_MESSAGES["ref_gzip_test"])
        try:
            subprocess.run(
                ["gzip", "-t", resolved_ref], check=True, stderr=subprocess.PIPE
            )
            logging.info(LOG_MESSAGES["ref_gzip_ok"])
        except subprocess.CalledProcessError as e:
            msg = e.stderr.decode() if e.stderr else "Unexpected end of file"
            logging.error(f"Gzip integrity FAILED: {msg}")
            return
        except Exception as e:
            logging.error(f"Gzip test failed: {e}")
            return

    # 2. Check samtools faidx
    logging.info(LOG_MESSAGES["ref_faidx_check"])
    try:
        # Check if index exists, if not try to create/verify
        res = subprocess.run(
            ["samtools", "faidx", resolved_ref], capture_output=True, text=True
        )
        if res.returncode == 0:
            logging.info(LOG_MESSAGES["ref_faidx_ok"])
        else:
            logging.error(f"Samtools faidx FAILED: {res.stderr}")
            return
    except Exception as e:
        logging.error(f"Samtools faidx check failed: {e}")
        return

    logging.info(
        LOG_MESSAGES["ref_valid"].format(filename=os.path.basename(resolved_ref))
    )


def cmd_library_list(args):
    """Non-interactive library status list."""
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib_dir = args.ref if args.ref else os.path.join(prog_root, "reference")
    reflib_dir = os.path.abspath(reflib_dir)

    genomes = get_available_genomes()

    print(f"\nREFERENCE LIBRARY: {reflib_dir}")
    print("-" * 80)
    print(f"{'GENOME':<40} {'STATUS':<15} {'SIZE':<10} {'DETAILS'}")
    print("-" * 80)

    for g in genomes:
        status = get_genome_status(g["final"], reflib_dir).upper()
        size = get_genome_size(g["final"], reflib_dir)

        details = []
        if has_ref_ns(g["final"], reflib_dir):
            details.append("N-counts")

        # Check for VEP cache
        bn = g["final"].upper()
        species = ""
        assembly = ""
        if "38" in bn or "HG38" in bn or "GRCH38" in bn:
            assembly = "GRCh38"
            species = "homo_sapiens"
        elif "37" in bn or "HG19" in bn or "GRCH37" in bn:
            assembly = "GRCh37"
            species = "homo_sapiens"
        elif "GSD" in bn or "DOG" in bn:
            species = "canis_lupus_familiaris"
        elif "FCA126" in bn or "CAT" in bn:
            species = "felis_catus"

        if species:
            vep_path = os.path.join(reflib_dir, "vep", species)
            if os.path.exists(vep_path):
                # If human, check for specific assembly
                if species == "homo_sapiens" and assembly:
                    # Look for any directory starting with [version]_[assembly]
                    found_asm = False
                    if os.path.isdir(vep_path):
                        for d in os.listdir(vep_path):
                            if assembly in d:
                                found_asm = True
                                break
                    if found_asm:
                        details.append(f"VEP-{assembly}")
                else:
                    details.append("VEP-Cache")

        details_str = ", ".join(details)
        print(f"{g['label']:<40} {status:<15} {size:<10} {details_str}")

    print("-" * 80)
    gm_installed = "INSTALLED" if are_gene_maps_installed(reflib_dir) else "MISSING"
    print(f"{'Gene Maps (hg19/hg38)':<40} {gm_installed}")

    # Check for ClinVar, REVEL, gnomAD
    ref_dir = os.path.join(reflib_dir, "ref")
    for build in ["hg19", "hg38"]:
        cv = (
            "INSTALLED"
            if os.path.exists(os.path.join(ref_dir, f"clinvar_{build}.vcf.gz"))
            else "MISSING"
        )
        print(f"{f'ClinVar ({build})':<40} {cv}")
        rv = (
            "INSTALLED"
            if os.path.exists(os.path.join(ref_dir, f"revel_{build}.tsv.gz"))
            else "MISSING"
        )
        print(f"{f'REVEL ({build})':<40} {rv}")
        ph = (
            "INSTALLED"
            if os.path.exists(os.path.join(ref_dir, f"phylop_{build}.tsv.gz"))
            else "MISSING"
        )
        print(f"{f'PhyloP ({build})':<40} {ph}")
        gn = (
            "INSTALLED"
            if any(
                os.path.exists(os.path.join(ref_dir, f"gnomad_{build}{ext}"))
                for ext in [".vcf.bgz", ".vcf.gz"]
            )
            else "MISSING"
        )
        print(f"{f'gnomAD ({build})':<40} {gn}")

    print("-" * 80)


def cmd_library(args):
    """Interactive library manager."""
    deps = ["curl", "samtools", "bcftools", "tabix", "bgzip", "htsfile"]
    verify_dependencies(deps)
    log_dependency_info(deps)

    genomes = get_available_genomes()

    # Determine reference library directory
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib_dir = args.ref if args.ref else os.path.join(prog_root, "reference")
    reflib_dir = os.path.abspath(reflib_dir)

    print("\n" + "=" * 80)
    print("WGS Extract Reference Library Manager")
    print(f"Library Path: {reflib_dir}")
    print("=" * 80)
    print("Select an option:")
    print(" 0) Exit")
    print(" G) Gene Map (hg19/hg38)")
    print(" C) ClinVar (hg19/hg38)")
    print(" R) REVEL (hg19/hg38)")
    print(" P) PhyloP (hg19/hg38)")
    print(" N) gnomAD (hg19/hg38)")
    print(" S) SpliceAI (hg19/hg38)")
    print(" A) AlphaMissense (hg19/hg38)")
    print(" K) PharmGKB")

    # Check for installed genomes
    for i, g in enumerate(genomes, 1):
        s = get_genome_status(g["final"], reflib_dir)
        status = ""
        if s == "installed":
            status = " [Installed]"
        elif s == "incomplete":
            status = " [Incomplete]"
        print(f" {i:2}) {g['label']}{status}")
    print("=" * 80)

    try:
        choice = input("\nEnter choice (number or G): ").strip().upper()
        if not choice or choice == "0":
            print("Exiting library manager.")
            return

        if choice == "G":
            from wgsextract_cli.core.gene_map import (
                are_gene_maps_installed,
                delete_gene_maps,
                download_gene_maps,
            )

            if are_gene_maps_installed(reflib_dir):
                confirm = input("Gene maps already installed. Delete? (y/n): ").lower()
                if confirm == "y":
                    if delete_gene_maps(reflib_dir):
                        print("Gene maps deleted.")
                    else:
                        print("Deletion failed.")
            else:
                download_gene_maps(reflib_dir)
            return

        if choice == "C":
            from wgsextract_cli.core.ref_library import download_clinvar

            download_clinvar(reflib_dir)
            return

        if choice == "R":
            from wgsextract_cli.core.ref_library import download_revel

            download_revel(reflib_dir)
            return

        if choice == "P":
            from wgsextract_cli.core.ref_library import download_phylop

            download_phylop(reflib_dir)
            return

        if choice == "N":
            from wgsextract_cli.core.ref_library import download_gnomad

            download_gnomad(reflib_dir)
            return

        if choice == "S":
            from wgsextract_cli.core.ref_library import download_spliceai

            download_spliceai(reflib_dir)
            return

        if choice == "A":
            from wgsextract_cli.core.ref_library import download_alphamissense

            download_alphamissense(reflib_dir)
            return

        if choice == "K":
            from wgsextract_cli.core.ref_library import download_pharmgkb

            download_pharmgkb(reflib_dir)
            return

        idx = int(choice) - 1
        if 0 <= idx < len(genomes):
            if not os.path.exists(reflib_dir):
                os.makedirs(reflib_dir, exist_ok=True)

            download_and_process_genome(genomes[idx], reflib_dir)
        else:
            print("Invalid choice.")
    except (ValueError, EOFError, KeyboardInterrupt):
        print("\nExiting library manager.")


def cmd_gene_map(args):
    from wgsextract_cli.core.gene_map import delete_gene_maps, download_gene_maps

    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    if getattr(args, "delete", False):
        if delete_gene_maps(reflib):
            print(LOG_MESSAGES["del_genemap_success"])
        else:
            print(LOG_MESSAGES["del_genemap_failed"])
    else:
        if download_gene_maps(reflib):
            print(LOG_MESSAGES["dl_genemap_success"])
        else:
            print(LOG_MESSAGES["dl_genemap_failed"])


def cmd_clinvar_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting ClinVar download and indexing...")
    if download_clinvar(reflib):
        logging.info("ClinVar setup complete.")
    else:
        logging.error("ClinVar setup failed.")
        sys.exit(1)


def cmd_revel_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting REVEL download and indexing...")
    if download_revel(reflib):
        logging.info("REVEL setup complete.")
    else:
        logging.error("REVEL setup failed.")
        sys.exit(1)


def cmd_phylop_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting PhyloP download and indexing...")
    if download_phylop(reflib):
        logging.info("PhyloP setup complete.")
    else:
        logging.error("PhyloP setup failed.")
        sys.exit(1)


def cmd_gnomad_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting gnomAD download and indexing...")
    if download_gnomad(reflib):
        logging.info("gnomAD setup complete.")
    else:
        logging.error("gnomAD setup failed.")
        sys.exit(1)


def cmd_spliceai_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting SpliceAI download and indexing...")
    if download_spliceai(reflib):
        logging.info("SpliceAI setup complete.")
    else:
        logging.error("SpliceAI setup failed.")
        sys.exit(1)


def cmd_alphamissense_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting AlphaMissense download and indexing...")
    if download_alphamissense(reflib):
        logging.info("AlphaMissense setup complete.")
    else:
        logging.error("AlphaMissense setup failed.")
        sys.exit(1)


def cmd_pharmgkb_dl(args):
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    reflib = os.environ.get("WGSE_REFLIB")
    if not reflib:
        reflib = args.ref if args.ref else os.path.join(prog_root, "reference")

    logging.info("Starting PharmGKB download...")
    if download_pharmgkb(reflib):
        logging.info("PharmGKB setup complete.")
    else:
        logging.error("PharmGKB setup failed.")
        sys.exit(1)
