import logging
import os
import shutil
import sys


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
