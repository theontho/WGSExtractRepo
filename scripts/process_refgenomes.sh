#!/usr/bin/env bash
# Process Reference Genomes
# A standalone or sourced script to process Reference Genome files or folder for use in Bioinformatic tools
# 
# If a directory specified, the script naively presumes any file in the folder with the correct extension
#   is a FASTA file.
#
# Part of the Reference Genome package in WGS Extract (https://wgsextract.github.io/)
# Copyright (c) 2020-23 Randy Harr
#

# -----------------------------------------------------------------------------------------------------------------
# Programs used (that must be available on the PATH):
# gunzip, unzip, bunzip2, 7z, sort, cut, (g)awk, sed, grep, tail, head, wc, md5sum, rm, bgzip, htsfile, samtools

np=16         # Number of Processors to use when available for bgzip  (Todo should read from system)
LANG=POSIX		# Needed for sort command

usage() {
  printf "Usage: %s [option]   where options is:\n" "${BASH_SOURCE[0]##*/}"
  printf "     [directory]  # All FASTA files in the directory; use dot (.) for current.\n"
  printf "  or [file(s)]    # Provide a list of FASTA files to process.\n"
  printf "  or clean        # Remove all files created by this script\n"
  printf "  or clean_all    # Remove all files; including any reference genomes\n"
  printf "When a whole directory is specified, files with an extension\n"
  printf " fa, fna, fasta, gz, zip, bz, bz2, or 7z are treated as FASTAs.\n"
  printf "\n"
  printf "Processes Reference Genome FASTA files to the correct compression  format.  Then\n"
  printf "  create the DICT file & index files needed by the tools.  Finally  catalog  the\n"
  printf "  file for WGSE use. Processing a whole directory causes the catalog to be first\n"
  printf "  cleared (mini-clean).  Otherwise,  the catalog is appended with any  processed\n"
  printf "  file(s). Files newer than the FASTA are not changed.\n"
  (return 0 2>/dev/null) && return 1 || exit 1
}


#---------------------------------- Setup common environment ------------------------------------------------------

[[ ":$PATH:" != *":/usr/bin:"* ]] && PATH="/usr/bin:${PATH}" && export PATH
[[ ":$PATH:" != *":/ucrt64/bin:"* ]] && PATH="/ucrt64/bin:${PATH}"

# Occassionally, we are finding Windows is setting new files with 060 permissions. Hence more aggressive on setting.

if [[ -z $wgse_FP ]] ; then
  # Find the installation directory
  declare -x wgse_FP
  _wgsedir=$(dirname "${BASH_SOURCE[0]}")       # Get the (calling) script location to determine the install directory
  _wgseabs=$( cd "$_wgsedir" || true ; pwd -P ) # Resolve any aliases and symlinks (readlink not available)
  [[ $(basename "$_wgseabs") == "scripts" ]] && wgse_FP=$(dirname "$_wgseabs") || wgse_FP="$_wgseabs" # not in scripts/

fi

# cd "$wgse_FP" || true   # Need to retain current directory as file/dir parameters likely have relative path specs

if ! declare -f _perform_rmx > /dev/null ; then
  # When running stand-alone, must retain the starting directory to find any specified relative path files
  # pushd "$wgse_FP" || true

  declare -x pythonx owgse_FP
  declare -f cdx mvx rmx readq _perform_rmx >/dev/null
  # shellcheck source=./zcommon.sh
  source "${wgse_FP}/scripts/zcommon.sh" "$wgse_FP"  || onError "ERROR: Cannot source scripts/zcommon.sh" # includes exit 

  # popd
fi


#
# This script works off a directory or a file parameter list passed as parameters
#   * If parameter list is one or more files, it works off that.
#   * If a single directory specified, it works off the matching files in that directory.
# If a directory specified, it tries to find all Reference Genomes (actually, FASTA files) using common extensions.
# It uses each identified FASTA as the base.  
# It can be run a second time and will simply do any needed updates. So if errors are fixed, simply rerun.
#  Only difference is the WGSE.csv file is appended to on each run (cleared first on directory processing).
#
# NOTE: We have commented out the BWA Index command due to the extensive resource usage (CPU and file space) for
#  doing BWA indices.  It is simply part of the main python code and run when needed.  Also different aligners have
#  different index files as it is.
#


# -----------------------------------------------------------------------------------------------------------------
# Check and Process arguments

