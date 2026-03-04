#!/bin/bash
# Verify that bioinformatics tools have been successfully uninstalled

echo "Verifying uninstallation..."

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
    "vep"
)

found_tools=()

for tool in "${tools[@]}"; do
    if command -v "$tool" >/dev/null 2>&1; then
        # On CI, python3 and openjdk are often pre-installed.
        # We only fail if the specific bioinformatics tools are still present.
        if [[ "$tool" != "python3" && "$tool" != "java" && "$tool" != "openjdk" ]]; then
            echo "❌ $tool is still present at $(command -v $tool)"
            found_tools+=("$tool")
        else
            echo "⚠️ $tool is still present, but it might be a system default."
        fi
    else
        echo "✅ $tool is successfully uninstalled."
    fi
done

if [ ${#found_tools[@]} -ne 0 ]; then
    echo "Uninstallation verification FAILED for: ${found_tools[*]}"
    exit 1
fi

echo "Uninstallation verified successfully."
