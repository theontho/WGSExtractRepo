# WGS Extract CLI (`wgsextract-cli`)

A completely independent, modern command-line interface for the WGS Extract application. This tool allows users to perform bioinformatics workflows (BAM/CRAM management, extraction, variant calling, microarray simulation, and lineage evaluation) directly from the terminal without relying on the legacy GUI environment.

## Key Features

*   **Zero-Config Startup**: Support for `cli/.env.local` allows you to set global defaults for your reference library and input files.
*   **Automatic Resource Resolution**: The `ReferenceLibrary` engine automatically finds genomes, ploidy files, and microarray SNP tables from a single `--ref` directory.
*   **Synchronized Testing**: A robust four-tier test suite (136 tests total) ensures plumbing, error handling, robustness, and E2E behavioral correctness.
*   **Optimized for Speed**: Built-in `--region` support for heavy commands (sort, convert, coverage, variant calling) enables rapid processing of specific chromosomal regions like `chrM`.

## Requirements

This CLI assumes that you have standard bioinformatics tools installed and accessible on your system's `$PATH`.

*   **Core:** `samtools`, `bcftools`, `tabix`, `bgzip`
*   **Aligners:** `bwa`, `minimap2`
*   **QC Tools:** `fastp`, `fastqc` (requires `java`)
*   **Lineage Tools:** `java` (for Haplogrep), `python3` (for Yleaf)
*   **System Utilities:** `awk`, `sed`, `zip`, `wget`

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

## Usage

### Direct Command
```bash
wgsextract-cli info --detailed
```

### Module Mode (Advanced)
```bash
# From project root
PYTHONPATH=cli/src uv run python -m wgsextract_cli.main ref identify
```

### All Subcommands (34 Combinations)
*   `info`: plain, `--detailed`, `calculate-coverage`, `coverage-sample`
*   `bam`: `sort`, `index`, `unindex`, `unsort`, `to-cram`, `to-bam`, `unalign`, `subset`
*   `extract`: `mito`, `ydna`, `unmapped`
*   `vcf`: `snp`, `indel`, `annotate`, `filter`, `qc`
*   `microarray`: Generate simulation kit
*   `lineage`: `mt-dna` (Haplogrep), `y-dna` (Yleaf)
*   `repair`: `ftdna-bam`, `ftdna-vcf`
*   `qc`: `fastp`, `fastqc`, `coverage-wgs`, `coverage-wes`
*   `ref`: `identify`, `download`, `index`
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
Actual tool execution on `chrM` with performance reporting.
```bash
uv run python cli/tests/test_e2e.py
```

### 5. Unit Tests
Specific logic for metrics and formatting.
*   `cli/tests/test_info.py`
*   `cli/tests/test_warnings.py`
