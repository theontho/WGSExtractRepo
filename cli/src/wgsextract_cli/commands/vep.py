import logging
import os
import shlex
import shutil
import subprocess
import tempfile

from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.ref_library import download_file
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    calculate_bsd_sum,
    ensure_vcf_indexed,
    get_resource_defaults,
    run_command,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "vep", parents=[base_parser], help=CLI_HELP["cmd_vep-run"]
    )

    vep_subs = parser.add_subparsers(dest="vep_cmd", required=False)

    # Download helper
    dl_parser = vep_subs.add_parser(
        "download", parents=[base_parser], help=CLI_HELP["cmd_vep-download"]
    )
    dl_parser.add_argument(
        "--species", default="homo_sapiens", help="Species name (default: homo_sapiens)"
    )
    dl_parser.add_argument(
        "--assembly",
        choices=["GRCh37", "GRCh38"],
        default="GRCh38",
        help="Assembly (default: GRCh38)",
    )
    dl_parser.add_argument(
        "--vep-version", default="115", help="Ensembl release version (default: 115)"
    )
    dl_parser.add_argument(
        "--mirror",
        choices=["us-east", "uk", "asia", "aws"],
        default="uk",
        help="Ensembl mirror to use (default: uk)",
    )
    dl_parser.set_defaults(func=cmd_vep_download)

    # Verify helper
    verify_parser = vep_subs.add_parser(
        "verify", parents=[base_parser], help=CLI_HELP["cmd_vep-verify"]
    )
    verify_parser.add_argument(
        "--species", default="homo_sapiens", help="Species name (default: homo_sapiens)"
    )
    verify_parser.add_argument(
        "--assembly",
        choices=["GRCh37", "GRCh38"],
        default="GRCh38",
        help="Assembly (default: GRCh38)",
    )
    verify_parser.add_argument(
        "--vep-version", default="115", help="Ensembl release version (default: 115)"
    )
    verify_parser.set_defaults(func=cmd_vep_verify)

    # Main run arguments
    parser.add_argument(
        "--vep-cache", help="Path to VEP cache directory (e.g., $HOME/.vep)"
    )
    parser.add_argument(
        "--vep-assembly",
        choices=["GRCh37", "GRCh38"],
        help="Reference assembly for VEP (GRCh37 or GRCh38)",
    )
    parser.add_argument(
        "--vep-args",
        help="Additional raw arguments to pass to VEP (e.g., '--everything --pick')",
    )
    parser.add_argument(
        "--format",
        choices=["vcf", "tab", "json"],
        default="vcf",
        help="Output format (default: vcf)",
    )

    # Variant Calling (if BAM/CRAM input)
    parser.add_argument(
        "--ploidy-file",
        help="File defining ploidy per chromosome (auto-resolved if possible)",
    )
    parser.add_argument(
        "--ploidy", help="Predefined ploidy name or value (e.g., 'human')"
    )
    parser.add_argument(
        "-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)"
    )

    parser.set_defaults(func=cmd_vep)


