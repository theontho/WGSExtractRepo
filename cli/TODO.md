# WGS Extract Todo List

This document outlines the planned features, improvements, and bug fixes for WGS Extract. Items are categorized by their relevance to the **CLI (Engine)** and the **GUI (Interface)**.

## 🚀 Strategic & High Priority
- [x] **Merge v5 Changes**: (Engine) Integrated major updates including DeepVariant, GATK, and Trio analysis.
- [ ] **Automated Release Process**: (Infrastructure) Implement GitHub Actions for platform-specific installers.
- [x] **Modernization**: (Technical Debt) Fully transitioned to `uv` and `pyproject.toml`.
- [ ] **Move to GitHub Issues**: (Project Mgmt) Migrate this list to GitHub Issues for better tracking.

---

## 💻 CLI & Core Engine (Functional Enhancements)

### VCF & Variant Calling
- [x] **VCF Action Buttons (Backend)**: Engine logic for InDel, CNV, SV, and Filtering is complete.
- [x] **Robust InDel Support**: Insertions/Deletions included in microarray and variant calling.
- [x] **VCF Annotator**: Engine-level annotation for rsIDs, SNPs, and gene info (VEP supported).
- [x] **Additional Variant Callers**: FreeBayes and DeepVariant/GATK integrated.
- [ ] **Consensus Sequence Generation**: (New) Implement `vcf to-fasta` to generate a full consensus FASTA from VCF + Ref.

### 🧬 Gene Analysis & Clinical Interpretation
- [x] **Gene-Centric Workflows**: Filter VCFs and BAMs by Gene Name or HGNC ID.
- [x] **Inheritance & Trio Analysis**: Detect De Novo mutations and Compound Heterozygotes.
- [x] **Population Frequency Integration**: (Priority) Annotate variants with gnomAD, ExAC, and 1000 Genomes.
- [x] **ClinVar clinical significance**: Report "Pathogenic" status from ClinVar using `vcf clinvar`.
- [x] **REVEL Pathogenicity Scores**: Annotate missense variants with REVEL scores.
- [x] **Modern Pathogenicity Support**: Added AlphaMissense (Google DeepMind) and SpliceAI (Illumina).
- [x] **Pharmacogenomics (PharmGKB)**: Support for annotating drug metabolism variants.
- [ ] **Pathogenicity & Conservation**: Support for CADD, SIFT, PolyPhen-2, PhyloP (DONE), and GERP++.

### BAM/CRAM Processing
- [x] **mtDNA/Y-DNA Extraction**: Dedicated `mito` and `ydna` commands.
- [ ] **BAM/CRAM Merging**: (New) Add `bam merge` utility for multiple alignment files.
- [ ] **uBAM (Unaligned BAM) Creator**: (New) Convert FASTQ/BAM to unaligned BAM for GATK pipelines.
- [x] **MD5 Integrity Checks**: Automated MD5sum checking for reference genomes.
- [x] **Performance Boost**: Integrated `sambamba` and `samblaster` for faster processing (with macOS fallback).

### Microarray & Specialized Analysis
- [x] **Pet Sequencing Support**: Dog/cat genome support (align, extract, lineage).
- [ ] **Legacy Format Support**: 23andMe v1, FTDNA v1, etc.
- [ ] **Digital Signing**: Routine to digitally sign output files for verification.
- [ ] **Advanced Typing**: HLA Typing and STR Variant Calling.

### CLI Improvements
- [x] **CLI Robustness**: Improved parameter handling and "Auto Mode" reliability.
- [x] **Pixi Environment Management**: Cross-platform dependency isolation and automatic fallback.
- [ ] **Parallel Microarray Generation**: (In Progress) Implement `--parallel` flag for per-chromosome calling.
- [x] **JSON/TSV Output**: Machine-readable formats for all stats and results.
- [x] **Smoke Test Coverage**: Full CLI coverage with automated tests.

---

## 🎨 GUI Specific (User Interface & Experience)

### Web-based GUI (v0)
- [x] **Modular Architecture**: Transitioned from Tkinter to a modern Web-based GUI.
- [x] **Full Functional Parity**: All CLI commands accessible via Web interface.
- [x] **Live Progress Tracking**: Real-time bars for downloads, alignment, and annotation.
- [x] **Cancel Button**: Functional "Cancel/Abort" for backend processes.
- [ ] **Interactive VCF Viewer**: (Next) Search and filter VCFs directly in the Web UI.

---

## 🛠️ Technical Debt & Known Bugs

### Technical Debt
- [x] **Python Integration**: Ported core Bash scripts to native Python.
- [x] **Tooling Updates**: Updated samtools, bcftools, and other binaries.
- [x] **Path Validation**: Fixed `verify_paths_exist` to support Pixi command strings and restricted environments.

### Known Bugs
- [x] **Cross-Platform TTY Issues**: Resolved terminal TTY bugs.
- [ ] **samtools Hangs**: Fix `markdup` and `fastq` hangs on specific MGI/Dante files.
- [x] **yleaf Integration**: Fixed command naming and resolved execution issues on macOS ARM.