# Figure out what we have to do in the reflib genomes directory; or if explicitly set in the parameter list
# That way we know how to respond with usage; if needed
shopt -s nullglob
sumFPB="WGSE"
if [[ $# -eq 1 && "$1" == "clean" ]] ; then
  rmx ./*fai ./*gzi ./*dict
  rmx ./*wgse "${sumFPB}.csv" "${sumFPB}_dict*csv" "${sumFPB}_uniq*csv"    # Created here
  (return 0 2>/dev/null) && return || exit

elif [[ $# -eq 1 &&"$1" == "clean_all" ]] ; then
  rmx ./*fai ./*gzi ./*dict ./*wgse "${sumFPB}.csv" "${sumFPB}_dict*csv" "${sumFPB}_uniq*csv"   # Created here
  rmx ./*amb ./*ann ./*bwt ./*pac ./*sa   # BWA Index files (if enabled)

  readq 'Do you really want to remove ALL the reference genomes in  [y/N]?'
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    rmx ./*fa.gz ./*fasta.gz ./*fna.gz  # Delete downloaded reference genomes; get back to original folder

  else
    echo ' ... leaving reference genomes alone.'

  fi

  (return 0 2>/dev/null) && return || exit

elif [[ $# -eq 1 && -d "$1" ]] ; then   # Single, directory parameter. Create a file list from content. Could be '.'
  file_list=("$1"/*.{fa,fna,fasta,7z,gz,zip,bz,bz2})  # Put all matching files in the dir into a file list
  if [[ $1 != "." ]] ; then
    sumFPB="$1"/WGSE

  fi

  # Want to process whole directory; so start with clean slate of summary files (catalog cleared)
  rmx "${sumFPB}.csv" "${sumFPB}_dict.csv" "$1"/*wgse
  rmx "${sumFPB}_uniq_build.csv" "${sumFPB}_uniq_ChrLNM5.csv" "${sumFPB}_uniq_SNcnt.csv" "${sumFPB}_uniq_ChrSN.csv"
  rmx "${sumFPB}_dict_uniq_SNLNM5.csv" "${sumFPB}_dict_uniq_LNM5.csv"
  wholedir=true

else
  file_list=( "$@" )    # One or more file specs; convert to file list. (will kick out later if one spec is a dir)
  wholedir=false

fi

# Now that we have processed the passed parameters, we can determine usage in case no file(s) or directory passed in
(( ${#file_list[@]} == 0 )) && usage
(( ${#file_list[@]} == 1 )) && multi=false || multi=true


# -----------------------------------------------------------------------------------------------------------------
# Setup variables for finding primary chromosomes.  Use LN entries as main source. But some alt contigs have
#  same length.  So also then filter by common SN names. Should change to read in a file / table that we can update.
#
# Build   15/(33)        16/34         17/35         18/36         19/37         (20)/38       hg01243 v3    chm13 v0.9    chm13 v1.1    chm13 v1.0 (chm13 v0.7 X, hg002 v2 XY, hg002 v2.7 XY)
chr[0]="LN:245203898\|LN:246127941\|LN:245522847\|LN:247249719\|LN:249250621\|LN:248956422\|LN:248415701\|LN:248387561\|LN:248387328\|LN:248387497"  # chr1
chr[1]="LN:243315028\|LN:243615958\|LN:243018229\|LN:242951149\|LN:243199373\|LN:242193529\|LN:242509959\|LN:242696759\|LN:242696752\|LN:242696747"  # chr2
chr[2]="LN:199411731\|LN:199344050\|LN:199505740\|LN:199501827\|LN:198022430\|LN:198295559\|LN:200717518\|LN:201106621\|LN:201105948\|LN:201106605"  # chr3
chr[3]="LN:191610523\|LN:191731959\|LN:191411218\|LN:191273063\|LN:191154276\|LN:190214555\|LN:193408891\|LN:193575384\|LN:193574945\|LN:193575430"  # chr4
chr[4]="LN:180967295\|LN:181034922\|LN:180857866\|LN:180857866\|LN:180915260\|LN:181538259\|LN:182049998\|LN:182045443\|LN:182045439\|LN:182045437"  # chr5
chr[5]="LN:170740541\|LN:170914576\|LN:170975699\|LN:170899992\|LN:171115067\|LN:170805979\|LN:171893897\|LN:172126875\|LN:172126628\|LN:172126870"  # chr6
chr[6]="LN:158431299\|LN:158545518\|LN:158628139\|LN:158821424\|LN:159138663\|LN:159345973\|LN:160394084\|LN:160567465\|LN:160567428\|LN:160567423"  # chr7
chr[7]="LN:145908738\|LN:146308819\|LN:146274826\|LN:146274826\|LN:146364022\|LN:145138636\|LN:146097661\|LN:146259347\|LN:146259331\|LN:146259322"  # chr8
chr[8]="LN:134505819\|LN:136372045\|LN:138429268\|LN:140273252\|LN:141213431\|LN:138394717\|LN:149697505\|LN:150617238\|LN:150617247\|LN:150617274"  # chr9
chr[9]="LN:135480874\|LN:135037215\|LN:135413628\|LN:135374737\|LN:135534747\|LN:133797422\|LN:134341430\|LN:134758139\|LN:134758134\|LN:134758122"  # chr10
chr[10]="LN:134978784\|LN:134482954\|LN:134452384\|LN:134452384\|LN:135006516\|LN:135086622\|LN:134654341\|LN:135129789\|LN:135127769\|LN:135127772" # chr11
chr[11]="LN:133464434\|LN:132078379\|LN:132449811\|LN:132349534\|LN:133851895\|LN:133275309\|LN:133439878\|LN:133324792\|LN:133324548\|LN:133324781" # chr12
chr[12]="LN:114151656\|LN:113042980\|LN:114142980\|LN:114142980\|LN:115169878\|LN:114364328\|LN:113815969\|LN:114240132\|LN:113566686\|LN:114240146" # chr13
chr[13]="LN:105311216\|LN:105311216\|LN:106368585\|LN:106368585\|LN:107349540\|LN:107043718\|LN:100860689\|LN:101219190\|LN:101161492\|LN:101219177" # chr14
chr[14]="LN:100114055\|LN:100256656\|LN:100338915\|LN:100338915\|LN:102531392\|LN:101991189\|LN:99808683\|LN:100338336\|LN:99753195\|LN:100338308"   # chr15
chr[15]="LN:89995999\|LN:90041932\|LN:88827254\|LN:88827254\|LN:90354753\|LN:90338345\|LN:96296229\|LN:96330509\|LN:96330374\|LN:96330493"           # chr16
chr[16]="LN:81691216\|LN:81860266\|LN:78774742\|LN:78774742\|LN:81195210\|LN:83257441\|LN:83946371\|LN:84277212\|LN:84276897\|LN:84277185"           # chr17
chr[17]="LN:77753510\|LN:76115139\|LN:76117153\|LN:76117153\|LN:78077248\|LN:80373285\|LN:80696073\|LN:80537682\|LN:80542538\|LN:80542536"           # chr18
chr[18]="LN:63790860\|LN:63811651\|LN:63811651\|LN:63811651\|LN:59128983\|LN:58617616\|LN:61612450\|LN:61707413\|LN:61707364\|LN:61707359"           # chr19
chr[19]="LN:63644868\|LN:63741868\|LN:62435964\|LN:62435964\|LN:63025520\|LN:64444167\|LN:67262993\|LN:66210261\|LN:66210255\|LN:66210247"           # chr20
chr[20]="LN:46976537\|LN:46976097\|LN:46944323\|LN:46944323\|LN:48129895\|LN:46709983\|LN:44996062\|LN:45827694\|LN:45090682\|LN:45827691"           # chr21
chr[21]="LN:49476972\|LN:49396972\|LN:49554710\|LN:49691432\|LN:51304566\|LN:50818468\|LN:51228122\|LN:51353916\|LN:51324926\|LN:51353906"           # chr22
chr[22]="LN:152634166\|LN:153692391\|LN:154824264\|LN:154913754\|LN:155270560\|LN:156040895\|LN:154343774\|LN:154259664\|LN:154259566\|LN:154259625\|LN:154269076\|LN:154349815\|LN:154434329"  # chrX
chr[23]="LN:50961097\|LN:50286555\|LN:57701691\|LN:57772954\|LN:59373566\|LN:57227415\|LN:62480187\|LN:62456832\|LN:62460029"                        # chrY (hg002 but no CHM13 entries)

# Need separate chromosomes later so define array per chromosome first above and then concatenate to form chrl
chrl=${chr[0]}
for val in "${chr[@]:1}" ; do
  chrl+="\|${val}"
done

# Some alt contigs have same length as a chromosome; so further refine selection by known primary entry SNs (prefix)
chrsnhg="SN:CHR[1-9XY]\>\|SN:CHR1[0-9]\>\|SN:CHR2[0-2]\>\|SN:CHRX_V0.7"  # HGP naming (special CHM13 v0.7)
chrsneb="SN:[1-9XY]\>\|SN:1[0-9]\>\|SN:2[012]\>"                         # EBI naming
chrsngb="CM0006\|SN:NC_0000[0-2][0-9]\|CP0682[567]\|CP08656[89]\|CM0349[567]\|SN:CHR[XY]_HG002"    # Accession
chrsn="${chrsnhg}\|${chrsneb}\|${chrsngb}"
# Alt contig names in HGP and EBI start with full chromosome name; so make sure checking whole field (>)
# In accession naming, alt contigs have their own accession entries that start differently than the chromosomes


# -----------------------------------------------------------------------------------------------------------------
# Start processing ... first, setup global files if they do not exist.  Then loop on each argument / refgen file
printf "\n"
printf "================================================================================\n"
printf "Processing Reference Genome file(s) ...\n"
# echo "***DEBUG:${#file_list[@]} parameters: ${file_list[@]}"

# Setup initial csv summary file header if not yet written; for when initial processing of whole directory (TSV)
# Columns are: File Name, Major/Minor build code, SN Cnt ; MD5Sums: SN/LN, SN/LN/M5, LN/M5, Chromo SN, Chromo LN/M5 ;
#              Mito: SN, LN, M5 ; Error Message(s)
# Chromo LN/M5 identifies Major Build, Full LN/M5 the Minor Class (and also SN Cnt)
if [[ ! -f "${sumFPB}.csv" ]] ; then
  printf $'%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "File" "Build" "SN_CNT" "BAM_(SN,_LN)" "CRAM_(SN,_LN,_M5)" "FASTA_(LN,_M5)" "Chromo_(LN,_M5)" "Chromo_(SN)" \
    "Mito:_SN" "LN" "M5" "Message" "SNs" > "${sumFPB}.csv"
fi

# -----------------------------------------------------------------------------------------------------------------
# Loop through for each file to process ...

# Special use for Error / Warning within main processing loop. Uses $multi , $wholedir , $fbn
declare multi wholedir fbn
onError() {
  local err pref suff

  { $multi || $wholedir ; } && err=false || err=true

  # shellcheck disable=SC2015
  $err && { pref="ERROR" ; suff="Exiting" ; } || { pref+="WARNING" ; suff="Skipping file" ; }
  
  echo "$fbn: *** $pref: ${1}. ($suff)"
  
  $err    # return truthy of err -- 0 if true, 1 if false
}


for file in "${file_list[@]}"; do
  # echo "***DEBUG: file = $file ; cwd is $PWD"

  # For common case of using current directory, strip off ./ that starts each file name
  if [[ "${file:0:2}" == "./" ]]; then
    file=${file:2}
  fi

  # fpa=${file%/*}    # File path (if it exists)  (not used; but keep in case we need it later)
  fbn=${file##*/} # File base name
  ext=${file##*.} # File (last) extension

  # Check if even a file

  if [[ ! -f "$file" ]]; then
    # shellcheck disable=SC2015
    onError "Invalid file specified" && exit 1 || continue
  fi

  # Check if file content and extension correct; override permissions if set wrong
  touch "HTS.tmp" && chmod 777 "HTS.tmp" # cygwin64 sometimes defaulting to 060 permissions when created here
  chmod 775 "$file"                      # cygwin64 sometimes defaulting to 070 permissions after curl

  # here-documents from variable not working in cygwin bootstrap; so change to use a temp file
  # HTS=$(htsfile "$file") then could use <<< $HTS if here-documents are working
  htsfile "$file" >"HTS.tmp"

  if [[ "$ext" =~ ^(zip|7z|bz|bz2)$ ]]; then
    # htsfile cannot see in (to tell if FASTA) for .zip, .7z nor .bz2 archive formats (but does recognize bzip2 format)
    # So go ahead if those and check if a FASTA after recompressing; might recompress some non-bioinformatic files but ...
    # that is a risk the user takes if they do a general directory specification
    echo "$fbn: Cannot look into .zip/.bz/.bz2/.7z files; so recompressing to peak inside."

  elif grep -q -v "FASTA" "HTS.tmp"; then
    rmx "HTS.tmp"
    # shellcheck disable=SC2015
    onError "Non-FASTA file specified" && exit 1 || continue

  fi # simply fall through as next check determines if you need to recompress or not

  # ---------------------------------------------------------------------------------------------------------------
  # Check for bgzip compression form; (re)compress if not in that form
  if grep -q "FASTA BGZF" "HTS.tmp"; then
    # echo "$file: Already a BGZF compressed FASTA file!"   # simply keep silent
    filen="$file"

  else
    # OK, if here, is (likely) a FASTA but it is not BGZF compressed
    echo "$fbn: Fixing Reference Genome File compression"
    case "$ext" in
    gz) # BGZF already checked above; so must be gzipped
      {
        gzip -d -f "$file"
        bgzip -if@ $np "${file%.*}"
      } && filen="$file" ;;
      # This is the only format where you end up with the same file extension; they should have used .bgz but ...

    zip) # Likely zip'ped
      { unzip -p "$file" | bgzip -cf@ $np >"${file%.*}.gz"; } && rmx "$file" && filen="${file%.*}.gz" ;;

    7z) # A popular, very high compression format not normally seen in Bioinformatics
      { 7z e -mmt$np -so "$file" | bgzip -cf@ $np >"${file%.*}.gz"; } && rmx "$file" && filen="${file%.*}.gz" ;;

    bz | bz2) # A popular Linux/Unix/MacOSX high compression format sometimes seen in Bioinformatics
      { bunzip2 -cf "$file" | bgzip -cf@ $np >"${file%.*}.gz"; } && rmx "$file" && filen="${file%.*}.gz" ;;

    fa | fna | fasta) # Appears likely not compressed; but will check
      if grep -q -- "-compressed" "HTS.tmp"; then
        # shellcheck disable=SC2015
        onError "FASTA file is compressed but missing a .gz extension" && exit 1 || continue

      fi
      bgzip -if@ $np "$file"
      filen="$file.gz"
      ;;

    *) # Well that is embarrising
      # shellcheck disable=SC2015
      onError "Unknown file extension (internal error)" && exit 1 || continue
      ;;
    esac
    # Above does not handle .zip / .7z archive with multiple files (i.e. like tar+gzip combo from original pkzip)
    #  Singular, internal file name must be the same name as containing archive file without extension

    # Check again if matched file with extension is a valid, compressed FASTA file just to make sure
    if [[ ! -f "$filen" ]]; then
      # shellcheck disable=SC2015
      onError "Compression conversion failed (missing file)" && exit 1 || continue

    fi

    htsfile "$filen" > "HTS.tmp"        # HTS=$(htsfile "$filen")

    if grep -q -v "FASTA BGZF" "HTS.tmp"; then
      # shellcheck disable=SC2015
      onError "Compression conversion failed (not BGZF)" && exit 1 || continue

    fi
  fi

  rmx "HTS.tmp"

  # ---------------------------------------------------------------------------------------------------------------
  # Check and (re)create any supporting indices
  #
  # By this point, Ref Genome file ends in .gz, is a FASTA and is BGZF compressed. Does allow explicitely named file
  #  in parameter list that is a FASTA and BGZF compressed but without the proper extension (e.g. .fa.gz).
  #  Some programs will not allow that but who are we to judge.
  #
  # If file was properly compressed AND files to be created are up to date, nothing will get posted about this file!

  # (Re)create any missing or old indices (using a new filename $filen if compression changed)
  # GATK uses the .dict file and wants it to be named without {fasta,fa,fna}.gz extension so we oblige
  # Reminder: -nt is the BASH "file newer than" operator
  filed=$(echo "$filen" | sed "s/.fasta.gz//;s/.fna.gz//;s/.fa.gz//") # strip known extension to add .dict back on
  fbnn=${filen##*/}               # We use the whole filename for status reporting; so if changed need a new basename
  [ "$filen" -nt "${filed}.dict"     ] &&
    echo "$fbnn: Creating FA DICTionary"     && samtools dict "$filen" -o "$filed.dict"
  [ "$filen" -nt "${filen}.fai"      ] &&
    echo "$fbnn: Creating FA Index (FAI)"    && samtools faidx "$filen" # Usually creates .gzi as well
  [ "$filen" -nt "${filen}.gzi"      ] &&
    echo "$fbnn: Creating BGZip Index (GZI)" && bgzip -r "$filen"    # Also samtools index works
  [ "$filen" -nt "${filed}_ncnt.csv" ] &&
    echo "$fbnn: Counting N's (ncnt, nbin)"  && "$pythonx" "${owgse_FP}/program/countingNs.py" "$filen" | grep -v "INFO"

  # BWA Index creates .bwt (30 min, 3 GB), .pac (800MB), .ann, .amb, and .sa (10 min, 1.5GB) so 6.4GB added
  # [ "$filen" -nt "$filen.bwt" ]  && echo "$filen: Creating BWA Indices: 45 min, 5.5 GB" && bwa index "$filen"
  # Todo add parameter to optionally turn on BWA index capability

  # ---------------------------------------------------------------------------------------------------------------
  # Create special WGS Extract catalog entry from the DICT file; processing a directory cleared all .wgse files first
  [ "$filen" -nt "$filed.wgse"       ] &&
    echo "$fbnn: Creating WGS Extract Catalog Info" && {

    # ISSUE: How to best sort DICT file to get matching build ID's on primary chromosomes?  We sort on SN now.
    #   But different naming has different order and so different md5p. Sort by LN and get alt contigs interspersed?
    #   Cannot rely on M5 field existing. Leave as sort on SN before extracting primary chromosomes. And live with fact
    #   that different SN name models will have different md5p (chromosome only M5 signatures) due to sort order diff.
    # sort -V would be optimal when "human" viewing the result; but -V is not portable (GNU Util only)
    # sort --key=2.4brn,2 -k1.4b,1 -k3.4b,3   # to sort by descending LN first, then SN ; closest to original chr order

    # Throw out DICT first line, take only columns 2 to 4, upcase and sort. Store temporarily. This is the key file.
    tail -n +2 "$filed.dict" | cut -f2-4 | awk '{print toupper($0)}' | sort -d >"$filed.tmp"

    # DO NOT sort again below; original sort is based on the SN field. So md5f changes if you sort again
    md5b=$(cut -f1-2 <"$filed.tmp" | md5sum | cut -d' ' -f1) # MD5Sum BAM   (SN, LN)
    md5c=$(cut -f1-3 <"$filed.tmp" | md5sum | cut -d' ' -f1) # MD5Sum CRAM  (SN, LN, MD)
    md5f=$(cut -f2-3 <"$filed.tmp" | md5sum | cut -d' ' -f1) # MD5Sum FASTA (    LN, MD)

    # Capture Primary (Chromosomes) key stats
    # <<< $var here-document with variables is not working in subsetted cygwin64 of Win10; so we use temp file instead
    # primary=$(grep -w -e "$chrs" "$filed.tmp" | grep -e "$chrsn") 	# Length is not enough; need to then filter by SN
    # Do NOT sort again; keep same order as original sort in whole DICT for md5 variables.
    grep -w -e "$chrl" "$filed.tmp" | grep -e "$chrsn" >"$filed.ptmp" # Filter by LN then SN; keeps sorted order
    # Note: above retains multiple chrM or chrY values if they exist

    # To get "normal" sorted order; pull out each chromosome in order; should we do this for the capture as well?
    # for val in "${chr[@]} ; do
    #   sn=$(grep -w -e "$val" "$filed.tmp" | grep -e "$chrsn" | head -n 1)  # Note, using original, full DICT
    #   printf "%s\n" "$sn" >> "${filed}.ptmp"
    # done

    md5s=$(cut -f1 "$filed.ptmp" | md5sum | cut -d' ' -f1)   # MD5Sum Chrs-only Names (SN) (but odd sorted order)
    md5p=$(cut -f2-3 "$filed.ptmp" | md5sum | cut -d' ' -f1) # MD5Sum Chrs-only FASTA (   LN, MD) (IMPORTANT)

    # SN Count (whole DICT), Primary SN count (just chromosomes and mito), Y chromosome count, Mitochondria count
    declare -i snct pcnt ycnt mcnt

    # Smallest Analysis model is 84 SN entries; if less than that then likely an error (24/25 is exception for T2T)
    snct=$(wc -l <"$filed.tmp") # True SN count
    ((snct < 25)) && errp=" ***WARN: Too few SN entries (<25)***" || errp=""

    pcnt=$(wc -l <"$filed.ptmp")
    ycnt=$(grep -c -w -e "${chr[23]}" "$filed.ptmp")

    if ((pcnt == 0)); then
      echo "$fbnn: ***ERROR: No Chromosomes found; unrecognized LN lengths? Build previously seen?"
      errp+=" *** ERROR:No Chromosomes ***"

    elif ((ycnt != 1)); then # First check if missing Y or more than one Y; report that as issue before checking pcnt
      # M and Y are only duplicates found so far; so give a special error if found to be Y here; M is later
      echo "$fbnn: ***ERROR: 1 expected, $ycnt found: Y chromosome entries in ref model"
      errp+=" *** ERROR:Y $ycnt!=1 ***"

    elif ((pcnt != 24)); then
      echo "$fbnn: ***ERROR: 24 expected, $pcnt found: chromosomes in primary ref model"
      errp+=" *** ERROR:P $pcnt!=24 ***"

    fi

    # DEBUG
    # echo "Primary Chromosomes: $pcnt"
    # cat "$filed.ptmp"

    # ---------------------------------------------------------------------------------------------------------------
    # Capture the MT line to get SN name, LN, and M5 hash -- not directly captured in primary above
    # <<< here-document no longer works in subsetted cygwin64 bootstrap release here; so change to temp file
    # Models are rCRS, Yoruba, and individual T2T / HPP entries for samples (CHM13, hg01243, etc)
    grep -w -e "LN:16569\|LN:16571\|LN:16568" "$filed.tmp" >"$filed.mtmp" # Keep all columns for detail
    mcnt=$(wc -l <"$filed.mtmp")         # Keep redirection; if use filename as parameter; wc prints file name also.
    if ((mcnt != 1)); then
      echo "$fbnn: ***ERROR: 1 expected, $mcnt found: mitrochondrial entries in ref model"
      errp+=" *** ERROR:M $mcnt!=1 ***"

    fi

    if ((mcnt > 1)); then
      head -n 1 "$filed.mtmp" >"temp.mtmp" && mvx "temp.mtmp" "$filed.mtmp"   # Truncate to first line to simplify later

    fi

    msn=$(cut -f1 "$filed.mtmp")
    chrMSN="${msn:3}" # Pull out SN of Mito

    # Setup trailing ID based on Sequence Naming convention using Mito entry as primary identifier
    #  (could use md5sum of SN from primary chromosomes also to be more precise)
    case $chrMSN in
      CHRM)        msn="h" ;;   # UCSC chrN with single numeric / alphabetic naming
      CHRMT)       msn="ht"     # UCSC chrN naming with oddball chrMT
        errp+=" ***WARN: chrMT name is non-standard ***"  ;;
      MT)          msn="g" ;;   # EBI single mumeric / alphabetic naming except MT
      NC_012920.1) msn="n" ;;   # NCBI RefSeq Acquisition ID naming
      J01415.2)    msn="c" ;;   # NCBI GenBank ID naming (T2T v2)
      CP068254.1)  msn="c" ;;   # NCBI GenBank ID naming (T2T v1.x)
      CM032116.2)  msn="c" ;;   # NCBI GenBank ID naming (T2T hg01243)
      "GI|113200490|GB|J01415.2|HUMMTCG")
                   msn="c" ;;   # NCBI GenBank ID naming (T2T)
      *)                      # Check if a ref model we already know about; maybe just no MT. Otherwise, truly unknown.
        if ((pcnt > 0)); then # Model we know about; so has to be one of the three types we already checked for
          declare -i SNchrM SNMT
          SNchrM=$(grep -c -e "$chrsnhg" "$filed.tmp")
          SNMT=$(grep -c -e "$chrsneb" "$filed.tmp")
          if ((SNchrM > 0)); then
            msn="h"
          elif ((SNMT > 0)); then
            msn="g"
          else
            msn="c"
          fi

        else
          msn="x" # Unrecognized naming convention; or no MT in FASTA model file?
          unkSN=$(grep -e "SN\:" "$filed.tmp" | head -n 1)
          echo "$fbnn: ***ERROR: Unregonized Sequence Naming (${unkSN})"
          errp+=" ***ERROR: Unrecognized SN Name***"

        fi ;;
    esac

    chrMLN=$(cut -f2 "$filed.mtmp") # Used in WGSE line print out later

    # Determine mitochondria model Build variation based on mitochondrial model found
    chrMM5=$(cut -f3 "$filed.mtmp")
    case $chrMM5 in
      M5:C68F52674C9FB33AEF52DCF399755519) mbuild="37" ;; # rCRS build 37, 38, etc
      M5:D2ED829B8A1628D16CBEEE88E88E39EB) mbuild="19" ;; # Yoruba build 19, 18, etc
      M5:EC493A132AC4823AA696E37109F64972) mbuild="99" ;; # T2T model: chm13 v1.0, v1.1, v2.0 (and those that include it)
      M5:2AEA08C58600A30435E4302A82481DC0) mbuild="99" ;; # T2T model: chm13 v0.9
      M5:30F23EB261CAB50B34C0BED87EE38C7E) mbuild="99" ;; # T2T model: hg01243 v3
      *)
        mbuild="xx"               # Unrecognized model; RSRS?
        if [ -n "$chrMM5" ]; then # Only report error if set; otherwise no MT in model already reported
          echo "$fbnn: ***ERROR: Unregonized Mitochondrial Model (${chrMM5})"
          errp+=" ***ERROR: Unrecognized Mito Model***"
        fi ;;
    esac

    # ---------------------------------------------------------------------------------------------------------------
    # Based on Primary-Chromosome-only MD5sum of LN and M5 fields; determine major/minor Build type (ignoring SN names)
    # Bug introduced by adding extra sort caused fields to change mid-release,so be careful if you think below is wrong.
    # ISSUE: How to best sort primary / chromosomes to get matching build ID's?  Sort on SN before - like done now -
    #   and different naming has different order and so different md5p. Sort by LN and get alt contigs interspersed.
    #   Cannot rely on M5 field. So simply leave as sort on SN before extracting primary chrosomes. And live with fact
    #   that different SN name models will have different md5p (chromosome only M5 signatures) due to sort order diff.
    #   But maybe a sort -V -r on LN field in middle instead of SN, if can be done in BASH AND Python, would work?
    case $md5p in
      13cbd449292df5bd282ff5a21d7d0b8f) build="T2Tv20a"     ;; # T2T CHM13+HG002Y v2.0 (accession; diff sort order)
      1e34cdea361327b59b5e46aefd9c0a5e) build="HG16"        ;; # hg 16 / NCBI 34
      3566ee58361e920af956992d7f0124e6) build="HG15"        ;; # hg 15 / NCBI 33
      4136c29467b6757938849609bedd3996) build="NCB38"       ;; # NCBI 38 all patches (GENBANK, REFSEQ)
      46cf0768c13ec7862c065e45f58155bf) build="EBI18"       ;; # EBI 18
      4bdbf8a3761d0cd03b53a398b6da026d) build="HG38"        ;; # HG38 all patches
      4bf6c704e4f8dd0d31a9bf305df63ed3) build="THGv27"      ;; # T2T CHM13 v1.1 with HG002 xy v2.7
      4d0aa9b8472b69f175d279a9ba8778a1) build="HPPv11"      ;; # HPP CHM13 v1.1 with GRCh38 Y
      591bb02c89ed438566ca68b077fee367) build="1K37p"       ;; # EBI GRCh37 Errored  (extra Y) (few are EBI37)
      5a23f5a85bd78221010561466907bf7d) build="EBI37"       ;; # EBI 37
      5e16e3cbdcc7b69d21420c332deecd3b) build="T2Tv10"      ;; # T2T CHM13 v1.0 (original)
      5f451c1014248af62b41c18fec1c3660) build="T2Tv07"      ;; # T2T CHM13 v0.7 (chr X only; not a true build)
      65a05319ad475cf51c929d3b55341bc2) build="THGv20"      ;; # T2T CHM13 v1.1 with HG002 xy v2
      7083d4ee8aa126726961ab1ae41c66c1) build="THG1243v3"   ;; # T2T HG01243 (Pr1) (accession)
      7a5eb72fb45c4567431651aa6f9edfef) build="1K${mbuild}" ;; # 1K 19 / 37
      7cee777f1939f4028926017158ed5512) build="T2Tv20"      ;; # T2T v2.0 (CHM13 v1.1 w/ HG002 v2.7 Y) (chr name)
      84e78573982f3ea293bfeb54cd529309) build="1K38p"       ;; # Verily oddball GRCh38
      85c436650ffe85696c0fb51de4a3a74f) build="THG1243v3"   ;; # T2T HG01243 (aka PR1 Puerto Rican) (chr name)
      90814fe70fd8bbc59cacf2a3fd08e24c) build="T2Tv09"      ;; # T2T CHM13 v0.9
      a2fe6ab831d884104783f9be437ddbc0) build="EBI38p"      ;; # EBI GRCh38 Errored models
      a9634b94a29618dc3faf15a3060006ec) build="HG18"        ;; # hg 18 / NCBI 36
      b05113b52031beadfb6737bc1185960b) build="HG${mbuild}" ;; # HG 19 / NCBI 37
      b7884451f3069579e5f2e885582b9434) build="1K38"        ;; # 1K 38
      bbd2cf1448ccc0eaa2472408fa9d514a) build="THGySeqp"    ;; # ySeq HG38 w/ HG002 v2 Y
      bc811d53b8a6fc404d279ab951f2be4d) build="HG17"        ;; # hg 17 / NCBI 35
      bee8aebc6243ff5963c30abbd738d1f6) build="NCB38"       ;; # NCBI 38 Genbank (orig top_level)
      c182b40ef3513ef9a1196881a4315392) build="HPPv1"       ;; # HPP CHM13 v1 with GRCh38 Y
      ca2e97bc5ecff43a27420eee237dbcc3) build="EBI37p"      ;; # EBI GRCh37 Errored models (extra Y)
      e9438f38ad1b9566c15c3c64a9419d9d) build="T2Tv11"      ;; # T2T CHM13 v1.1 (original)
      eec5eb2eeae44c48a31eb32647cd04f6) build="EBI38"       ;; # EBI 38
      f7c76dbcf8cf8b41d2c1d05c1ed58a75) build="NCB37"       ;; # NCBI GRCh37 (RefSeq)
      d41d8cd98f00b204e9800998ecf8427e) build="UNK"            # d41d8... is what shows when an empty file
        echo "$fbnn: ***ERROR: Unknown Build (0 chromosomes)"  ;;
      *)                                build="UNK"
        echo "$fbnn: ***ERROR: Build Not Seen Before (${md5p})"
        errp+=" ***ERROR: Unrecognized Build Model***"  ;;
    esac
    build="${build}${msn}" # Append sequence naming convention used

    chrSN=""
    for val in "${chr[@]}"; do
      # shellcheck disable=SC2034
      sn=$(grep -w -e "$val" "$filed.ptmp" | head -n 1 | cut -f1) # Extract SN for LN of chromosome in ptmp file
      chrSN+="\t\"${sn:3}\""                                      # TSV format
    done
    chrSN+="\t\"${chrMSN}\""
    chrSNt=$(printf "%b" "${chrSN:2}") # Ugly. printf to get \t's converted; :2 to remove leading \t

    # Save all the values as single line, tab separated text file; append to project file for directory
    #  Note: chrM is already a 3 value, tab separated variable that we simply use to create 3 columns
    printf $'\"%s\"\t%s\t%u\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t\"%s\"\t%s\n' \
      "$filen" $build "$snct" "$md5b" "$md5c" "$md5f" "$md5p" "$md5s" \
      "$chrMSN" "$chrMLN" "$chrMM5" "$errp" "$chrSNt" >"$filed.wgse"

    # Final error check -- in case previous uncaught error left intermediate .wgse file or multi-line stats (mtDNA)
    wcnt=$(wc -l <"$filed.wgse")
    if ((wcnt != 1)); then
      echo "$fbnn: ***ERROR: Failed generating final WGSE stats file"
      rmx "$filed.wgse"

    else
      cat "$filed.wgse" >>"${sumFPB}.csv"

    fi

    rmx "$filed.tmp" "$filed.mtmp" "$filed.ptmp" # **** ERROR: environment: _perform_rmx: command not found
  }
