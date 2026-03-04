#!/bin/bash
# Verify that all required bioinformatics tools are installed and functional

set -e

echo "Verifying mandatory tool installations..."

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

# Optional but supported tools
optional_tools=(
    "vep"
    "gatk"
    "run_deepvariant"
    "dv_call_variants.py"
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

echo "Verifying optional tools..."
for tool in "${optional_tools[@]}"; do
    FOUND=false
    # Check current shell, wgse env, or vep_env
    if command -v "$tool" >/dev/null 2>&1; then 
        FOUND=true
        CMD="$tool"
    elif conda run -n wgse command -v "$tool" >/dev/null 2>&1; then 
        FOUND=true
        CMD="conda run -n wgse $tool"
    elif conda run -n vep_env command -v "$tool" >/dev/null 2>&1; then 
        FOUND=true
        CMD="conda run -n vep_env $tool"
    fi

    if [ "$FOUND" = true ]; then
        echo "✅ $tool is installed."
        # Use a subshell to avoid exit on help/version failure
        ($CMD --help 2>&1 | head -n 1) || echo "($tool available)"
    else
        echo "⚠️ $tool is NOT installed (optional)."
    fi
done

echo "All mandatory tools verified successfully."
