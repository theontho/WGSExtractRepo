import shutil
import sys
import logging
import os

def verify_dependencies(tool_list):
    """
    Checks if all required tools or JAR files are available.
    Exits gracefully if a tool is missing.
    """
    missing = []
    
    # Base directory for JAR tools (assume relative to cli/ root or repo root)
    # The cli/tests/e2e_base.py sets up sys.path.
    # From cli/src/wgsextract_cli/core/dependencies.py, repo root is 4 levels up.
    # But often it's easier to check from the current script's location.
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(current_dir, "../../../.."))
    jar_dir = os.path.join(repo_root, "jartools")

    for tool in tool_list:
        if tool.endswith(".jar"):
            if not os.path.exists(os.path.join(jar_dir, tool)):
                missing.append(f"{tool} (in {jar_dir})")
        else:
            if shutil.which(tool) is None:
                missing.append(tool)
            
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
