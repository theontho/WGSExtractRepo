import logging
import os
import shutil
import subprocess
import sys
from typing import Any

# Define mandatory and optional tools based on verify_tools.sh
MANDATORY_TOOLS = [
    "samtools",
    "bcftools",
    "tabix",
    "bgzip",
    "bwa",
    "minimap2",
    "fastp",
    "fastqc",
    "delly",
    "freebayes",
]

OPTIONAL_TOOLS = [
    "vep",
    "gatk",
    "run_deepvariant",
    "dv_call_variants.py",
    "curl",
]

# Conda environments to check if a tool is not in the primary PATH
CONDA_ENVS = ["wgse", "vep_env"]


def check_dependencies(tool_list):
    """
    Checks if all required tools or JAR files are available.
    Returns a list of missing tools.
    """
    missing = []

    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
    jar_dir = os.path.join(repo_root, "jartools")

    for tool in tool_list:
        if tool.endswith(".jar"):
            if not os.path.exists(os.path.join(jar_dir, tool)):
                missing.append(f"{tool} (in {jar_dir})")
        else:
            if shutil.which(tool) is None:
                # Check conda environments
                found_in_conda = False
                for env in CONDA_ENVS:
                    if (
                        subprocess.run(
                            ["conda", "run", "-n", env, "command", "-v", tool],
                            capture_output=True,
                        ).returncode
                        == 0
                    ):
                        found_in_conda = True
                        break
                if not found_in_conda:
                    missing.append(tool)
    return missing


def verify_dependencies(tool_list):
    """
    Checks if all required tools or JAR files are available.
    Exits gracefully if a tool is missing.
    """
    missing = check_dependencies(tool_list)

    if missing:
        logging.error("Fatal Error: Missing required tools or JAR files.")
        for t in missing:
            logging.error(f" - {t}")
        sys.exit(1)


def get_jar_path(jar_name):
    """Returns absolute path to a JAR file in jartools/."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
    path = os.path.join(repo_root, "jartools", jar_name)
    if os.path.exists(path):
        return path
    return None


def get_tool_version(tool, conda_env=None):
    """Attempt to get the version of a tool."""
    base_cmd = [tool]
    if conda_env:
        base_cmd = ["conda", "run", "-n", conda_env, tool]

    try:
        # 1. Try --version first (standard)
        res = subprocess.run(
            base_cmd + ["--version"], capture_output=True, text=True, timeout=5
        )
        output = (res.stdout or res.stderr).strip()

        if res.returncode == 0 and output and not output.startswith("[main]"):
            # Success, parse output
            lines = [
                line.strip()
                for line in output.splitlines()
                if line.strip() and not line.startswith("DEBUG:")
            ]
            if lines:
                return lines[0]

        # 2. Fallback for older tools (samtools 0.1.x, bwa, etc.) that use bare command or --help
        # and for tools like VEP that don't support --version
        res = subprocess.run(base_cmd, capture_output=True, text=True, timeout=5)
        output = (res.stdout or res.stderr).strip()

        # Check for dyld/library errors first in the fallback output too
        failure_keywords = [
            "Library not loaded",
            "not found",
            "illegal instruction",
            "segmentation fault",
            "bad interpreter",
        ]
        if any(kw.lower() in output.lower() for kw in failure_keywords):
            # Only return error if it's a real system error, not just "command not found"
            # (which shouldn't happen here as we check which/conda run first)
            if "not found" in output.lower() and tool.lower() not in output.lower():
                pass  # might be a tool message
            else:
                return f"Error: {output.splitlines()[0]}"

        # Search for "Version:" or similar in the output
        for line in output.splitlines():
            line_l = line.lower()
            if "version:" in line_l:
                return line.strip()
            if tool.lower() in line_l and any(c.isdigit() for c in line):
                # e.g. "samtools 1.23" or "bcftools 1.23"
                if len(line.strip()) < 50:  # Avoid long descriptive lines
                    return line.strip()

        # Specific fallback for VEP
        if tool == "vep":
            for line in output.splitlines():
                if "ensembl-vep" in line.lower():
                    return line.strip()
            # If we don't find ensembl-vep line, look for the first line with a colon after "Versions:"
            found_versions = False
            for line in output.splitlines():
                if "versions:" in line.lower():
                    found_versions = True
                    continue
                if found_versions and ":" in line:
                    return line.strip()

        return "Available"
    except Exception as e:
        return f"Error: {str(e)}"


def check_all_dependencies():
    """
    Performs a comprehensive dependency check and returns results.
    """
    results: dict[str, list[dict[str, Any]]] = {"mandatory": [], "optional": []}

    for tool in MANDATORY_TOOLS:
        path = shutil.which(tool)
        version = None
        env_found = None

        if path:
            version = get_tool_version(tool)
        else:
            # Check conda environments
            for env in CONDA_ENVS:
                check = subprocess.run(
                    ["conda", "run", "-n", env, "which", tool], capture_output=True
                )
                if check.returncode == 0:
                    path = check.stdout.decode().strip()
                    env_found = env
                    version = get_tool_version(tool, conda_env=env)
                    break

        # Consider it broken/missing if there's an execution error
        is_broken = version and version.startswith("Error:")

        results["mandatory"].append(
            {
                "name": tool,
                "path": path if not is_broken else None,
                "version": f"{version} [conda:{env_found}]"
                if env_found and version
                else version,
            }
        )

    for tool in OPTIONAL_TOOLS:
        path = shutil.which(tool)
        version = None
        env_found = None

        display_name = tool
        if tool == "run_deepvariant":
            display_name = f"{tool} (Wrapper)"
        elif tool == "dv_call_variants.py":
            display_name = f"{tool} (Bioconda)"

        if path:
            version = get_tool_version(tool)
        else:
            # Check conda environments
            for env in CONDA_ENVS:
                check = subprocess.run(
                    ["conda", "run", "-n", env, "which", tool], capture_output=True
                )
                if check.returncode == 0:
                    path = check.stdout.decode().strip()
                    env_found = env
                    version = get_tool_version(tool, conda_env=env)
                    break

        is_broken = version and version.startswith("Error:")

        results["optional"].append(
            {
                "name": display_name,
                "path": path if not is_broken else None,
                "version": f"{version} [conda:{env_found}]"
                if env_found and version
                else version,
            }
        )

    return results
