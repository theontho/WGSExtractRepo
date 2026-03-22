import logging
import os
import subprocess

from wgsextract_cli.core.dependencies import log_dependency_info, verify_dependencies
from wgsextract_cli.core.messages import CLI_HELP, LOG_MESSAGES
from wgsextract_cli.core.utils import (
    get_resource_defaults,
    get_sam_index_cmd,
    get_sam_view_cmd,
    run_command,
)


def register(subparsers, base_parser):
    parser = subparsers.add_parser(
        "qc", help="Runs quality control or calculates coverage."
    )
    qc_subs = parser.add_subparsers(dest="qc_cmd", required=True)

    fastp_parser = qc_subs.add_parser(
        "fastp", parents=[base_parser], help=CLI_HELP["cmd_fastp"]
    )
    fastp_parser.add_argument("--r1", required=True, help=CLI_HELP["arg_r1"])
    fastp_parser.add_argument("--r2", help=CLI_HELP["arg_r2"])
    fastp_parser.set_defaults(func=cmd_fastp)

    fastqc_parser = qc_subs.add_parser(
        "fastqc", parents=[base_parser], help=CLI_HELP["cmd_fastqc"]
    )
    fastqc_parser.set_defaults(func=cmd_fastqc)

    vcf_parser = qc_subs.add_parser(
        "vcf", parents=[base_parser], help=CLI_HELP["cmd_vcf-qc"]
    )
    vcf_parser.add_argument(
        "--vcf-input",
        default=os.environ.get("WGSE_INPUT_VCF"),
        help=CLI_HELP["arg_vcf_input"],
    )
    vcf_parser.set_defaults(func=cmd_vcf_qc)

    fake_parser = qc_subs.add_parser(
        "fake-data", parents=[base_parser], help=CLI_HELP["cmd_fake-data"]
    )
    fake_parser.add_argument(
        "--coverage", type=float, default=1.0, help="Coverage depth (e.g. 30.0)"
    )
    fake_parser.add_argument(
        "--build",
        choices=["hg38", "hg19", "hg37", "t2t"],
        default="hg38",
        help="Human genome build naming convention.",
    )
    fake_parser.add_argument(
        "--type",
        default="cram",
        help="Comma-separated list of types to generate (vcf, cram, bam, fastq, all). Default: cram",
    )
    fake_parser.add_argument(
        "--full-size",
        action="store_true",
        help="Use real human chromosome lengths (creates large files).",
    )
    fake_parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    fake_parser.set_defaults(func=cmd_fake_data)


def cmd_fastp(args):
    verify_dependencies(["fastp"])
    log_dependency_info(["fastp"])

    from wgsextract_cli.core.utils import verify_paths_exist

    paths = {"--r1": args.r1}
    if args.r2:
        paths["--r2"] = args.r2
    if not verify_paths_exist(paths):
        return

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.r1))

    logging.debug(f"Input file (R1): {os.path.abspath(args.r1)}")
    if args.r2:
        logging.debug(f"Input file (R2): {os.path.abspath(args.r2)}")
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    base_name = os.path.basename(args.r1).split(".")[0]
    out_r1 = os.path.join(outdir, f"{base_name}_fp_1.fastq.gz")
    out_json = os.path.join(outdir, f"{base_name}_fastp.json")
    out_html = os.path.join(outdir, f"{base_name}_fastp.html")

    cmd = [
        "fastp",
        "--thread",
        threads,
        "-i",
        args.r1,
        "-o",
        out_r1,
        "-j",
        out_json,
        "-h",
        out_html,
    ]
    if args.r2:
        out_r2 = os.path.join(outdir, f"{base_name}_fp_2.fastq.gz")
        cmd.extend(["-I", args.r2, "-O", out_r2])

    logging.info(LOG_MESSAGES["running_fastp"].format(input=args.r1))
    try:
        run_command(cmd)
    except Exception as e:
        logging.error(f"fastp failed: {e}")


