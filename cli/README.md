# WGS Extract CLI (`wgsextract-cli`)

A completely independent, modern command-line interface for the WGS Extract application. This tool allows users to perform bioinformatics workflows (BAM/CRAM management, extraction, variant calling, microarray simulation, and lineage evaluation) directly from the terminal without relying on the legacy GUI environment.

## Key Features

*   **Zero-Config Startup**: Support for `cli/.env.local` allows you to set global defaults for your reference library and input files.
*   **Automatic Resource Resolution**: The `ReferenceLibrary` engine automatically finds genomes, ploidy files, and microarray SNP tables from a single `--ref` directory.
*   **Synchronized Testing**: A robust four-tier test suite (136 tests total) ensures plumbing, error handling, robustness, and E2E behavioral correctness.
*   **Optimized for Speed**: Built-in `--region` support for heavy commands (sort, convert, coverage, variant calling) enables rapid processing of specific chromosomal regions like `chrM`.

## Dependencies

The `wgsextract-cli` relies on several industry-standard bioinformatics tools.

> ⚠️ **Platform Support Note**: macOS instructions have been verified on Apple Silicon. Windows (WSL2/Conda) and Linux instructions are currently **unverified** and provided as a best-effort guide.

### Required Tools
*   **Core:** `samtools`, `bcftools`, `htslib` (tabix/bgzip), `delly`, `freebayes`, `ensembl-vep`
*   **Aligners:** `bwa`, `minimap2`
*   **QC & Utils:** `fastp`, `fastqc`, `openjdk` (Java), `python3`, `pip`, `uv`

### 🛠️ Installation Scripts

You can find pre-written install/uninstall scripts for each platform in the [cli/dep_scripts/](dep_scripts/) directory.

#### macOS (using Homebrew) — ✅ Verified
```bash
# Install (Note: VEP not available via brew, manual install required)
bash cli/dep_scripts/install_macos.sh

# Uninstall
bash cli/dep_scripts/uninstall_macos.sh
```

#### macOS / Linux (using Conda/Mamba) — ⚠️ Unverified
This is the recommended method for getting **Ensembl VEP** easily.
```bash
# Install (macOS)
bash cli/dep_scripts/install_macos_conda.sh

# Install (Linux)
bash cli/dep_scripts/install_linux_conda.sh

# Uninstall (macOS)
bash cli/dep_scripts/uninstall_macos_conda.sh

# Uninstall (Linux)
bash cli/dep_scripts/uninstall_linux_conda.sh
```

#### Ubuntu / Debian / Mint — ⚠️ Unverified
```bash
# Install
bash cli/dep_scripts/install_ubuntu.sh

# Uninstall
bash cli/dep_scripts/uninstall_ubuntu.sh
```

#### Fedora / RHEL / CentOS — ⚠️ Unverified
```bash
# Install
bash cli/dep_scripts/install_fedora.sh

# Uninstall
bash cli/dep_scripts/uninstall_fedora.sh
```

#### Arch Linux / Manjaro — ⚠️ Unverified
```bash
# Install
bash cli/dep_scripts/install_arch.sh

# Uninstall
bash cli/dep_scripts/uninstall_arch.sh
```

#### Windows (WSL2 / PowerShell) — ⚠️ Unverified
We strongly recommend using **WSL2 (Ubuntu)** for the best experience. If using native Windows, you can use **Conda/Mamba**:

```powershell
# Install via Conda (PowerShell)
./cli/dep_scripts/install_windows_conda.ps1

# Uninstall
./cli/dep_scripts/uninstall_windows_conda.ps1
```

---

## Installation

```bash
# Clone the repository and navigate into the CLI directory
cd cli

# Install using uv (Recommended)
uv pip install -e .

# Or using standard pip
pip install -e .
```

## Environment Configuration

Copy the template to create your local configuration:
```bash
cp cli/.env.example cli/.env.local
```
Edit `cli/.env.local` to set your paths:
*   `WGSE_REF`: Path to your reference genome folder.
*   `WGSE_INPUT`: Default BAM/CRAM file for testing/identification.

Once set, global arguments like `--ref` and `--input` become optional for many commands.

## UI Wrapper

For non-technical users or those who prefer a more interactive experience, the CLI tool includes a modern UI wrapper.

### 🎨 Graphical User Interface (GUI)
A modern desktop application built with `CustomTkinter`. It provides file browsers and intuitive forms for common tasks.
```bash
wgsextract-cli gui
```

## Usage

### Direct Command
```bash
wgsextract-cli info --detailed
```

### Wrapper Script (Recommended for development)
```bash
# From within the cli directory
./wgsextract info --detailed
```

### Module Mode (Advanced)
```bash
# From project root
PYTHONPATH=cli/src uv run python -m wgsextract_cli.main bam identify
```

### All Subcommands (34 Combinations)
*   `info`: plain, `--detailed`, `calculate-coverage`, `coverage-sample`
*   `bam`: `sort`, `index`, `unindex`, `unsort`, `to-cram`, `to-bam`, `unalign`, `identify`
*   `extract`: `mt-bam`, `mito-fasta`, `mito-vcf`, `ydna-bam`, `ydna-vcf`, `y-mt-extract`, `bam-subset`, `unmapped`, `custom`
*   `vcf`: `snp`, `indel`, `annotate`, `filter`, `sv`, `cnv`, `freebayes`, `gatk`, `deepvariant`, `trio`, `vep-run`
*   `microarray`: Generate simulation kit
*   `lineage`: `mt-haplogroup` (Haplogrep), `y-haplogroup` (Yleaf)
*   `repair`: `ftdna-bam`, `ftdna-vcf`
*   `qc`: `fastp`, `fastqc`, `vcf`, `coverage-wgs`, `coverage-wes`
*   `pet-align`: Species-specific alignment and calling
*   `ref`: `download`, `index`
*   `align`: FASTQ to BAM/CRAM alignment

## Testing Suite

All tests are synchronized to cover the same 34 command combinations.

### 1. Smoke Tests (Mocked Plumbing)
Verifies subcommand registration and argument parsing in milliseconds.
```bash
uv run python cli/tests/test_smoke.py
```

### 2. Graceful Exit Tests (Resilience)
Ensures immediate exit (3s timeout) and informative errors for missing arguments.
```bash
uv run python cli/tests/test_graceful_exit.py
```

### 3. Robustness Tests (Stability)
Verifies no tracebacks are generated when provided with invalid path types (e.g. directories instead of files).
```bash
uv run python cli/tests/test_robustness.py
```

### 4. E2E Tests (Real Data & Benchmarks)

Real-world verification using a sorted BAM/CRAM and a reference genome:

1. **Configure Paths**: Create a `cli/.env.local` file:
   ```env
   WGSE_REF="/path/to/reference/folder"
   WGSE_INPUT="/path/to/sample.cram"
   ```

2. **Run Focused Tests (Fast)**: Target `chrM` to verify tool logic in minutes.
   ```bash
   uv run python cli/tests/test_e2e_fast_chrM.py
   ```

3. **Run Full Genome (Rigorous)**: Process the entire file for final validation.
   ```bash
   uv run python cli/tests/test_e2e_full_genome.py
   ```

### 5. Unit Tests
Specific logic for metrics and formatting.
*   `cli/tests/test_info.py`
*   `cli/tests/test_warnings.py`
