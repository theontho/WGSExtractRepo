import shutil
import sys
import logging

def verify_dependencies(tool_list):
    """
    Checks if all required tools are available in the system $PATH.
    Exits gracefully if a tool is missing.
    """
    missing_tools = []
    for tool in tool_list:
        if shutil.which(tool) is None:
            missing_tools.append(tool)
            
    if missing_tools:
        logging.error("Fatal Error: Missing required tools in $PATH.")
        for t in missing_tools:
            logging.error(f" - {t}")
        sys.exit(1)
