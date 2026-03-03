#!/bin/bash
# Verify that all required bioinformatics tools are installed and functional

set -e

echo "Verifying tool installations..."

tools=(
    "samtools"
    "bcftools"
    "bwa"
    "minimap2"
    "fastp"
    "fastqc"
    "delly"
    "freebayes"
)

for tool in "${tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✅ $tool is installed."
        # Attempt to run --version or help if available, but don't fail if they don't support it
        if [[ "$tool" == "bwa" ]]; then
            $tool 2>&1 | head -n 3
        else
            $tool --version 2>&1 | head -n 1 || $tool --help 2>&1 | head -n 1 || echo "($tool version check skipped)"
        fi
    else
        echo "❌ $tool is NOT installed."
        exit 1
    fi
done

# VEP check (optional but recommended)
if command -v vep >/dev/null 2>&1; then
    echo "✅ vep is installed."
    vep --help 2>&1 | head -n 1
else
    echo "⚠️ vep is NOT installed (optional on some platforms)."
fi

echo "All mandatory tools verified successfully."
