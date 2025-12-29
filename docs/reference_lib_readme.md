## Content of the Reference Library provided with WGS Extract v4 Installation

You can relocate the library (this folder) with a setting inside the program.
It is often helpful to move the folder and its content before setting a new
location in the program.  The installer will also pick up on this relocated
setting and act accordingly. The majority of space will be taken up by the
Reference Genomes; none of which are installed until you request it in the
`Library.***` manager script.

### Liftover Chain file (ucsc.edu, T2T)
Used by Liftover in the Microarray generator when starting with a Build 38 model BAM.

* `hg38ToHg19.over.chain.gz`  (and corresponding `.gzi` index file)
  > **note**: this is actually a rCRS to Yoruba chain file. See [https://console.cloud.google.com/storage/browser/hail-common/references/](https://console.cloud.google.com/storage/browser/hail-common/references/) for a proper 38 to 37 chain file that has a mito noop.
* `chm13v2-{grch38, hg19}.chain` for T2T chm13v2 to Build38 and 37
* `{grch38m hg19}-chm13v2.chain` for Build 38 / 37 to T2T chm13v2

### Y Chromosome SNPs file (yBrowse.org)
Used by Y DNA VCF file generator.

* `snps_hg38.vcf.gz`, `snps_grch38.vcf.gz` -- Build 38 files in `chrN` and `N` nomenclature; respectively
* `snps_hg19.vcf.gz`, `snps_grch38.vcf.gz` -- Build 37 files in `chrN` and `N` nomenclature; respectively
* (and corresponding `.gzi` and `.tbi` index files)

> (note: original hg19 had some errors and had not been updated since 2017. Now corrected. Original left here with added `.orig` suffix)

### Exome BED Files for determing WES regions ()
* Original TruSeq from Illumina for Build 37:
  [https://support.illumina.com/downloads/truseq-exome-product-files.html](https://support.illumina.com/downloads/truseq-exome-product-files.html)
* Build38 form converted from TruSeq by BioBank:
  [https://biobank.ndph.ox.ac.uk/ukb/refer.cgi?id=3803](https://biobank.ndph.ox.ac.uk/ukb/refer.cgi?id=3803)

* `TruSeq_Exome_TargetedRegions_v1.2.bed` -- Build 37 `chrN` nomenclature
* `TruSeq_Exome_TargetedRegions_v1.2_GRCh.bed` -- Build 37 `N` nomenclature
* `xgen_plus_spikein.GRCh38.bed`, `xgen_plus_spikein.GRCh38.GRCh.bed` -- Build 38 `chrN` and `N` nomenclature

### Y Chromosome BED files (with mito added)
For use in the WES buttons on Y-only (or Y and MT only) BAM files.  We use
the Phylogenetic Tree of Haplogroup communiy regions BED instead of the Y 
Exome BED. Original is from a spreadsheet of HG38 regions created by
David Vance from various sources (Ian McDonalds paper, yFull data, FTDNA
data). See the user manual for more details.

* `BigY3_hg*.bed` - various Y BED files specific to FTDNA BigY-700 test
* `CombBED_McDonald_Poznik_Merged_hg*.bed` - various BED files as mentioned above; as created from David Vance's spreadsheet

### Genomes Seed definition file
Copied into `Genomes/` on first use. Used by `Library` and `get_and_process_refgenome.sh` scripts.

* `seed_genomes.csv`

### `Genomes/`
Starts as an empty folder.  Filled by `Library.***` command and Ref Genome Library scripts in `scripts/`:

* `process_refgenomes.sh` -- sript to index any available reference genomes (called by `get_and_process_refgenomes.sh`)
* `compare_refgenomes.sh` -- script to compare two reference genomes based on extracted stats
* `get_and_process_refgenome.sh` -- script to individually download and process each reference genome for use in the program. Called by the `Library.*` tool and the WGS Extract program itself.
* `bwa-kit-gen-ref.sh`   -- modified (updated, corrected) script from `bwa-kit` to make 1K Genome project reference models (aka `hsxxxx`)

### `Microarray/`
* All Variants file to create CombinedKit from BAM; one for each build and naming style
* Microarray RAW file templates for headers and bodies to target generating microarray files
* Ploidy definition file
