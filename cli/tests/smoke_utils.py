import os
import shutil
import subprocess
from typing import Optional

_TOOL_CACHE = {}


def check_tool(tool_name: str) -> bool:
    """Checks if a tool is available in the system PATH and caches the result."""
    if tool_name in _TOOL_CACHE:
        return _TOOL_CACHE[tool_name]

    # Try finding it in path
    path = shutil.which(tool_name)
    if path:
        _TOOL_CACHE[tool_name] = True
        return True

    # Check common locations or via 'uv run' if needed
    # (Simplified for now)
    _TOOL_CACHE[tool_name] = False
    return False


def verify_bam(file_path: str) -> bool:
    """Verifies that a BAM file exists and is valid using samtools quickcheck."""
    if not os.path.exists(file_path):
        print(f"File missing: {file_path}")
        return False
    if not check_tool("samtools"):
        return os.path.getsize(file_path) > 0

    result = subprocess.run(["samtools", "quickcheck", file_path])
    return result.returncode == 0


def verify_vcf(file_path: str, allow_empty: bool = False) -> bool:
    """Verifies that a VCF file exists and is valid using bcftools view -h."""
    if not os.path.exists(file_path):
        print(f"File missing: {file_path}")
        return False

    if not check_tool("bcftools"):
        return os.path.getsize(file_path) > 0

    result = subprocess.run(["bcftools", "view", "-h", file_path], capture_output=True)
    if result.returncode != 0:
        print(f"VCF header check failed: {file_path}")
        return False

    if not allow_empty:
        # Check if it has any variant lines (not starting with #)
        try:
            if file_path.endswith(".gz"):
                import gzip

                with gzip.open(file_path, "rt") as f:
                    for line in f:
                        if not line.startswith("#"):
                            return True
            else:
                with open(file_path) as f:
                    for line in f:
                        if not line.startswith("#"):
                            return True
            print(f"VCF has no variant lines: {file_path}")
            return False
        except Exception:
            return False
    return True


def verify_fastq(file_path: str) -> bool:
    """Basic check if a file is a valid FASTQ."""
    if not os.path.exists(file_path):
        return False
    try:
        if file_path.endswith(".gz"):
            import gzip

            with gzip.open(file_path, "rt") as f:
                lines = [next(f) for _ in range(4)]
        else:
            with open(file_path) as f:
                lines = [next(f) for _ in range(4)]
        return len(lines) == 4
    except (StopIteration, OSError):
        print(f"FASTQ is empty or malformed: {file_path}")
        return False


def assert_file_contains(file_path: str, pattern: str) -> bool:
    """Checks if a file contains a specific string pattern."""
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, errors="ignore") as f:
            content = f.read()
            return pattern in content
    except Exception:
        return False


def get_cli_command() -> list[str]:
    """Returns the base command for running the CLI as a subprocess."""
    # Using 'uv run python3 -m wgsextract_cli.main' ensures we use the project's env
    return ["uv", "run", "python3", "-m", "wgsextract_cli.main"]


def run_cli(args: list[str], env: dict | None = None) -> tuple[int, str, str]:
    """Runs the CLI as a subprocess and returns (returncode, stdout, stderr)."""
    # Clean environment to prevent interference from .env files during tests
    # Also skip loading .env files from the project root
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("WGSE_")}
    clean_env["WGSE_SKIP_DOTENV"] = "1"
    if env:
        clean_env.update(env)

    cmd = get_cli_command() + args
    result = subprocess.run(cmd, capture_output=True, text=True, env=clean_env)
    return result.returncode, result.stdout, result.stderr


def run_cli_pipe(
    args: list[str], stdin_str: str, env: dict | None = None
) -> tuple[int, str, str]:
    """Runs the CLI as a subprocess with stdin and returns (returncode, stdout, stderr)."""
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("WGSE_")}
    clean_env["WGSE_SKIP_DOTENV"] = "1"
    if env:
        clean_env.update(env)

    cmd = get_cli_command() + args
    result = subprocess.run(
        cmd, input=stdin_str, capture_output=True, text=True, env=clean_env
    )
    return result.returncode, result.stdout, result.stderr


def assert_log_contains(stderr: str, pattern: str):
    """Asserts that the CLI log (stderr) contains a specific message."""
    assert pattern in stderr


def ensure_fake_data(fake_dir: str):
    """Ensures that fake test data is generated in the specified directory."""
    if os.path.exists(os.path.join(fake_dir, "fake.bam")):
        return

    os.makedirs(fake_dir, exist_ok=True)
    # Use the CLI to generate fake data
    run_cli(
        [
            "qc",
            "fake-data",
            "--outdir",
            fake_dir,
            "--build",
            "hg38",
            "--seed",
            "42",
            "--coverage",
            "0.1",
        ]
    )


def setup_test_reference(tmp_path: str, ref_src: str):
    """Sets up a reference genome in a temporary directory for testing."""
    ref_dir = os.path.join(tmp_path, "reference")
    os.makedirs(os.path.join(ref_dir, "genomes"), exist_ok=True)

    ref_name = os.path.basename(ref_src)
    ref_dst = os.path.join(ref_dir, "genomes", ref_name)
    shutil.copy(ref_src, ref_dst)

    # Copy indices if they exist
    for ext in [".fai", ".gzi"]:
        if os.path.exists(ref_src + ext):
            shutil.copy(ref_src + ext, ref_dst + ext)

    return ref_dst, ref_dir


def copy_resource_files(src_dir: str, dst_dir: str, build: str):
    """Copies resource files (ClinVar, REVEL, etc.) for a specific build."""
    if not os.path.exists(src_dir):
        return

    os.makedirs(os.path.join(dst_dir, "ref"), exist_ok=True)

    # Common resource patterns
    patterns = [
        f"clinvar_{build}.vcf.gz",
        f"revel_{build}.tsv.gz",
        f"gnomad_{build}.vcf.gz",
        f"phylop_{build}.tsv.gz",
    ]

    import glob

    for pattern in patterns:
        for file in glob.glob(os.path.join(src_dir, pattern + "*")):
            shutil.copy(file, os.path.join(dst_dir, "ref", os.path.basename(file)))


def prepare_vcf_for_test(vcf_src: str, outdir: str, ref: str):
    """Prepares a VCF for testing by copying and indexing it."""
    vcf_name = os.path.basename(vcf_src)
    vcf_dst = os.path.join(outdir, vcf_name)
    shutil.copy(vcf_src, vcf_dst)

    # Index if it's a gzipped VCF and doesn't have an index
    if vcf_dst.endswith(".gz") and not os.path.exists(vcf_dst + ".tbi"):
        tbi_src = vcf_src + ".tbi"
        if os.path.exists(tbi_src):
            if os.path.abspath(tbi_src) != os.path.abspath(vcf_dst + ".tbi"):
                shutil.copy(tbi_src, vcf_dst + ".tbi")
        else:
            # Try to index it
            run_cli(["ref", "index", "--ref", vcf_dst])

    # Copy .tbi if it exists next to source
    if os.path.exists(vcf_src + ".tbi"):
        tbi_src = vcf_src + ".tbi"
        tbi_dst = vcf_dst + ".tbi"
        if os.path.exists(tbi_src):
            if os.path.abspath(tbi_src) != os.path.abspath(tbi_dst):
                shutil.copy(tbi_src, tbi_dst)

    # Index ref if needed
    if os.path.exists(ref) and not os.path.exists(ref + ".fai"):
        run_cli(["ref", "index", "--ref", ref])
