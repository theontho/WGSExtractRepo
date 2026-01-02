import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class Logger:
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str, to_stdout: bool = True, to_file: bool = True):
        """Logs a message to stdout and/or a file."""
        if to_stdout:
            print(message)
            sys.stdout.flush()
        
        if to_file and self.log_path:
            try:
                with open(self.log_path, 'a') as f:
                    f.write(message + '\n')
            except OSError:
                pass

    def echo_tee(self, message: str):
        """Equivalent to echo_tee in shell scripts."""
        self.log(message)

    def echo_log(self, message: str):
        """Only logs to file."""
        self.log(message, to_stdout=False)

    def error(self, message: str):
        """Logs an error message to both."""
        full_mesg = f"*** ERROR: {message}"
        self.log(full_mesg)

def get_timestamp() -> str:
    """Returns a timestamp string for log filenames."""
    return datetime.now().strftime("%d%m%y_%H%M%S")

# Global logger instance
logger = Logger()

def set_global_log_file(path: Path):
    global logger
    logger.log_path = path

def echo_tee(message: str):
    logger.echo_tee(message)

def echo_log(message: str):
    logger.echo_log(message)

def askyesno(prompt: str) -> bool:
    """Prompts the user with a yes/no question."""
    while True:
        choice = input(f"{prompt} [y/N]? ").lower()
        if choice in ['y', 'yes']:
            return True
        if choice in ['n', 'no', '']:
            return False
        print("Please enter 'y' or 'n'.")
