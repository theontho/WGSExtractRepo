import logging
import os
import shutil
import subprocess
import sys
from typing import Any

# Define mandatory and optional tools
MANDATORY_TOOLS = [
    "samtools",
    "bcftools",
    "tabix",
    "bgzip",
    "bwa",
    "python3",
    "gzip",
    "tar",
]

OPTIONAL_TOOLS = [
    "minimap2",
    "fastp",
    "fastqc",
    "delly",
    "freebayes",
    "vep",
    "gatk",
    "run_deepvariant",
    "dv_call_variants.py",
    "curl",
    "wget",
    "java",
    "yleaf",
    "haplogrep",
    "htsfile",
]


def get_repo_root():
    """
    Attempts to find the repository root by looking for common markers.
    Defaults to 4 levels up from this file if no markers are found.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Check for pyproject.toml or .git in parents
    probe = current_dir
    while probe != os.path.dirname(probe):  # stop at filesystem root
        if os.path.exists(os.path.join(probe, "pyproject.toml")) or os.path.exists(
            os.path.join(probe, ".git")
        ):
            # If we found it in 'cli/', the real repo root is one level up
            if os.path.basename(probe) == "cli":
                return os.path.dirname(probe)
            return probe
        probe = os.path.dirname(probe)

    # Fallback to hardcoded relative path if markers not found
    return os.path.abspath(os.path.join(current_dir, "../../../.."))


def get_jar_dir():
    """Returns the directory where JAR tools are expected to live."""
    # Allow override via environment variable
    env_path = os.environ.get("WGSE_JAR_DIR")
    if env_path and os.path.isdir(env_path):
        return env_path

    return os.path.join(get_repo_root(), "jartools")


def check_dependencies(tool_list, jar_dir=None):
    """
    Checks if all required tools or JAR files are available in the PATH.
    Returns a list of missing tools.
    """
    missing = []
    if jar_dir is None:
        jar_dir = get_jar_dir()

    for tool in tool_list:
        if tool.endswith(".jar"):
            if not os.path.exists(os.path.join(jar_dir, tool)):
                missing.append(f"{tool} (in {jar_dir})")
        else:
            if shutil.which(tool) is None:
                missing.append(tool)
    return missing


def verify_dependencies(tool_list, optional_list=None):
    """
    Checks if all required tools or JAR files are available.
    Exits gracefully if a tool is missing or version is too old.
    """
    if optional_list is None:
        optional_list = OPTIONAL_TOOLS

    missing = check_dependencies(tool_list)

    if missing:
        is_optional = all(tool in optional_list for tool in missing)
        if is_optional:
            logging.error("Required optional tool(s) missing for this feature:")
        else:
            logging.error("Fatal Error: Missing required core tools or JAR files.")

        for t in missing:
            logging.error(f" - {t}")

        if is_optional:
            logging.info(
                "\nPlease install the missing tools using your system package manager "
                "(e.g., brew, apt, conda) or follow the project installation guide."
            )
        else:
            logging.error(
                "\nPlease ensure all mandatory tools are installed and in your PATH."
            )

        sys.exit(1)

    # Version Validation for critical tools
    for tool in ["bcftools", "samtools"]:
        if tool in tool_list:
            version_str = get_tool_version(tool)
            # Handle version strings like "bcftools 1.12" or "Version: 0.1.19"
            import re

            match = re.search(r"(\d+)\.(\d+)", version_str)
            if match:
                major = int(match.group(1))
                if major < 1:
                    logging.error(
                        f"Fatal Error: {tool} version {version_str} is too old."
                    )
                    logging.error(f"This tool requires {tool} version 1.0 or newer.")
                    logging.info(
                        f"\nYour current path for {tool} is: {shutil.which(tool)}"
                    )
                    logging.info("Please update your conda environment or system path.")
                    sys.exit(1)


def get_jar_path(jar_name):
    """Returns absolute path to a JAR file in jartools/."""
    path = os.path.join(get_jar_dir(), jar_name)
    if os.path.exists(path):
        return path
    return None


def get_tool_version(tool):
    """Attempt to get the version of a tool by running it."""
    try:
        # 1. Try --version first (standard)
        res = subprocess.run(
            [tool, "--version"], capture_output=True, text=True, timeout=5
        )
        output = (res.stdout or res.stderr).strip()

        if res.returncode == 0 and output and not output.startswith("[main]"):
            lines = [
                line.strip()
                for line in output.splitlines()
                if line.strip() and not line.startswith("DEBUG:")
            ]
            if lines:
                return lines[0]

        # 2. Fallback for tools that use bare command or --help
        res = subprocess.run([tool], capture_output=True, text=True, timeout=5)
        output = (res.stdout or res.stderr).strip()

        # Check for dyld/library errors
        failure_keywords = [
            "Library not loaded",
            "not found",
            "illegal instruction",
            "segmentation fault",
            "bad interpreter",
        ]
        if any(kw.lower() in output.lower() for kw in failure_keywords):
            if "not found" in output.lower() and tool.lower() not in output.lower():
                pass
            else:
                return f"Error: {output.splitlines()[0]}"

        # Search for "Version:" or similar in the output
        for line in output.splitlines():
            line_l = line.lower()
            if "version:" in line_l:
                return line.strip()
            if tool.lower() in line_l and any(c.isdigit() for c in line):
                if len(line.strip()) < 50:
                    return line.strip()

        # Generalized fallback for tools like VEP or others with multi-line help
        if not output:
            return "Available"

        # Check first 5 lines for anything that looks like a version string
        for line in output.splitlines()[:5]:
            if any(word in line.lower() for word in ["version", "release", "v[0-9]"]):
                if len(line.strip()) < 60:
                    return line.strip()

        return "Available"
    except Exception as e:
        return f"Error: {str(e)}"


def get_tool_path(tool):
    """Returns the path to a tool if it exists in the system PATH."""
    return shutil.which(tool)


def check_all_dependencies(mandatory=None, optional=None):
    """
    Performs a simple dependency check and returns results.
    """
    if mandatory is None:
        mandatory = MANDATORY_TOOLS
    if optional is None:
        optional = OPTIONAL_TOOLS

    results: dict[str, list[dict[str, Any]]] = {"mandatory": [], "optional": []}

    # Python Version Check
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    results["mandatory"].append(
        {
            "name": "Python Runtime",
            "path": sys.executable,
            "version": f"Python {py_version} (Required >= 3.11)",
        }
    )

    for tool in mandatory:
        if tool == "python3":
            continue  # Already checked above as Runtime
        path = shutil.which(tool)
        version = get_tool_version(tool) if path else None
        is_broken = version and version.startswith("Error:")

        results["mandatory"].append(
            {
                "name": tool,
                "path": path if not is_broken else None,
                "version": version,
            }
        )

    for tool in optional:
        path = shutil.which(tool)
        version = get_tool_version(tool) if path else None

        display_name = tool
        if tool == "run_deepvariant":
            display_name = f"{tool} (Wrapper)"
        elif tool == "dv_call_variants.py":
            display_name = f"{tool} (Bioconda)"

        is_broken = version and version.startswith("Error:")

        results["optional"].append(
            {
                "name": display_name,
                "path": path if not is_broken else None,
                "version": version,
            }
        )

    return results


def log_dependency_info(tool_list):
    """Logs the path and version for a list of tools for diagnostic purposes."""
    for tool in tool_list:
        path = shutil.which(tool)
        if path:
            version = get_tool_version(tool)
            logging.debug(f"Dependency: {tool} -> {path} ({version})")
        else:
            logging.debug(f"Dependency: {tool} -> NOT FOUND")