def cmd_vep_download(args):
    verify_dependencies(["curl", "tar"])

    vep_version = args.vep_version
    species = args.species
    assembly = args.assembly
    mirror = args.mirror

    mirror_hosts = {
        "us-east": "useast.ensembl.org",
        "uk": "ftp.ensembl.org",
        "asia": "asia.ensembl.org",
        "aws": "annotation-cache",
    }
    host = mirror_hosts.get(mirror, "useast.ensembl.org")

    cache_root = args.vep_cache
    if not cache_root:
        lib = ReferenceLibrary(args.ref)
        if lib.root and os.path.isdir(lib.root):
            cache_root = os.path.join(lib.root, "vep")
        else:
            cache_root = os.path.expanduser("~/.vep")

    os.makedirs(cache_root, exist_ok=True)

    filename = f"{species}_vep_{vep_version}_{assembly}.tar.gz"
    url = f"https://{host}/pub/release-{vep_version}/variation/indexed_vep_cache/{filename}"
    target_path = os.path.join(cache_root, filename)

    progress_callback = getattr(args, "progress_callback", None)
    cancel_event = getattr(args, "cancel_event", None)

    logging.info(LOG_MESSAGES["vep_downloading"].format(host=host))
    success = download_file(url, target_path, progress_callback, cancel_event)
    if not success:
        if cancel_event and cancel_event.is_set():
            logging.info("Download cancelled.")
        else:
            logging.error("Download failed.")
        return False

    try:
        checksum_url = f"https://{host}/pub/release-{vep_version}/variation/indexed_vep_cache/CHECKSUMS"
        checksum_path = target_path + ".CHECKSUMS"
        logging.info(LOG_MESSAGES["vep_verifying_checksums"])

        try:
            subprocess.run(
                ["curl", "-s", "-L", "-o", checksum_path, checksum_url], check=True
            )
            found_sum = None
            found_blocks = None
            with open(checksum_path) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[-1] == filename:
                        found_sum = int(parts[0])
                        found_blocks = int(parts[1])
                        break

            if found_sum is not None:
                local_sum, local_blocks = calculate_bsd_sum(target_path)
                if local_sum == found_sum and local_blocks == found_blocks:
                    logging.info(
                        LOG_MESSAGES["vep_checksum_ok"].format(
                            sum=local_sum, blocks=local_blocks
                        )
                    )
                else:
                    logging.warning(
                        LOG_MESSAGES["vep_checksum_failed"].format(
                            expected_sum=found_sum,
                            expected_blocks=found_blocks,
                            actual_sum=local_sum,
                            actual_blocks=local_blocks,
                        )
                    )
        except Exception as e:
            logging.debug(f"Checksum verification failed: {e}")
        finally:
            if os.path.exists(checksum_path):
                os.remove(checksum_path)

        if cancel_event and cancel_event.is_set():
            logging.info("Download cancelled before extraction.")
            return False

        logging.info(LOG_MESSAGES["vep_extracting"].format(filename=filename))
        subprocess.run(["tar", "-xzf", target_path, "-C", cache_root], check=True)
        logging.info(LOG_MESSAGES["vep_extraction_complete"])
        logging.info(LOG_MESSAGES["vep_ready"].format(path=f"{cache_root}/{species}"))
        os.remove(target_path)
        return True
    except Exception as e:
        logging.error(f"Post-download processing failed: {e}")
        return False


def cmd_vep_verify(args):
    vep_version = args.vep_version
    species = args.species
    assembly = args.assembly

    cache_root = args.vep_cache
    if not cache_root:
        lib = ReferenceLibrary(args.ref)
        if lib.root and os.path.isdir(lib.root):
            cache_root = os.path.join(lib.root, "vep")
        else:
            cache_root = os.path.expanduser("~/.vep")

    species_dir = os.path.join(cache_root, species)
    version_dir = os.path.join(species_dir, f"{vep_version}_{assembly}")

    logging.info(
        LOG_MESSAGES["vep_verifying"].format(
            species=species, version=vep_version, assembly=assembly
        )
    )
    logging.info(LOG_MESSAGES["vep_location"].format(path=version_dir))

    if not os.path.exists(version_dir):
        logging.error(LOG_MESSAGES["vep_cache_missing"].format(path=version_dir))
        return False

    # Check for basic files
    info_file = os.path.join(version_dir, "info.txt")
    if os.path.exists(info_file):
        logging.info(LOG_MESSAGES["vep_info_found"])
    else:
        logging.warning(LOG_MESSAGES["vep_info_missing"])

    # Check for chromosomal directories
    missing_chrs = []
    for c in list(range(1, 23)) + ["X", "Y", "MT"]:
        chr_dir = os.path.join(version_dir, str(c))
        if not os.path.exists(chr_dir):
            missing_chrs.append(str(c))

    if missing_chrs:
        logging.warning(
            LOG_MESSAGES["vep_chrs_missing"].format(chrs=", ".join(missing_chrs))
        )
    else:
        logging.info(LOG_MESSAGES["vep_chrs_ok"])

    logging.info(LOG_MESSAGES["vep_verification_complete"])
    return True


