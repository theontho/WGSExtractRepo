# WGS Extract Todo List

This document outlines the planned features, improvements, and bug fixes for WGS Extract. Items are categorized by their relevance to the **CLI (Engine)** and the **GUI (Interface)**.

## 🚀 Strategic & High Priority
- [ ] **Merge v5 Changes**: (Engine) Integrate the major update from the internal v5 development branch.
- [ ] **Automated Release Process**: (Infrastructure) Implement GitHub Actions for platform-specific installers.
- [ ] **Modernization**: (Technical Debt) Continue modernizing with `uv` and `pyproject.toml`.
- [ ] **Move to GitHub Issues**: (Project Mgmt) Migrate this list to GitHub Issues for better tracking.

---

## 💻 CLI & Core Engine (Functional Enhancements)
*These features improve the underlying processing logic and should be implemented in the engine to be accessible via both CLI and GUI.*

### VCF & Variant Calling
- [x] **VCF Action Buttons (Backend)**: Complete the engine logic for InDel, CNV, SV, and Filtering.
- [x] **Robust InDel Support**: Properly call and include Insertions/Deletions in microarray and variant calling.
- [x] **VCF Annotator**: Implement engine-level annotation for rsIDs, SNP names, and gene info. (Added auto-resolution and VEP support).
- [x] **Additional Variant Callers**: Integrate FreeBayes, Platypus, or Scalpel as engine options. (Added FreeBayes).
- [x] **DeepVariant/GATK Integration**: Add support for these industry-standard callers in the backend.

### 🧬 Gene Analysis & Clinical Interpretation
*Inspired by gene.iobio, these features focus on making variants actionable and medically relevant.*

- [ ] **Population Frequency Integration**: Add engine support for annotating variants with gnomAD, ExAC, and 1000 Genomes frequencies.
- [ ] **ClinVar clinical significance**: Automatically check and report if variants are listed as "Pathogenic" in ClinVar.
- [ ] **Advanced Pathogenicity Scores**: Implement support for CADD, SIFT, and PolyPhen-2 score annotation.
- [x] **Gene-Centric Workflows**: Add a CLI command to filter VCFs by a specific Gene Name or HGNC ID.
- [x] **Inheritance & Trio Analysis**: Add logic to detect De Novo mutations and Compound Heterozygotes in family trios.
- [ ] **Conservation Analysis**: Add annotation support for PhyloP and GERP++ conservation scores.
- [ ] **Phenotype-to-Gene Ranking**: Integrate Phenolyzer or HPO-based gene prioritization into the engine.

### BAM/CRAM Processing
- [x] **mtDNA BAM Extraction**: Add a dedicated engine command to generate and save mtDNA-only BAMs.
- [ ] **BAM/CRAM Merging**: Add a utility to merge multiple alignment files.
- [ ] **Unaligned BAM Creator**: Add a tool to create unaligned BAMs for specific pipelines.
- [x] **MD5 Integrity Checks**: Implement automated MD5sum checking for reference genome files.
- [ ] **Sambamba/Samblaster Integration**: Evaluate and integrate these for faster Y/MT extraction and marking duplicates.

### Microarray & Specialized Analysis
- [ ] **Legacy Format Support**: Add engine support for 23andMe v1, FTDNA v1, and other older formats.
- [ ] **Digital Signing**: Implement a routine to digitally sign output files for quality verification.
- [ ] **HLA Typing**: Integrate HLA-HD or similar engine-level tools.
- [ ] **STR Variant Caller**: Add engine support for STR calling (e.g., HipSTR, GangSTR).
- [ ] **Consensus Sequence Generation**: Implement BAM/VCF to FASTA consensus logic.

### CLI Improvements
- [x] **CLI Robustness**: Improve parameter error handling and "Auto Mode" reliability.
- [ ] **Parallel Microarray Generation**: Fully implement and test the `--parallel` flag for per-chromosome variant calling in the CLI.
- [x] **JSON/TSV Output**: Ensure CLI commands can output machine-readable formats (JSON/TSV) for all stats and results. (Added JSON metrics caching).

---

## 🎨 GUI Specific (User Interface & Experience)
*These features are specific to the Tkinter-based (or future) graphical interface.*

### UI Enhancements
- [ ] **GUI Modernization**: Evaluate migrating from Tkinter to a more modern framework (GTK, Qt, or Web-based).
- [ ] **Selectable Text**: Fix the limitation where text in result windows cannot be selected or copied.
- [ ] **Cancel Button**: Add a functional "Cancel/Abort" button to the "Please Wait" dialog.
- [ ] **Live Progress Tracking**: Implement better progress bars that update based on real-time tool output.
- [ ] **Terminal Log "Teeing"**: Create a GUI-accessible log viewer that shows the real-time output of background tools.
- [ ] **Font & Scaling Fixes**: Resolve inconsistencies between macOS, Windows, and Linux/WSLG fonts.
- [ ] **BAM Subset GUI**: Create a visual chromosome selector for creating subset BAMs.

### UX Improvements
- [ ] **Reference Library Browser**: A dedicated GUI tab to view, manage, and download reference genomes.
- [ ] **Sample Manager**: A GUI concept that treats a folder as a "Sample" (grouping FASTQs, BAMs, and VCFs).
- [ ] **Interactive VCF Viewer**: Integrate a tool like VarSifter or a custom viewer for searching VCFs within the GUI.

---

## 🛠️ Technical Debt & Known Bugs

### Technical Debt
- [ ] **Python Integration**: Port remaining Bash scripts (e.g., reference management) into native Python.
- [ ] **Tooling Updates**: Update bundled bioinformatics binaries (samtools, bcftools, etc.).
- [ ] **Path Validation**: Fix the `is_legal_path` logic for output directories.

### Known Bugs
- [ ] **samtools markdup Hang**: Fix hang on specific Dante MGI files.
- [ ] **samtools fastq Hang**: Fix hang during unaligning on certain BAMs.
- [ ] **yleaf Crash**: Fix crash on early HG19 delivered files.
- [ ] **Tkinter Style Inconsistencies**: Fix gray-shading and button coloring issues on macOS/WSLG.
