import hashlib
import logging
import os
import subprocess
import sys

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.ref_library import (
    GENOME_DATA,
    download_and_process_genome,
    get_available_genomes,
    get_genome_status,
    load_genomes_from_csv,
)
from wgsextract_cli.core.utils import (
    calculate_bam_md5,
    resolve_reference,
    verify_paths_exist,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser("ref", help="Reference Data Management commands.")
    ref_subs = parser.add_subparsers(dest="ref_cmd", required=True)

    ident_parser = ref_subs.add_parser(
        "identify", parents=[base_parser], help=CLI_HELP["cmd_ref-identify"]
    )
    ident_parser.set_defaults(func=cmd_identify)

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

    genemap_parser = ref_subs.add_parser(
        "gene-map", parents=[base_parser], help=CLI_HELP["cmd_ref-gene-map"]
    )
    genemap_parser.add_argument(
        "--delete", action="store_true", help="Delete gene maps instead of downloading"
    )
    genemap_parser.set_defaults(func=cmd_gene_map)


def cmd_identify(args):
    verify_dependencies(["samtools"])
    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    if not verify_paths_exist({"--input": args.input}):
        return

    # Auto-resolve ref if a directory was provided
    resolved_ref = resolve_reference(args.ref, "")

    md5_sig = calculate_bam_md5(args.input, resolved_ref)
    logging.info(
        LOG_MESSAGES["ref_md5_signature"].format(input=args.input, sig=md5_sig)
    )


def cmd_download(args):
    verify_dependencies(["wget"])
    logging.info(LOG_MESSAGES["ref_downloading"].format(url=args.url, path=args.out))
    try:
        subprocess.run(["wget", "-O", args.out, args.url], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Download failed: {e}")


def cmd_index(args):
    verify_dependencies(["samtools"])
    if not args.ref:
        logging.error("--ref is required.")
        return

    if not verify_paths_exist({"--ref": args.ref}):
        return

    logging.info(LOG_MESSAGES["ref_indexing"].format(path=args.ref))
    try:
        subprocess.run(["samtools", "faidx", args.ref], check=True)
        out_dict = os.path.splitext(args.ref)[0] + ".dict"
        logging.info(LOG_MESSAGES["ref_creating_dict"].format(path=out_dict))
        subprocess.run(["samtools", "dict", args.ref, "-o", out_dict], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Indexing failed: {e}")


def cmd_count_ns(args):
    verify_dependencies(["python3"])
    if not args.ref:
        logging.error("--ref is required.")
        return

    if not verify_paths_exist({"--ref": args.ref}):
        return

    prog_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../program")
    )
    script = os.path.join(prog_dir, "countingNs.py")
    if not os.path.exists(script):
        logging.error("countingNs.py script not found.")
        return

    logging.info(LOG_MESSAGES["analyzing_ns"].format(path=args.ref))
    try:
        subprocess.run([sys.executable, script, args.ref], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"N-counting failed: {e}")


def cmd_ref_verify(args):
    verify_dependencies(["gzip", "samtools"])
    if not args.ref:
        logging.error("--ref is required.")
        return

    # Auto-resolve ref if a directory was provided
    resolved_ref = resolve_reference(args.ref, "")
    if not os.path.exists(resolved_ref):
        logging.error(f"Reference file not found: {resolved_ref}")
        return

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


def cmd_library(args):
    """Interactive library manager."""
    verify_dependencies(["curl", "samtools", "bcftools", "tabix", "bgzip", "htsfile"])

    # Try to find seed_genomes.csv
    prog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    csv_path = os.path.join(prog_root, "base_reference", "seed_genomes.csv")

    genomes = load_genomes_from_csv(csv_path)
    if not genomes:
        # Fallback to hardcoded list if CSV missing
        genomes = get_available_genomes()

    # Determine reference library directory
    reflib_dir = args.ref if args.ref else os.path.join(prog_root, "reference")
    reflib_dir = os.path.abspath(reflib_dir)

    print("\n" + "=" * 80)
    print("WGS Extract Reference Library Manager")
    print(f"Library Path: {reflib_dir}")
    print("=" * 80)
    print("Select an option:")
    print(" 0) Exit")
    print(" G) Gene Map (hg19/hg38)")

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