done

# Some basic stats for the Reference Genome study document when run on a directory with all known models (assume GNU utils)
if "$wholedir"; then
  tail -n +2 "${sumFPB}.csv" > temp.csv     # Create Headless CSV file (strip first line of labels)
  echo "Entries: $(wc -l "temp.csv")" | sed "s/temp/${sumFPB}/"    # Use original file name; not headless temp one
  cut -f2     "temp.csv" | sort -V | uniq -c | awk '{gsub(/^ +/,"") gsub(/ /,"\t")} {print $0}' > "${sumFPB}_uniq_build.csv"
  echo "Entries: $(wc -l "${sumFPB}_uniq_build.csv")"
  cut -f8,13- "temp.csv" | sort --key=3,3 | uniq -c | awk '{gsub(/^ +/,"") gsub(/ /,"\t")} {print $0}' > "${sumFPB}_uniq_ChrSN.csv"
  echo "Entries: $(wc -l "${sumFPB}_uniq_ChrSN.csv")"
  cut -f7     "temp.csv" | sort | uniq -c | awk '{gsub(/^ +/,"") gsub(/ /,"\t")} {print $0}' > "${sumFPB}_uniq_ChrLNM5.csv"
  echo "Entries: $(wc -l "${sumFPB}_uniq_ChrLNM5.csv")"
  cut -f3     "temp.csv" | sort -n | uniq -c | awk '{gsub(/^ +/,"") gsub(/ /,"\t")} {print $0}' > "${sumFPB}_uniq_SNcnt.csv"
  echo "Entries: $(wc -l "${sumFPB}_uniq_SNcnt.csv")"
  rmx temp.csv
  # For convenience, create a table of all Sequence entries in all FASTA's in the specified directory
  grep -v "^@HD" "$1"/*dict | cut -f2- | sort --key=2.4brn,2 -k3.4b,3 -k1.4b,1 > "${sumFPB}_dict.csv"
  echo "Entries: $(wc -l "${sumFPB}_dict.csv")"
  cut -f1-3 "${sumFPB}_dict.csv" | sort -V | uniq -c | awk '{gsub(/^ +/,"") gsub(/ /,"\t")} {print $0}' > "${sumFPB}_dict_uniq_SNLNM5.csv"
  echo "Entries: $(wc -l "${sumFPB}_dict_uniq_SNLNM5.csv")"
  cut -f2-3 "${sumFPB}_dict.csv" | sort -rV | uniq -c | awk '{gsub(/^ +/,"") gsub(/ /,"\t")} {print $0}' > "${sumFPB}_dict_uniq_LNM5.csv"
  echo "Entries: $(wc -l "${sumFPB}_dict_uniq_LNM5.csv")"
fi