def cmd_vep(args):
    if getattr(args, "vep_cmd", None) == "download":
        return
    if not args.input:
        logging.error("--input is required.")
        return

    is_vcf = args.input.lower().endswith((".vcf", ".vcf.gz", ".bcf"))
    is_bam = args.input.lower().endswith((".bam", ".cram"))
    if not is_vcf and not is_bam:
        logging.error("Input must be a VCF, BAM, or CRAM file.")
        return

    if is_vcf:
        ensure_vcf_indexed(args.input)
    verify_dependencies(["vep", "tabix", "bcftools"])

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    os.makedirs(outdir, exist_ok=True)

    md5_sig = calculate_bam_md5(args.input, None) if is_bam else None
    lib = ReferenceLibrary(args.ref, md5_sig)
    resolved_ref = lib.fasta

    if is_bam and not resolved_ref:
        logging.error("--ref is required for variant calling from BAM/CRAM.")
        return

    input_vcf = args.input
    temp_vcf = None
    if is_bam:
        logging.info(LOG_MESSAGES["vep_calling_pre"])
        temp_dir = tempfile.mkdtemp(dir=outdir)
        temp_vcf = os.path.join(temp_dir, "variants.vcf.gz")
        region_args = ["-r", args.region] if args.region else []
        ploidy_args = (
            ["--ploidy-file", args.ploidy_file]
            if args.ploidy_file
            else ["--ploidy", args.ploidy]
            if args.ploidy
            else ["--ploidy-file", lib.ploidy_file]
            if lib.ploidy_file
            else ["--ploidy", "human"]
        )

        try:
            assert resolved_ref is not None
            p1 = subprocess.Popen(
                [
                    "bcftools",
                    "mpileup",
                    "-B",
                    "-I",
                    "-C",
                    "50",
                    "-f",
                    resolved_ref,
                    "-Ou",
                ]
                + region_args
                + [args.input],
                stdout=subprocess.PIPE,
            )
            p2 = subprocess.Popen(
                ["bcftools", "call"]
                + ploidy_args
                + ["-mv", "-P", "0", "--threads", threads, "-Oz", "-o", temp_vcf],
                stdin=p1.stdout,
                stderr=subprocess.PIPE,
            )
            if p1.stdout:
                p1.stdout.close()
            _, stderr = p2.communicate()
            if p2.returncode != 0:
                logging.error(f"Variant calling failed: {stderr.decode()}")
                return
            ensure_vcf_indexed(temp_vcf)
            input_vcf = temp_vcf
        except Exception as e:
            logging.error(f"Failed during variant calling: {e}")
            return

    base_name = os.path.basename(args.input).split(".")[0]
    out_ext = (
        ".vcf" if args.format == "vcf" else ".txt" if args.format == "tab" else ".json"
    )
    output_file = os.path.join(outdir, f"{base_name}_vep{out_ext}")
    vep_cmd = ["vep", "-i", input_vcf, "-o", output_file, "--fork", threads]
    if args.format == "vcf":
        vep_cmd.append("--vcf")
    elif args.format == "json":
        vep_cmd.append("--json")
    else:
        vep_cmd.append("--tab")

    if args.vep_assembly:
        vep_cmd.extend(["--assembly", args.vep_assembly])
    elif lib.build:
        if "38" in lib.build:
            vep_cmd.extend(["--assembly", "GRCh38"])
        elif "37" in lib.build or "19" in lib.build:
            vep_cmd.extend(["--assembly", "GRCh37"])

    if resolved_ref:
        vep_cmd.extend(["--fasta", resolved_ref])

    if args.vep_args:
        vep_cmd.extend(shlex.split(args.vep_args))
    else:
        vep_cmd.append("--everything")
        cache_dir = args.vep_cache or lib.vep_cache or os.path.expanduser("~/.vep")
        if os.path.exists(cache_dir):
            vep_cmd.extend(["--offline", "--dir_cache", cache_dir])
            logging.info(LOG_MESSAGES["vep_using_cache"].format(path=cache_dir))
        else:
            logging.warning(LOG_MESSAGES["vep_no_cache_warn"].format(path=cache_dir))
            vep_cmd.append("--database")

    logging.info(LOG_MESSAGES["vep_running"].format(command=" ".join(vep_cmd)))
    try:
        run_command(vep_cmd)
        logging.info(LOG_MESSAGES["vep_complete"].format(path=output_file))
    except Exception as e:
        logging.error(f"VEP failed: {e}")
    finally:
        if temp_vcf:
            shutil.rmtree(os.path.dirname(temp_vcf), ignore_errors=True)
