#!/bin/bash

# Configuration
FAKE_DIR="out/fake_30x"
MAP_FILE="$FAKE_DIR/fake.map"
MODEL_DIR="reference/models/deepvariant/WGS"
DV_VERSION="1.10.0"

# Add common miniconda and homebrew paths to PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:$PATH"

echo ":: Setting up VCF resources..."

# 1. Generate Mappability Map for Fake Reference
if [ ! -f "$MAP_FILE" ]; then
    echo ":: Generating dummy mappability map for fake reference..."
    FAI="$FAKE_DIR/fake_ref.fa.fai"
    if [ ! -f "$FAI" ]; then
        echo ":: Indexing fake reference..."
        samtools faidx "$FAKE_DIR/fake_ref.fa"
    fi

    TMP_MAP="$FAKE_DIR/fake.map"
    rm -f "$TMP_MAP"

    while read -r chrom length rest; do
        for ((pos=1; pos<=length; pos+=100)); do
            echo -e "$chrom\t$pos\t1.0" >> "$TMP_MAP"
        done
        echo -e "$chrom\t$length\t1.0" >> "$TMP_MAP"
    done < "$FAI"
    echo "✅ Generated: $MAP_FILE"
fi

# 2. Download DeepVariant Model using gsutil
if [ ! -f "$MODEL_DIR/deepvariant.wgs.ckpt.index" ]; then
    echo ":: Downloading DeepVariant $DV_VERSION WGS model using gsutil..."
    mkdir -p "$MODEL_DIR"

    GS_URL="gs://deepvariant/models/DeepVariant/1.10.0/checkpoints/wgs"

    gsutil cp "$GS_URL/deepvariant.wgs.ckpt.data-00000-of-00001" "$MODEL_DIR/"
    gsutil cp "$GS_URL/deepvariant.wgs.ckpt.index" "$MODEL_DIR/"

    if [ -f "$MODEL_DIR/deepvariant.wgs.ckpt.index" ] && [ -s "$MODEL_DIR/deepvariant.wgs.ckpt.index" ]; then
        echo "✅ Downloaded DeepVariant models to $MODEL_DIR"
    else
        echo "❌ Failed to download DeepVariant models using gsutil."
    fi
else
    echo "✅ DeepVariant models already present in $MODEL_DIR"
fi

echo ":: Resource setup complete."
