import os
import subprocess
import logging
import tempfile
import shlex
import shutil
from wgsextract_cli.core.dependencies import verify_dependencies
from wgsextract_cli.core.utils import get_resource_defaults, calculate_bam_md5, verify_paths_exist, ReferenceLibrary, run_command, ensure_vcf_indexed, calculate_bsd_sum
from wgsextract_cli.core.warnings import print_warning
from wgsextract_cli.core.help_texts import HELP_TEXTS

def register(subparsers, base_parser):
    parser = subparsers.add_parser("vep", parents=[base_parser], help=HELP_TEXTS["vep-run"])
    
    vep_subs = parser.add_subparsers(dest="vep_cmd", required=False)
    
    # Download helper
    dl_parser = vep_subs.add_parser("download", parents=[base_parser], help=HELP_TEXTS["vep-download"])
    dl_parser.add_argument("--species", default="homo_sapiens", help="Species name (default: homo_sapiens)")
    dl_parser.add_argument("--assembly", choices=["GRCh37", "GRCh38"], default="GRCh38", help="Assembly (default: GRCh38)")
    dl_parser.add_argument("--vep-version", default="115", help="Ensembl release version (default: 115)")
    dl_parser.add_argument("--mirror", choices=["us-east", "uk", "asia", "aws"], default="uk", help="Ensembl mirror to use (default: uk)")
    dl_parser.set_defaults(func=cmd_vep_download)

    # Verify helper
    verify_parser = vep_subs.add_parser("verify", parents=[base_parser], help=HELP_TEXTS["vep-verify"])
    verify_parser.add_argument("--species", default="homo_sapiens", help="Species name (default: homo_sapiens)")
    verify_parser.add_argument("--assembly", choices=["GRCh37", "GRCh38"], default="GRCh38", help="Assembly (default: GRCh38)")
    verify_parser.add_argument("--vep-version", default="115", help="Ensembl release version (default: 115)")
    verify_parser.set_defaults(func=cmd_vep_verify)

    # Main run arguments
    parser.add_argument("--vep-cache", help="Path to VEP cache directory (e.g., $HOME/.vep)")
    parser.add_argument("--vep-assembly", choices=["GRCh37", "GRCh38"], help="Reference assembly for VEP (GRCh37 or GRCh38)")
    parser.add_argument("--vep-args", help="Additional raw arguments to pass to VEP (e.g., '--everything --pick')")
    parser.add_argument("--format", choices=["vcf", "tab", "json"], default="vcf", help="Output format (default: vcf)")
    
    # Variant Calling (if BAM/CRAM input)
    parser.add_argument("--ploidy-file", help="File defining ploidy per chromosome (auto-resolved if possible)")
    parser.add_argument("--ploidy", help="Predefined ploidy name or value (e.g., 'human')")
    parser.add_argument("-r", "--region", help="Chromosomal region (e.g. chrM, chrY:10000-20000)")
    
    parser.set_defaults(func=cmd_vep)

