#!/bin/bash
# Verify that all required bioinformatics tools are installed and functional

set -e

echo "Verifying tool installations..."

tools=(
    "samtools"
    "bcftools"
    "tabix"
    "bwa"
    "minimap2"
    "fastp"
    "fastqc"
    "delly"
    "freebayes"
)

for tool in "${tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1 || conda run -n wgse command -v "$tool" >/dev/null 2>&1; then
        echo "✅ $tool is installed."
        # Attempt to run --version or help if available
        if [[ "$tool" == "bwa" ]]; then
            $tool 2>&1 | head -n 3
        elif command -v "$tool" >/dev/null 2>&1; then
            $tool --version 2>&1 | head -n 1 || $tool --help 2>&1 | head -n 1 || echo "($tool version check skipped)"
        else
            conda run -n wgse "$tool" --version 2>&1 | head -n 1 || echo "($tool version check skipped)"
        fi
    else
        echo "❌ $tool is NOT installed."
        exit 1
    fi
done

# VEP check (optional but recommended)
if command -v vep >/dev/null 2>&1 || conda run -n vep_env command -v vep >/dev/null 2>&1 || conda run -n wgse command -v vep >/dev/null 2>&1; then
    echo "✅ vep is installed."
    if command -v vep >/dev/null 2>&1; then
        vep --help 2>&1 | head -n 1
    elif conda run -n vep_env command -v vep &>/dev/null; then
        conda run -n vep_env vep --help 2>&1 | head -n 1
    else
        conda run -n wgse vep --help 2>&1 | head -n 1
    fi
else
    echo "⚠️ vep is NOT installed (optional on some platforms)."
fi

echo "All mandatory tools verified successfully."
