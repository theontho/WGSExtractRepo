#!/bin/bash

# common.sh: Shared functions for WGS Extract CLI smoke tests

# Load environment variables for data paths
if [ -f .env.local ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' .env.local | xargs)
fi

# Add common paths for bioinformatics tools
NEW_PATH="/opt/homebrew/bin:/usr/local/bin:/opt/homebrew/Caskroom/miniconda/base/bin:/opt/homebrew/Caskroom/miniconda/base/envs/wgse/bin:/opt/homebrew/Caskroom/miniconda/base/envs/yleaf_env/bin:$PATH"
export PATH="$NEW_PATH"

# Function to check for required tools and exit with 77 (SKIP) if any are missing
check_deps() {
    local missing=()
    for tool in "$@"; do
        if ! command -v "$tool" &> /dev/null; then
            missing+=("$tool")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo "⏭️  SKIP: Missing required tools: ${missing[*]}"
        exit 77
    fi
}

# Function to check for mandatory tools (samtools, bcftools, tabix, bgzip, bwa)
check_mandatory_deps() {
    check_deps samtools bcftools tabix bgzip bwa
}