def cmd_fastqc(args):
    verify_dependencies(["fastqc"])
    log_dependency_info(["fastqc"])

    if not args.input:
        logging.error(LOG_MESSAGES["input_required"])
        return

    from wgsextract_cli.core.utils import verify_paths_exist

    if not verify_paths_exist({"--input": args.input}):
        return

    threads, _ = get_resource_defaults(args.threads, None)
    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(args.input))
    )

    logging.debug(f"Input file: {os.path.abspath(args.input)}")
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")

    logging.info(LOG_MESSAGES["running_fastqc"].format(input=args.input))
    try:
        run_command(["fastqc", "-t", threads, "-o", outdir, args.input])
    except Exception as e:
        logging.error(f"FastQC failed: {e}")


def cmd_vcf_qc(args):
    verify_dependencies(["bcftools"])
    log_dependency_info(["bcftools"])
    input_file = args.vcf_input if args.vcf_input else args.input
    if not input_file:
        logging.error("--input is required.")
        return

    from wgsextract_cli.core.utils import verify_paths_exist

    if not verify_paths_exist({"--input": input_file}):
        return

    logging.debug(f"Input file: {os.path.abspath(input_file)}")

    outdir = (
        args.outdir if args.outdir else os.path.dirname(os.path.abspath(input_file))
    )
    logging.debug(f"Output directory: {os.path.abspath(outdir)}")
    base_name = os.path.basename(input_file)
    out_stats = os.path.join(outdir, f"{base_name}.vcfstats.txt")

    logging.info(LOG_MESSAGES["vcf_stats"].format(input=input_file, output=out_stats))
    try:
        with open(out_stats, "w") as f:
            subprocess.run(["bcftools", "stats", input_file], stdout=f, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"VCF stats failed: {e}")
        import sys

        sys.exit(1)


def cmd_fake_data(args):
    verify_dependencies(["samtools", "bcftools", "bgzip", "tabix"])
    log_dependency_info(["samtools", "bcftools"])

    outdir = args.outdir if args.outdir else os.getcwd()
    os.makedirs(outdir, exist_ok=True)

    from wgsextract_cli.core.ref_library import get_available_genomes
    from wgsextract_cli.core.utils import resolve_reference

    # Try to find reference in library if a known build is specified
    lib_ref = None
    target_md5 = None

    # Map CLI builds to library codes
    build_map = {"hg38": "hg38", "hg19": "hg19", "hg37": "hs37d5", "t2t": "T2Tv20"}

    target_code = build_map.get(args.build)
    if target_code:
        all_genomes = get_available_genomes()
        genome_info = next(
            (
                g
                for g in all_genomes
                if g["code"] == target_code or g["final"].startswith(target_code)
            ),
            None,
        )
        if genome_info:
            target_md5 = genome_info.get("md5") if genome_info.get("md5") else None
            if target_md5:
                logging.debug(f"Found target MD5 for {args.build}: {target_md5}")
            # See if it's installed
            reflib_dir = os.environ.get("WGSE_REFLIB")
            if reflib_dir:
                candidate = os.path.join(reflib_dir, "genomes", genome_info["final"])
                if os.path.exists(candidate):
                    lib_ref = candidate

    ref_path = resolve_reference(args.ref, None) if args.ref else lib_ref

    # If the resolved path is still a directory, it means it didn't find a fasta file there.
    if ref_path and os.path.isdir(ref_path):
        ref_path = None

    # Parse types
    types = [t.strip().lower() for t in args.type.split(",")]
    if "all" in types:
        types = ["vcf", "cram", "bam", "fastq"]

    generate_fake_genomics_data(
        outdir,
        ref_path,
        coverage=args.coverage,
        seed=args.seed,
        build=args.build,
        full_size=args.full_size,
        types=types,
        target_md5=target_md5,
    )


