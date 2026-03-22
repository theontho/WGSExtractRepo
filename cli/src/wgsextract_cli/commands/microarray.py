import argparse
import logging
import os
import subprocess
import time

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    ReferenceLibrary,
    calculate_bam_md5,
    ensure_vcf_indexed,
    get_resource_defaults,
    verify_paths_exist,
)
from wgsextract_cli.core.warnings import print_warning


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "microarray",
        parents=[base_parser],
        help=CLI_HELP["cmd_microarray"],
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--formats", default="all", help=CLI_HELP["micro_formats_help"])
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable per-chromosome parallel variant calling",
    )
    parser.add_argument(
        "--ref-vcf-tab",
        help="Master tabulated list of all consumer microarray SNPs (auto-resolved from --ref if possible)",
    )
    parser.add_argument(
        "--ploidy-file",
        help="File defining ploidy per chromosome (auto-resolved from --ref if possible)",
    )
    parser.add_argument("-r", "--region", help=CLI_HELP["arg_region"])
    parser.set_defaults(func=run)


def split_snps_by_chrom(ref_vcf_tab, outdir):
    """Splits the master SNP list into per-chromosome files for parallel processing."""
    chrom_files = {}

    # We use tabix to list chromosomes efficiently if possible
    try:
        # Get list of chromosomes from the index
        res = subprocess.run(
            ["tabix", "-l", ref_vcf_tab], capture_output=True, text=True, check=True
        )
        chroms = res.stdout.strip().splitlines()

        for chrom in chroms:
            chrom_out = os.path.join(outdir, f"snps_{chrom}.tab")
            # tabix extraction is very fast
            with open(chrom_out, "w") as f:
                subprocess.run(["tabix", ref_vcf_tab, chrom], stdout=f, check=True)
            chrom_files[chrom] = chrom_out

    except Exception as e:
        logging.warning(
            f"Failed to split SNPs using tabix: {e}. Falling back to linear scan."
        )
        # Fallback: slow linear scan if tabix fails
        with subprocess.Popen(
            ["gzcat", ref_vcf_tab], stdout=subprocess.PIPE, text=True
        ) as proc:
            if proc.stdout:
                for line in proc.stdout:
                    if line.startswith("#"):
                        continue
                    parts = line.split("\t", 2)
                    if len(parts) < 2:
                        continue
                    chrom = parts[0]
                    if chrom not in chrom_files:
                        chrom_files[chrom] = os.path.join(outdir, f"snps_{chrom}.tab")
                    with open(chrom_files[chrom], "a") as f:
                        f.write(line)

    return chrom_files