def cmd_vep_download(args):
    verify_dependencies(["curl", "tar"])
    
    vep_version = args.vep_version
    species = args.species
    assembly = args.assembly
    mirror = args.mirror
    
    # Map mirrors to hosts
    mirror_hosts = {
        "us-east": "useast.ensembl.org",
        "uk": "ftp.ensembl.org",
        "asia": "asia.ensembl.org",
        "aws": "annotation-cache"
    }
    host = mirror_hosts.get(mirror, "useast.ensembl.org")
    
    cache_root = args.vep_cache if args.vep_cache else os.path.expanduser("~/.vep")
    os.makedirs(cache_root, exist_ok=True)
    
    # Construct URL for the indexed cache
    filename = f"{species}_vep_{vep_version}_{assembly}.tar.gz"
    url = f"https://{host}/pub/release-{vep_version}/variation/indexed_vep_cache/{filename}"
    
    target_path = os.path.join(cache_root, filename)
    
    # Check for rsync availability
    rsync_path = shutil.which("rsync")
    use_rsync = rsync_path is not None
    
    # Check if a partial download exists and ask how to proceed
    curl_args = ["-L", "-o", target_path]
    choice = "1" # Default to resume
    if os.path.exists(target_path):
        size_mb = os.path.getsize(target_path) / (1024*1024)
        print(f"\nFound existing partial/complete download: {filename} ({size_mb:.1f} MB)")
        print("How would you like to proceed?")
        print(" 1) Resume download (default)")
        print(" 2) Restart from scratch (delete existing)")
        print(" 3) Skip download (attempt extraction of current file)")
        
        try:
            choice = input("\nEnter choice [1-3]: ").strip()
            if choice == "2":
                logging.info("Deleting existing file and starting fresh...")
                os.remove(target_path)
            elif choice == "3":
                logging.info("Skipping download, proceeding to extraction...")
            else:
                logging.info("Resuming download...")
                curl_args.insert(0, "-C")
                curl_args.insert(1, "-")
        except (EOFError, KeyboardInterrupt):
            print("\nDownload cancelled.")
            return

    # 1. Download if needed
    if not (os.path.exists(target_path) and choice == "3"):
        download_success = False
        
        # Try AWS S3 if requested
        if mirror == "aws":
            aws_path = shutil.which("aws")
            if aws_path:
                s3_url = f"s3://annotation-cache/vep_cache/{species}/{vep_version}_{assembly}/{filename}"
                logging.info(f"Starting VEP cache download via AWS S3 (Fastest)...")
                aws_cmd = ["aws", "s3", "cp", s3_url, target_path, "--no-sign-request"]
                try:
                    subprocess.run(aws_cmd, check=True)
                    download_success = True
                except subprocess.CalledProcessError:
                    logging.warning("AWS S3 download failed. Falling back to other methods...")
            else:
                logging.warning("AWS CLI not found. Cannot use AWS mirror.")

        # Try RSYNC if available and not already succeeded
        if not download_success and use_rsync:
            # Regional mirrors often don't support rsync, so we use the master UK server
            # which we KNOW supports rsync and is reliable.
            rsync_url = f"rsync://ftp.ensembl.org/ensembl/pub/release-{vep_version}/variation/indexed_vep_cache/{filename}"
            logging.info(f"Starting VEP cache download via RSYNC (Master Server)...")
            logging.info(f"Source: {rsync_url}")
            rsync_cmd = ["rsync", "-av", "--progress", rsync_url, target_path]
            try:
                subprocess.run(rsync_cmd, check=True)
                download_success = True
            except subprocess.CalledProcessError:
                logging.warning("RSYNC failed on master server. Falling back to CURL...")
        
        # Fallback to CURL
        if not download_success:
            # Regional host for CURL (HTTP/HTTPS)
            logging.info(f"Starting VEP cache download via CURL (Mirror: {mirror})...")
            logging.info(f"URL: {url}")
            curl_cmd = ["curl"] + curl_args + [url]
            try:
                subprocess.run(curl_cmd, check=True)
                download_success = True
            except subprocess.CalledProcessError as e:
                logging.error(f"Download failed. You can re-run this command to resume.")
                logging.error(f"Error: {e}")
                return

    try:
        # Verify checksum
        checksum_url = f"https://{host}/pub/release-{vep_version}/variation/indexed_vep_cache/CHECKSUMS"
        checksum_path = target_path + ".CHECKSUMS"
        checksum_path = target_path + ".CHECKSUMS"
        logging.info("Verifying download against Ensembl CHECKSUMS...")
        
        try:
            # Download CHECKSUMS file (quietly)
            subprocess.run(["curl", "-s", "-L", "-o", checksum_path, checksum_url], check=True)
            
            # Parse CHECKSUMS for our filename
            found_sum = None
            found_blocks = None
            with open(checksum_path, "r") as f:
                for line in f:
                    # Ensembl format: 'checksum block_count file_path filename'
                    parts = line.split()
                    if len(parts) >= 4 and parts[-1] == filename:
                        found_sum = int(parts[0])
                        found_blocks = int(parts[1])
                        break
            
            if found_sum is not None:
                local_sum, local_blocks = calculate_bsd_sum(target_path)
                if local_sum == found_sum and local_blocks == found_blocks:
                    logging.info(f"Checksum verification successful: {local_sum} {local_blocks}")
                else:
                    logging.warning(f"Checksum verification FAILED!")
                    logging.warning(f"Expected: {found_sum} {found_blocks}")
                    logging.warning(f"Calculated: {local_sum} {local_blocks}")
                    logging.warning("Proceeding anyway, but the file may be corrupted.")
            else:
                logging.warning(f"Entry for {filename} not found in CHECKSUMS. Skipping verification.")
        except Exception as e:
            logging.debug(f"Checksum verification failed or skipped: {e}")
        finally:
            if os.path.exists(checksum_path):
                os.remove(checksum_path)

        logging.info(f"Download complete. Extracting {filename}...")
        # Extract to the cache root
        # The tarball usually contains a directory structure like 'homo_sapiens/115_GRCh38/...'
        subprocess.run(["tar", "-xzf", target_path, "-C", cache_root], check=True)
        
        logging.info("Extraction complete.")
        logging.info(f"VEP cache is ready at {cache_root}/{species}")
        
        # Cleanup tarball
        os.remove(target_path)
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Download or extraction failed. You can re-run this command to resume the download.")
        logging.error(f"Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

def cmd_vep_verify(args):
    vep_version = args.vep_version
    species = args.species
    assembly = args.assembly
    
    cache_root = args.vep_cache if args.vep_cache else os.path.expanduser("~/.vep")
    species_dir = os.path.join(cache_root, species)
    version_dir = os.path.join(species_dir, f"{vep_version}_{assembly}")
    
    logging.info(f"Verifying VEP cache for {species} {vep_version} {assembly}...")
    logging.info(f"Location: {version_dir}")
    
    if not os.path.exists(version_dir):
        logging.error(f"Cache directory not found: {version_dir}")
        filename = f"{species}_vep_{vep_version}_{assembly}.tar.gz"
        tarball_path = os.path.join(cache_root, filename)
        if os.path.exists(tarball_path):
            logging.info(f"Found tarball at {tarball_path}. Checking its integrity...")
            try:
                checksum_url = f"https://ftp.ensembl.org/pub/release-{vep_version}/variation/indexed_vep_cache/CHECKSUMS"
                checksum_path = tarball_path + ".CHECKSUMS"
                subprocess.run(["curl", "-s", "-L", "-o", checksum_path, checksum_url], check=True)
                
                found_sum = None
                found_blocks = None
                with open(checksum_path, "r") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 4 and parts[-1] == filename:
                            found_sum = int(parts[0])
                            found_blocks = int(parts[1])
                            break
                
                if found_sum is not None:
                    local_sum, local_blocks = calculate_bsd_sum(tarball_path)
                    if local_sum == found_sum and local_blocks == found_blocks:
                        logging.info(f"Tarball checksum OK. It is safe to extract.")
                    else:
                        logging.error(f"Tarball checksum FAILED!")
                        logging.error(f"Expected: {found_sum} {found_blocks}, Got: {local_sum} {local_blocks}")
                else:
                    logging.warning("Tarball found but no checksum entry found in Ensembl CHECKSUMS.")
            except Exception as e:
                logging.error(f"Failed to verify tarball: {e}")
            finally:
                if os.path.exists(checksum_path): os.remove(checksum_path)
        return

    # 1. Check for basic files
    info_file = os.path.join(version_dir, "info.txt")
    if os.path.exists(info_file):
        logging.info("Found info.txt")
    else:
        logging.warning("info.txt missing - cache might be incomplete.")

    # 2. Check for chromosomal directories
    missing_chrs = []
    for c in list(range(1, 23)) + ['X', 'Y', 'MT']:
        chr_dir = os.path.join(version_dir, str(c))
        if not os.path.exists(chr_dir):
            missing_chrs.append(str(c))
    
    if missing_chrs:
        logging.warning(f"Missing chromosomal data for: {', '.join(missing_chrs)}")
    else:
        logging.info("All primary chromosomal directories (1-22, X, Y, MT) present.")

    # 3. Test VEP offline detection
    vep_path = shutil.which("vep")
    if vep_path:
        try:
            logging.info(f"Testing VEP offline cache detection (using {vep_path})...")
            # We use --help as a way to trigger cache initialization without running a full analysis
            test_cmd = ["vep", "--dir_cache", cache_root, "--species", species, "--assembly", assembly, "--offline", "--help"]
            res = subprocess.run(test_cmd, capture_output=True, text=True)
            
            # VEP often outputs its main header to STDOUT and errors/warnings to STDERR
            if "ERROR: Cache directory" in res.stderr:
                logging.error("VEP failed to detect the cache directory correctly.")
                logging.error(res.stderr.strip())
            elif "ERROR" in res.stderr:
                logging.warning("VEP reported an error during initialization:")
                logging.warning(res.stderr.strip())
            else:
                logging.info("VEP successfully detected and validated the offline cache.")
        except Exception as e:
            logging.warning(f"Failed to execute VEP test command: {e}")
    else:
        logging.warning("The 'vep' command was not found in your PATH.")
        logging.warning("Verification of actual cache loading skipped. Is VEP installed and available?")

    # 4. Also verify reference if provided or auto-resolved
    if args.ref:
        logging.info("-" * 40)
        from wgsextract_cli.commands.ref import cmd_ref_verify
        cmd_ref_verify(args)

    logging.info("Verification complete.")
def cmd_vep(args):
    if getattr(args, 'vep_cmd', None) == 'download':
        return # Already handled by subcommand func

    # Determine input type
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

    # Check dependencies
    deps = ["vep", "tabix", "bcftools"]
    verify_dependencies(deps)

    # Setup resources and paths
    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    os.makedirs(outdir, exist_ok=True)
    
    md5_sig = calculate_bam_md5(args.input, None) if is_bam else None
    lib = ReferenceLibrary(args.ref, md5_sig)
    resolved_ref = lib.fasta
    
    if is_bam and not resolved_ref:
        logging.error("--ref is required (and must be a file) for variant calling from BAM/CRAM.")
        return

    # 1. Generate VCF if input is BAM/CRAM
    temp_vcf = None
    input_vcf = args.input
    
    if is_bam:
        logging.info("Input is BAM/CRAM. Performing variant calling first...")
        temp_dir = tempfile.mkdtemp(dir=outdir)
        temp_vcf = os.path.join(temp_dir, "variants.vcf.gz")
        
        region_args = ["-r", args.region] if args.region else []
        
        ploidy_args = []
        if args.ploidy_file:
            ploidy_args = ["--ploidy-file", args.ploidy_file]
        elif args.ploidy:
            ploidy_args = ["--ploidy", args.ploidy]
        elif lib.ploidy_file:
            ploidy_args = ["--ploidy-file", lib.ploidy_file]
        else:
            # Fallback to human ploidy if not specified and not auto-resolved
            ploidy_args = ["--ploidy", "human"]
            logging.info("Using default 'human' ploidy for variant calling.")

        # Run variant calling (SNPs + Indels)
        try:
            p1 = subprocess.Popen(["bcftools", "mpileup", "-B", "-I", "-C", "50", "-f", resolved_ref, "-Ou"] + region_args + [args.input], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["bcftools", "call"] + ploidy_args + ["-mv", "-P", "0", "--threads", threads, "-Oz", "-o", temp_vcf], stdin=p1.stdout, stderr=subprocess.PIPE)
            p1.stdout.close()
            _, stderr = p2.communicate()
            
            if p2.returncode != 0:
                logging.error(f"Variant calling failed: {stderr.decode() if stderr else 'Unknown error'}")
                return
            
            ensure_vcf_indexed(temp_vcf)
            input_vcf = temp_vcf
            logging.info(f"Variant calling complete. VCF generated at {temp_vcf}")
        except Exception as e:
            logging.error(f"Failed during variant calling: {e}")
            return

    # 2. Run VEP
    base_name = os.path.basename(args.input).split('.')[0]
    out_ext = ".vcf" if args.format == "vcf" else ".txt" if args.format == "tab" else ".json"
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
        # Try to map lib.build to VEP assembly
        if "38" in lib.build:
            vep_cmd.extend(["--assembly", "GRCh38"])
        elif "37" in lib.build or "19" in lib.build:
            vep_cmd.extend(["--assembly", "GRCh37"])

    # Pass the FASTA file if resolved (enables HGVS and sequence lookups)
    if resolved_ref:
        vep_cmd.extend(["--fasta", resolved_ref])
        logging.info(f"Enabling sequence lookups using FASTA: {resolved_ref}")

    if args.vep_args:
        vep_cmd.extend(shlex.split(args.vep_args))
    else:
        # Default helpful args if none provided
        vep_cmd.append("--everything")
        
        # Smart detection of offline mode
        cache_dir = args.vep_cache if args.vep_cache else os.path.expanduser("~/.vep")
        if os.path.exists(cache_dir):
            vep_cmd.extend(["--offline", "--dir_cache", cache_dir])
            logging.info(f"Using VEP cache at {cache_dir}")
        else:
            logging.warning("VEP cache not found at ~/.vep. Attempting slow online mode (--database).")
            logging.warning("Hint: Run './wgsextract vep download' to install local data for 100x faster processing.")
            vep_cmd.append("--database")

    logging.info(f"Running VEP: {' '.join(vep_cmd)}")
    try:
        run_command(vep_cmd)
        logging.info(f"VEP analysis complete. Results saved to {output_file}")
    except Exception as e:
        logging.error(f"VEP failed: {e}")
    finally:
        # Cleanup temp VCF if created
        if temp_vcf and os.path.exists(temp_vcf):
            try:
                import shutil
                shutil.rmtree(os.path.dirname(temp_vcf))
            except Exception:
                pass