def generate_fake_genomics_data(
    outdir,
    ref_path=None,
    coverage=1.0,
    seed=42,
    build="hg38",
    full_size=False,
    types=None,
    target_md5=None,
):
    """Generates a scaled-down or full human fake BAM, CRAM and VCF."""
    import random

    if types is None:
        types = ["cram"]

    random.seed(seed)

    mode = "Full size" if full_size else "Scaled"
    logging.info(
        f"Generating fake human-like genomics data ({build}, {mode}) in {outdir} (Coverage: {coverage}x)..."
    )
    if target_md5:
        logging.debug(f"Generator using target MD5: {target_md5}")

    is_hg19 = build in ["hg19", "hg37"]

    # Pre-generate a noise buffer to use for both FASTA and BAM
    # 1MB of noise is enough to avoid obvious patterns
    noise_size = 1024 * 1024
    noise_buffer = "".join(random.choices(["A", "C", "G", "T"], k=noise_size))

    def get_noise_seq(chrom_idx, pos, length):
        # Use a large prime offset per chromosome to ensure diversity
        offset = chrom_idx * 15485863  # A large prime
        start = (pos + offset) % noise_size
        if start + length <= noise_size:
            return noise_buffer[start : start + length]
        else:
            # Wrap around
            return noise_buffer[start:] + noise_buffer[: length - (noise_size - start)]

    # Chromosome lengths
    if full_size:
        if build == "t2t":
            chroms = {
                "chr1": 248387328,
                "chr2": 242696752,
                "chr3": 201105948,
                "chr4": 193574945,
                "chr5": 182045439,
                "chr6": 172126628,
                "chr7": 160567428,
                "chr8": 146259331,
                "chr9": 150617247,
                "chr10": 134758134,
                "chr11": 135127769,
                "chr12": 133324548,
                "chr13": 113566686,
                "chr14": 101161492,
                "chr15": 99753195,
                "chr16": 96330374,
                "chr17": 84276017,
                "chr18": 80542538,
                "chr19": 61707364,
                "chr20": 66210255,
                "chr21": 45090682,
                "chr22": 57938617,
                "chrX": 154259566,
                "chrY": 62460029,
                "chrM": 16569,
            }
        elif is_hg19:
            chroms = {
                "1": 249250621,
                "2": 243199373,
                "3": 198022430,
                "4": 191154276,
                "5": 180915260,
                "6": 171115067,
                "7": 159138663,
                "8": 146364022,
                "9": 141213431,
                "10": 135534747,
                "11": 135006516,
                "12": 133851895,
                "13": 115169878,
                "14": 107349540,
                "15": 102531392,
                "16": 90354753,
                "17": 81195210,
                "18": 78077248,
                "19": 59128983,
                "20": 63025520,
                "21": 48129895,
                "22": 51304566,
                "X": 155270560,
                "Y": 59373566,
                "MT": 16569,
            }
        else:
            chroms = {
                "chr1": 248956422,
                "chr2": 242193529,
                "chr3": 198295559,
                "chr4": 190214555,
                "chr5": 181538259,
                "chr6": 170805979,
                "chr7": 159345973,
                "chr8": 145138636,
                "chr9": 138394717,
                "chr10": 133797422,
                "chr11": 135086622,
                "chr12": 133275309,
                "chr13": 114364328,
                "chr14": 107043718,
                "chr15": 101991189,
                "chr16": 90338345,
                "chr17": 83257441,
                "chr18": 80373285,
                "chr19": 58617616,
                "chr20": 64444167,
                "chr21": 46709983,
                "chr22": 50818468,
                "chrX": 156040895,
                "chrY": 57227415,
                "chrM": 16569,
            }

        # Calculate estimated BAM size to warn user
        # 1x WGS BAM is roughly 3GB.
        est_bam_gb = 3 * coverage
        if est_bam_gb > 1:
            logging.warning(
                f"Generating {est_bam_gb:.1f}GB of fake data. This will take significant time and disk space."
            )
            # Check free space
            import shutil

            _, _, free = shutil.disk_usage(outdir)
            if free < (est_bam_gb * 1.5) * (1024**3):
                logging.error(
                    f"Insufficient disk space in {outdir}. Need at least {est_bam_gb * 1.5:.1f}GB."
                )
                return
    else:
        chroms = {}
        for i in range(1, 23):
            name = f"chr{i}" if not is_hg19 else str(i)
            chroms[name] = 10000 + (i * 100)  # variety
        chroms["chrX" if not is_hg19 else "X"] = 30000
        chroms["chrY" if not is_hg19 else "Y"] = 25000
        chroms["chrM" if not is_hg19 else "MT"] = 16569  # Real length for chrM

    # Add a dummy contig to avoid collision with known SN counts in info.py (e.g. 25)
    chroms["chrExtra" if not is_hg19 else "Extra"] = 1000

    # 1. Create a reference if none provided
    if not ref_path:
        ref_path = os.path.join(
            outdir, f"fake_ref_{build}_{mode.lower().replace(' ', '_')}.fa"
        )

    if not os.path.exists(str(ref_path)):
        logging.info(f"Creating fake reference at {ref_path}...")
        with open(ref_path, "w") as f:
            for idx, (name, length) in enumerate(chroms.items()):
                f.write(f">{name}\n")
                # Writing large files in chunks is faster
                chunk_size = 1000000
                for i in range(0, length, chunk_size):
                    this_chunk = min(chunk_size, length - i)
                    # Use chromosome-specific noise
                    f.write(get_noise_seq(idx, i, this_chunk) + "\n")
        run_command(["samtools", "faidx", ref_path])
    else:
        logging.info(f"Using reference: {ref_path}")

    # 2. Create fake BAM with reads on all chromosomes based on coverage
    # We generate reads in sorted order to avoid a massive sort operation
    sam_path = os.path.join(outdir, "fake.sam")
    bam_path = os.path.join(outdir, "fake.bam")
    base_read_len = 100
    base_insert_size = 300

    need_bam = any(t in types for t in ["bam", "cram", "fastq"])
    if need_bam:
        with open(sam_path, "w") as f:
            f.write("@HD\tVN:1.6\tSO:coordinate\n")

            # Embed MD5 in Read Group Description so it survives into BAM and is visible to samtools view -H
            rg_line = "@RG\tID:sample1\tSM:sample1\tPL:ILLUMINA"
            if target_md5:
                rg_line += f"\tDS:MD5:{target_md5}"
            f.write(rg_line + "\n")

            if target_md5:
                f.write(f"@CO\tMD5:{target_md5}\n")

            # Always write SQ lines from chroms dict for fake data
            for name, length in chroms.items():
                f.write(f"@SQ\tSN:{name}\tLN:{length}\n")

            # Generate reads chromosome by chromosome (sorted)
            for idx, (name, length) in enumerate(chroms.items()):
                num_pairs = int(
                    (length * coverage) / (base_read_len * 2)
                )  # divided by 2 for pairs
                if num_pairs < 2:
                    num_pairs = 2

                # Generate read pairs
                reads = []
                for i in range(num_pairs):
                    # Randomize read length and insert size
                    rl1 = int(random.gauss(base_read_len, 2))
                    rl2 = int(random.gauss(base_read_len, 2))
                    # Ensure lengths are reasonable
                    rl1 = max(50, min(150, rl1))
                    rl2 = max(50, min(150, rl2))

                    ins = int(random.gauss(base_insert_size, 15))
                    ins = max(rl1 + rl2 + 10, ins)  # Ensure no weird overlaps

                    pos1 = random.randint(1, length - ins - 100)
                    pos2 = pos1 + ins - rl2

                    read_id = f"read_{name}_{i}"

                    # Pull sequences from the deterministic noise buffer
                    r1_seq = get_noise_seq(idx, pos1 - 1, rl1)
                    r2_seq = get_noise_seq(idx, pos2 - 1, rl2)

                    # R1 (99 = paired, proper pair, mstrand, mate reverse)
                    reads.append(
                        (
                            pos1,
                            f"{read_id}\t99\t{name}\t{pos1}\t60\t{rl1}M\t=\t{pos2}\t{ins}\t"
                            + r1_seq
                            + "\t"
                            + "I" * rl1
                            + "\tRG:Z:sample1\n",
                        )
                    )
                    # R2 (147 = paired, proper pair, reverse, mate mstrand)
                    reads.append(
                        (
                            pos2,
                            f"{read_id}\t147\t{name}\t{pos2}\t60\t{rl2}M\t=\t{pos1}\t-{ins}\t"
                            + r2_seq
                            + "\t"
                            + "I" * rl2
                            + "\tRG:Z:sample1\n",
                        )
                    )

                # Sort all reads by position
                reads.sort()

                # Write in batches
                batch_size = 10000
                for i in range(0, len(reads), batch_size):
                    f.write("".join([r[1] for r in reads[i : i + batch_size]]))

        # Convert SAM to BAM (already sorted)
        run_command(
            get_sam_view_cmd(threads="1", fmt="BAM", is_input_sam=True)
            + [sam_path, "-o", bam_path]
        )

        run_command(get_sam_index_cmd(bam_path))
        os.remove(sam_path)
        logging.info(f"Created {bam_path} ({len(chroms)} chromosomes)")

    # 3. Create fake CRAM
    if "cram" in types:
        cram_path = os.path.join(outdir, "fake.cram")
        run_command(
            get_sam_view_cmd(threads="1", fmt="CRAM", reference=ref_path)
            + [bam_path, "-o", cram_path]
        )
        run_command(get_sam_index_cmd(cram_path))
        logging.info(f"Created {cram_path}")

    # 4. Create fake VCF with variants on all chroms
    if "vcf" in types:
        vcf_path = os.path.join(outdir, "fake.vcf")
        with open(vcf_path, "w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write('##FILTER=<ID=PASS,Description="All filters passed">\n')
            # Use our chroms list directly for consistency
            for name, length in chroms.items():
                f.write(f"##contig=<ID={name},length={length}>\n")

            f.write('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n')
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample1\n")

            # At 30x, density = 700. At 1x, density = 21000.
            if full_size:
                variant_density = max(700, int(21000 / max(1.0, coverage)))
            else:
                variant_density = 5000

            for name, length in chroms.items():
                num_variants = int(length / variant_density)
                if num_variants < 2:
                    num_variants = 2

                positions = sorted(
                    [random.randint(1, length) for _ in range(num_variants)]
                )

                batch_size = 50000
                for i in range(0, len(positions), batch_size):
                    batch = positions[i : i + batch_size]
                    lines = []
                    for pos in batch:
                        # Randomized REF/ALT using the seeded random generator
                        ref = random.choice(["A", "C", "G", "T"])
                        alt = random.choice(
                            [b for b in ["A", "C", "G", "T"] if b != ref]
                        )

                        lines.append(
                            f"{name}\t{pos}\t.\t{ref}\t{alt}\t100\tPASS\t.\tGT\t0/1\n"
                        )
                    f.write("".join(lines))

        vcf_gz = vcf_path + ".gz"
        with open(vcf_gz, "wb") as f_gz:
            subprocess.run(["bgzip", "-c", vcf_path], stdout=f_gz, check=True)
        run_command(["tabix", "-p", "vcf", vcf_gz])
        os.remove(vcf_path)
        logging.info(f"Created {vcf_gz}")

    # 5. Create fake FASTQ (R1 and R2)
    if "fastq" in types:
        r1_path = os.path.join(outdir, "fake_R1.fastq.gz")
        r2_path = os.path.join(outdir, "fake_R2.fastq.gz")

        # We can use samtools fastq to generate these from the BAM we just made
        # -1 and -2 for paired end
        run_command(
            [
                "samtools",
                "fastq",
                "-1",
                r1_path,
                "-2",
                r2_path,
                "-0",
                "/dev/null",  # Ignore any singleton reads
                "-s",
                "/dev/null",  # Ignore any shared reads
                bam_path,
            ]
        )
        logging.info(f"Created {r1_path}")
        logging.info(f"Created {r2_path}")

    # Cleanup intermediate BAM if not requested
    if need_bam and "bam" not in types:
        if os.path.exists(bam_path):
            os.remove(bam_path)
        if os.path.exists(bam_path + ".bai"):
            os.remove(bam_path + ".bai")
        logging.debug(f"Removed intermediate BAM {bam_path}")
