# WGS Extract CLI (`wgsextract-cli`)

A completely independent, modern command-line interface for the WGS Extract application. This tool allows users to perform bioinformatics workflows (BAM/CRAM management, extraction, variant calling, microarray simulation, and lineage evaluation) directly from the terminal without relying on the legacy GUI environment.

## Requirements

This CLI adheres to a **No Environment Provisioning** constraint. It assumes that you have standard bioinformatics tools installed and accessible on your system's `$PATH`.

Required Tools:
*   **Core:** `samtools`, `bcftools`, `tabix`, `bgzip`
*   **Aligners:** `bwa`, `minimap2`
*   **QC Tools:** `fastp`, `fastqc` (requires `java`)
*   **Lineage Tools:** `java` (for Haplogrep), `python3` (for Yleaf)
*   **System Utilities:** `awk`, `sed`, `zip`, `wget`

## Installation

```bash
# Clone the repository and navigate into the CLI directory
cd cli

# Install using pip or uv
uv pip install -e .
```

## Usage

### Installed Usage
If you installed the package, the command is available directly:
```bash
wgsextract-cli --help
```

### Running without installing
If you prefer not to install the package, you can run it directly from the source code.

**Using `uv` (Recommended):**
`uv run` automatically sets up the environment and executes the code based on the `pyproject.toml` file in the current directory:
```bash
uv run python -m wgsextract_cli.main --help
```

**Using standard Python:**
You can tell Python to look in the `src` folder before executing the module:
```bash
PYTHONPATH=src python3 -m wgsextract_cli.main --help
```

See the subcommands for details on running specific pipelines (`info`, `bam`, `extract`, `microarray`, `lineage`, `vcf`, `repair`, `qc`, `ref`, `align`).

## Testing

The CLI includes a comprehensive test suite ranging from fast logic checks to full end-to-end processing with real data.

### 1. Fast logic and integration tests (Mocked)
These tests use "mocks" to simulate bioinformatics tools. They are extremely fast and do not require real BAM/CRAM files.

```bash
# Run from the cli/ directory
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 -m unittest discover tests
```

Tests include:
*   `test_warnings.py`: Time estimation and disk space logic.
*   `test_info.py`: Reference model and gender detection logic.
*   `test_commands_integration.py`: Verifies CLI subcommands trigger warnings correctly.
*   `test_graceful_exit.py`: Ensures commands handle missing arguments without crashing.
*   `test_robustness.py`: Checks directory-as-reference handling.

### 2. Smoke Tests (Real Headers)
Tests path resolution and `samtools view -H` against your real files, while mocking the heavy work.

```bash
export WGSE_REF="path/to/reference/folder/"
export WGSE_INPUT="path/to/your/sample.cram"
python3 tests/test_real_data_smoke.py
```

### 3. End-to-End Tests (Full Processing)
Runs actual `samtools` and `bcftools` pipelines on real data. This is slow and generates real output in a temporary directory.

```bash
export WGSE_REF="path/to/reference/folder/"
export WGSE_INPUT="path/to/your/sample.cram"
python3 tests/test_e2e_real_data.py
```