def process_chrom(
    chrom, snp_file, chrom_tmp_dir, ref_fasta, ref_vcf_tab, ploidy_args, input_path
):
    """Worker function for parallel chromosome processing. Must be at module level for pickling."""
    chrom_vcf = os.path.join(chrom_tmp_dir, f"{chrom}.vcf.gz")
    # We combine mpileup | call | annotate into a single pipeline
    try:
        logging.debug(f"Processing chromosome {chrom}...")
        p1 = subprocess.Popen(
            [
                "bcftools",
                "mpileup",
                "-r",
                chrom,
                "-B",
                "-I",
                "-C",
                "50",
                "-f",
                ref_fasta,
                "--targets-file",
                snp_file,
                input_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        p2 = subprocess.Popen(
            ["bcftools", "call"]
            + ploidy_args
            + ["-m", "-V", "indels", "-Oz", "-o", chrom_vcf],
            stdin=p1.stdout,
            stderr=subprocess.PIPE,
        )

        if p1.stdout:
            p1.stdout.close()

        _, stderr1 = p1.communicate()
        _, stderr2 = p2.communicate()

        if p2.returncode != 0:
            logging.error(f"bcftools call failed for {chrom}: {stderr2.decode()}")
            return None

        if not os.path.exists(chrom_vcf) or os.path.getsize(chrom_vcf) < 100:
            logging.warning(f"No variants called for {chrom}, skipping.")
            return None

        ensure_vcf_indexed(chrom_vcf)

        # Annotate RSIDs immediately
        annotated_chrom_vcf = os.path.join(chrom_tmp_dir, f"{chrom}_ann.vcf.gz")
        ann_res = subprocess.run(
            [
                "bcftools",
                "annotate",
                "-a",
                ref_vcf_tab,
                "-c",
                "CHROM,POS,ID",
                "-Oz",
                "-o",
                annotated_chrom_vcf,
                chrom_vcf,
            ],
            capture_output=True,
        )

        if ann_res.returncode != 0:
            logging.error(
                f"bcftools annotate failed for {chrom}: {ann_res.stderr.decode()}"
            )
            return None

        os.remove(chrom_vcf)
        if os.path.exists(chrom_vcf + ".tbi"):
            os.remove(chrom_vcf + ".tbi")
        return annotated_chrom_vcf
    except Exception as e:
        logging.error(f"Error processing {chrom}: {e}")
        return None


def run(args):
    verify_dependencies(["bcftools", "tabix", "samtools"])
    log_dependency_info(["bcftools", "tabix", "samtools"])

    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    if not verify_paths_exist({"--input": args.input}):
        return

    logging.debug(f"Input file: {os.path.abspath(args.input)}")

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    md5_sig = calculate_bam_md5(args.input, None)
    lib = ReferenceLibrary(args.ref, md5_sig, input_path=args.input)

    ref_fasta = lib.fasta
    ref_vcf_tab = args.ref_vcf_tab if args.ref_vcf_tab else lib.ref_vcf_tab
    ploidy_file = args.ploidy_file if args.ploidy_file else lib.ploidy_file

    logging.debug(f"Resolved Reference FASTA: {ref_fasta}")
    logging.debug(f"Resolved Target SNP Tab: {ref_vcf_tab}")
    logging.debug(f"Resolved Ploidy File: {ploidy_file}")
    if lib.liftover_chain:
        logging.debug(f"Resolved Liftover Chain: {lib.liftover_chain}")

    if not ref_fasta or not os.path.isfile(ref_fasta):
        logging.error(
            LOG_MESSAGES["ref_required_for"].format(task="microarray generation")
        )
        return

    if not ref_vcf_tab:
        logging.error("--ref-vcf-tab is required and could not be auto-resolved.")
        return

    start_total = time.time()

    print_warning("ButtonMicroarray", threads=threads)

    # 1. Variant Calling or VCF Extraction
    base_name = os.path.basename(args.input).split(".")[0]
    out_vcf = os.path.join(outdir, f"{base_name}_combined.vcf.gz")
    is_vcf = args.input.endswith((".vcf", ".vcf.gz", ".bcf"))

    region_args = ["-r", args.region] if args.region else []
    ploidy_args = (
        ["--ploidy-file", ploidy_file] if ploidy_file else ["--ploidy", "human"]
    )

    start_vcf = time.time()

    if is_vcf:
        logging.info(f"VCF input detected. Extracting target SNPs from {args.input}...")
        # For VCF input, we intersect our targets with the input VCF.
        # Any missing targets are assumed to be homozygous reference.
        try:
            # Step 1: Get actual variants from the input VCF that match our targets
            hit_vcf = os.path.join(outdir, f"{base_name}_hits.vcf.gz")
            # Use long-form --targets-file to avoid version conflicts
            subprocess.run(
                ["bcftools", "view", "--targets-file", ref_vcf_tab]
                + region_args
                + ["-Oz", "-o", hit_vcf, args.input],
                check=True,
            )
            ensure_vcf_indexed(hit_vcf)

            # Step 2: Since we need a complete file for the templates, we'll
            # handle the "Reference Filling" during the extraction to CombinedKit.txt
            # to save the overhead of building a massive reference-filled VCF.
            out_vcf = hit_vcf  # We use the hits for extraction
            vcf_duration = time.time() - start_vcf
            logging.info(f"VCF extraction took {vcf_duration:.2f}s")

            # For VCF input, annotation is usually already present, but we run it
            # to ensure RSIDs match our master tab file
            annotated_vcf = os.path.join(outdir, f"{base_name}_annotated.vcf.gz")
            subprocess.run(
                [
                    "bcftools",
                    "annotate",
                    "-a",
                    ref_vcf_tab,
                    "-c",
                    "CHROM,POS,ID",
                    "-Oz",
                    "-o",
                    annotated_vcf,
                    out_vcf,
                ],
                check=True,
            )
            out_vcf = annotated_vcf
            ensure_vcf_indexed(out_vcf)

        except Exception as e:
            logging.error(f"VCF extraction failed: {e}")
            return

    elif args.parallel and not args.region:
        from concurrent.futures import ProcessPoolExecutor

        logging.info(
            f"Enabling parallel variant calling across chromosomes using {threads} threads..."
        )

        # Create a temp dir for chromosome chunks
        chrom_tmp_dir = os.path.join(outdir, "chrom_chunks")
        os.makedirs(chrom_tmp_dir, exist_ok=True)

        # Split SNPs by chrom
        chrom_snps = split_snps_by_chrom(ref_vcf_tab, chrom_tmp_dir)

        vcf_chunks = []
        with ProcessPoolExecutor(max_workers=int(threads)) as executor:
            futures = {
                executor.submit(
                    process_chrom,
                    chrom,
                    snp_file,
                    chrom_tmp_dir,
                    ref_fasta,
                    ref_vcf_tab,
                    ploidy_args,
                    args.input,
                ): chrom
                for chrom, snp_file in chrom_snps.items()
            }
            for future in futures:
                res = future.result()
                if res:
                    vcf_chunks.append(res)

        # Merge results
        if vcf_chunks:
            logging.info(f"Merging {len(vcf_chunks)} chromosome VCFs...")
            subprocess.run(
                ["bcftools", "concat", "-Oz", "-o", out_vcf] + sorted(vcf_chunks),
                check=True,
            )
            ensure_vcf_indexed(out_vcf)

            # Use the merged VCF as the "annotated" source
            annotated_vcf = out_vcf

            # Cleanup chunks
            import shutil

            shutil.rmtree(chrom_tmp_dir)
        else:
            logging.error("No VCF chunks were generated.")
            return

        vcf_duration = time.time() - start_vcf
        logging.info(f"Parallel VCF generation and annotation took {vcf_duration:.2f}s")

    else:
        # ORIGINAL SEQUENTIAL LOGIC
        try:
            # mpileup restricted to target SNPs
            mpileup_cmd = (
                ["bcftools", "mpileup"]
                + region_args
                + [
                    "-B",
                    "-I",
                    "-C",
                    "50",
                    "-f",
                    ref_fasta,
                    "--targets-file",
                    ref_vcf_tab,
                    args.input,
                ]
            )

            p1 = subprocess.Popen(
                mpileup_cmd,
                stdout=subprocess.PIPE,
            )
            p2 = subprocess.Popen(
                ["bcftools", "call"]
                + ploidy_args
                + ["-m", "-V", "indels", "-Oz", "-o", out_vcf],
                stdin=p1.stdout,
            )
            if p1.stdout:
                p1.stdout.close()
            p2.communicate()

            ensure_vcf_indexed(out_vcf)
            vcf_duration = time.time() - start_vcf
            logging.info(f"VCF generation took {vcf_duration:.2f}s")

            # 1.5 Annotate the VCF with RSIDs from the reference tab file
            annotated_vcf = os.path.join(outdir, f"{base_name}_annotated.vcf.gz")
            logging.info(f"Annotating VCF with RSIDs from {ref_vcf_tab}...")
            start_ann = time.time()
            try:
                # -a: annotation file, -c: columns to use (CHROM, POS, ID)
                subprocess.run(
                    [
                        "bcftools",
                        "annotate",
                        "-a",
                        ref_vcf_tab,
                        "-c",
                        "CHROM,POS,ID",
                        "-Oz",
                        "-o",
                        annotated_vcf,
                        out_vcf,
                    ],
                    check=True,
                )
                # Use the annotated VCF for subsequent steps
                out_vcf = annotated_vcf
                ensure_vcf_indexed(out_vcf)
                ann_duration = time.time() - start_ann
                logging.info(f"Annotation took {ann_duration:.2f}s")
            except Exception as e:
                logging.warning(f"VCF annotation failed, IDs may be missing: {e}")

        except Exception as e:
            logging.error(f"Variant calling failed: {e}")
            return

    # 2. Extract results to a temporary CombinedKit.txt
    combined_kit_txt = os.path.join(outdir, f"{base_name}_CombinedKit.txt")
    logging.info(f"Extracting genotypes to {combined_kit_txt}...")
    start_ext = time.time()

    try:
        if is_vcf:
            # VCF MODE: We need to fill in reference alleles for missing positions
            # We iterate through the target list and check our 'hits' VCF

            # Load hits into a lookup dict (CHROM, POS) -> Genotype
            variant_calls = {}
            cmd = ["bcftools", "query", "-f", "%CHROM\t%POS\t[%TGT]\n", out_vcf]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
            if proc.stdout:
                for line in proc.stdout:
                    parts = line.strip().split("\t")
                    if len(parts) >= 3:
                        variant_calls[(parts[0], parts[1])] = parts[2]
            proc.wait()

            logging.info(
                f"Found {len(variant_calls)} variants in input VCF matching targets."
            )

            # OPTIMIZATION: Pre-fetch ALL reference alleles for targets in one pass
            logging.info("Pre-fetching reference alleles for target SNPs...")
            ref_alleles = {}
            region_file = os.path.join(outdir, "targets.regions")

            # 1. Detect FASTA chromosome naming to ensure faidx hits
            # Use .fai file if it exists, as it is more portable than samtools faidx -l
            fasta_chroms = set()
            fai_path = ref_fasta + ".fai"
            if os.path.exists(fai_path):
                try:
                    with open(fai_path) as f_fai:
                        fasta_chroms = {line.split("\t")[0] for line in f_fai}
                except Exception as e:
                    logging.warning(f"Failed to read .fai file: {e}")

            if not fasta_chroms:
                res_l = subprocess.run(
                    ["samtools", "faidx", "-l", ref_fasta],
                    capture_output=True,
                    text=True,
                )
                if res_l.returncode == 0:
                    fasta_chroms = set(res_l.stdout.splitlines())

            try:
                # 2. Generate region file (chr:pos-pos) with normalization
                # Map FASTA-normalized name back to original SNP-tab name for reverse lookup
                norm_to_orig = {}

                with open(region_file, "w") as f_reg:
                    # Use a stream that handles both compressed and uncompressed
                    cat_cmd = ["gzcat"] if ref_vcf_tab.endswith(".gz") else ["cat"]
                    with subprocess.Popen(
                        cat_cmd + [ref_vcf_tab], stdout=subprocess.PIPE, text=True
                    ) as proc_tab:
                        if proc_tab.stdout:
                            for line in proc_tab.stdout:
                                if line.startswith("#"):
                                    continue
                                parts = line.strip().split("\t")
                                if len(parts) < 2:
                                    continue
                                c, p = parts[0], parts[1]
                                # Normalize for FASTA
                                fc = c
                                if fc not in fasta_chroms:
                                    if fc.startswith("chr") and fc[3:] in fasta_chroms:
                                        fc = fc[3:]
                                    elif (
                                        not fc.startswith("chr")
                                        and f"chr{fc}" in fasta_chroms
                                    ):
                                        fc = f"chr{fc}"

                                if fc in fasta_chroms:
                                    f_reg.write(f"{fc}:{p}-{p}\n")
                                    norm_to_orig[f"{fc}:{p}-{p}"] = (c, p)

                # 3. Run samtools faidx --region-file
                faidx_cmd = [
                    "samtools",
                    "faidx",
                    "--region-file",
                    region_file,
                    ref_fasta,
                ]
                proc_ref = subprocess.Popen(
                    faidx_cmd, stdout=subprocess.PIPE, text=True
                )

                curr_region = None
                if proc_ref.stdout:
                    for line in proc_ref.stdout:
                        if line.startswith(">"):
                            curr_region = line.strip()[1:]
                        else:
                            if curr_region:
                                base = line.strip().upper()
                                # Map back to ORIGINAL chromosome name from the region string
                                if curr_region in norm_to_orig:
                                    orig_c, orig_p = norm_to_orig[curr_region]
                                    ref_alleles[(orig_c, orig_p)] = base
                                elif ":" in curr_region:
                                    # Fallback parsing
                                    c_norm, p_range = curr_region.split(":", 1)
                                    p = p_range.split("-")[0]
                                    ref_alleles[(c_norm, p)] = base
                                    # Also store variations to be safe
                                    if not c_norm.startswith("chr"):
                                        ref_alleles[(f"chr{c_norm}", p)] = base
                                    elif c_norm.startswith("chr"):
                                        ref_alleles[(c_norm[3:], p)] = base
                proc_ref.wait()
                logging.info(f"Pre-fetched {len(ref_alleles)} reference alleles.")
                if os.path.exists(region_file):
                    os.remove(region_file)
            except Exception as e:
                logging.warning(
                    f"Fast reference pre-fetch failed: {e}. Falling back to SNP-tab column or 'N'."
                )
                if os.path.exists(region_file):
                    os.remove(region_file)

            with open(combined_kit_txt, "w") as f_out:
                f_out.write("# RSID\tCHROM\tPOS\tRESULT\n")

                if args.region:
                    stream_cmd = ["tabix", ref_vcf_tab, args.region]
                else:
                    cat_cmd = ["gzcat"] if ref_vcf_tab.endswith(".gz") else ["cat"]
                    stream_cmd = cat_cmd + [ref_vcf_tab]

                with subprocess.Popen(
                    stream_cmd, stdout=subprocess.PIPE, text=True
                ) as proc:
                    if proc.stdout:
                        ref_col_idx = -1
                        for line in proc.stdout:
                            if line.startswith("#"):
                                header = line.strip().split("\t")
                                if "REF" in header:
                                    ref_col_idx = header.index("REF")
                                continue
                            parts = line.strip().split("\t")
                            if len(parts) < 3:
                                continue
                            chrom, pos, rsid = parts[0], parts[1], parts[2]

                            if (chrom, pos) in variant_calls:
                                tgt = variant_calls[(chrom, pos)]
                                genotype = (
                                    tgt.replace("/", "")
                                    .replace("|", "")
                                    .replace(".", "-")
                                )
                            else:
                                # MISSING in VCF -> Assume Homozygous Reference
                                ref_base = None

                                # 1. Try REF column from TAB file first (FASTEST)
                                if ref_col_idx != -1 and len(parts) > ref_col_idx:
                                    ref_base = parts[ref_col_idx].upper()

                                # 2. Try pre-fetched alleles
                                if not ref_base:
                                    ref_base = ref_alleles.get((chrom, pos))

                                # 3. Fallback to N (NO slow subprocess calls here)
                                if not ref_base:
                                    ref_base = "N"

                                genotype = f"{ref_base}{ref_base}"

                            chrom_norm = chrom.replace("chr", "").replace("M", "MT")
                            f_out.write(f"{rsid}\t{chrom_norm}\t{pos}\t{genotype}\n")

        else:
            # CRAM/BAM MODE: Standard extraction
            with open(combined_kit_txt, "w") as f_out:
                # Add a header for GEDMatch compatibility
                f_out.write("# RSID\tCHROM\tPOS\tRESULT\n")

                # Run bcftools query
                cmd = [
                    "bcftools",
                    "query",
                    "-f",
                    "%ID\t%CHROM\t%POS\t[%TGT]\n",
                    out_vcf,
                ]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
                if proc.stdout:
                    for line in proc.stdout:
                        parts = line.strip().split("\t")
                        if len(parts) < 4:
                            continue

                        snp_id, chrom, pos, tgt = parts[0], parts[1], parts[2], parts[3]

                        if snp_id == ".":
                            snp_id = f"pos_{chrom}_{pos}"

                        genotype = (
                            tgt.replace("/", "").replace("|", "").replace(".", "-")
                        )
                        if not genotype:
                            genotype = "--"

                        chrom_norm = chrom.replace("chr", "").replace("M", "MT")
                        f_out.write(f"{snp_id}\t{chrom_norm}\t{pos}\t{genotype}\n")
                proc.wait()

        ext_duration = time.time() - start_ext
        logging.info(f"Extraction took {ext_duration:.2f}s")
    except Exception as e:
        logging.error(f"Failed to generate CombinedKit.txt: {e}")
        return
    finally:
        # Cleanup intermediate files
        for f in ["hit_vcf", "annotated_vcf"]:
            if f in locals():
                path = locals()[f]
                if path and os.path.exists(path):
                    os.remove(path)
                    for ext in [".tbi", ".csi"]:
                        if os.path.exists(path + ext):
                            os.remove(path + ext)

    from wgsextract_cli.core.microarray_utils import (
        convert_to_vendor_format,
        liftover_hg38_to_hg19,
    )

    # 3. Liftover if needed (to hg19 for most vendors)
    final_txt = combined_kit_txt
    if lib.build and "38" in lib.build:
        hg19_txt = combined_kit_txt.replace(".txt", "_hg19.txt")
        if lib.liftover_chain:
            logging.info(LOG_MESSAGES["micro_liftover_warn"])
            start_lift = time.time()
            try:
                liftover_hg38_to_hg19(
                    combined_kit_txt,
                    hg19_txt,
                    lib.liftover_chain,
                    templates_dir=lib.root,
                )
                final_txt = hg19_txt
                lift_duration = time.time() - start_lift
                logging.info(f"Liftover took {lift_duration:.2f}s")
            except Exception as e:
                logging.error(f"Liftover failed: {e}")
                # Fallback to hg38? Most vendors expect hg19.
        else:
            logging.warning("Liftover requested but chain file not found.")

    # 4. Convert to vendor formats
    requested_formats = args.formats.split(",")
    start_fmt = time.time()
    for fmt_key in requested_formats:
        fmt_key = fmt_key.strip()
        if fmt_key == "all":
            continue

        logging.info(LOG_MESSAGES["micro_generating_fmt"].format(format=fmt_key))

        # We need to map fmt_key to actual template names if they differ
        # e.g. 23andme_v5 -> 23andMe_V5
        template_map = {
            "23andme_v3": "23andMe_V3",
            "23andme_v4": "23andMe_V4",
            "23andme_v5": "23andMe_V5",
            "23andme_api": "23andMe_SNPs_API",
            "ancestry_v1": "Ancestry_V1",
            "ancestry_v2": "Ancestry_V2",
            "ftdna_v2": "FTDNA_V2",
            "ftdna_v3": "FTDNA_V3",
            "ldna_v1": "LDNA_V1",
            "ldna_v2": "LDNA_V2",
            "myheritage_v1": "MyHeritage_V1",
            "myheritage_v2": "MyHeritage_V2",
        }

        real_fmt = template_map.get(fmt_key.lower(), fmt_key)

        output_file = os.path.join(outdir, f"{base_name}_{real_fmt}.txt")
        if "MyHeritage" in real_fmt or "FTDNA" in real_fmt:
            output_file = output_file.replace(".txt", ".csv")

        try:
            convert_to_vendor_format(real_fmt, final_txt, output_file, lib.root)
            logging.info(f"Generated {output_file}")
        except Exception as e:
            logging.error(f"Failed to generate {real_fmt}: {e}")

    fmt_duration = time.time() - start_fmt
    logging.info(f"Format conversion (all) took {fmt_duration:.2f}s")

    total_duration = time.time() - start_total
    logging.info(f"Total microarray process took {total_duration:.2f}s")
