import os
import sys
import time
import subprocess
import signal

def test_parent_pid_cleanup():
    """
    Test that the CLI exits when the parent process dies.
    """
    print("Starting process cleanup test...")
    
    # 1. Start a dummy "parent" process that will sleep for a bit then exit
    # We use a python one-liner for a simple steady process
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
    parent_pid = parent.pid
    print(f"Dummy parent PID: {parent_pid}")
    
    # 2. Start the wgsextract CLI with --parent-pid pointing to our dummy parent
    # We use 'align' which will wait for input if no args provided
    cli_cmd = [
        sys.executable, "-m", "wgsextract_cli.main", 
        "align", "--parent-pid", str(parent_pid)
    ]
    
    # Set PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    env["WGSE_SKIP_DOTENV"] = "1"
    
    cli_proc = subprocess.Popen(
        cli_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    print(f"CLI process PID: {cli_proc.pid}")
    
    # Give it a moment to start the monitoring thread
    time.sleep(2)
    
    # Check if CLI is still running (it should be, parent is alive)
    if cli_proc.poll() is not None:
        print("FAIL: CLI process exited prematurely")
        parent.terminate()
        return False
    
    print("CLI is running as expected. Killing parent...")
    
    # 3. Kill the dummy parent
    parent.terminate()
    parent.wait()
    print("Parent killed.")
    
    # 4. Wait for the CLI to notice and exit (it checks every 2 seconds)
    print("Waiting for CLI to detect parent death...")
    start_wait = time.time()
    while time.time() - start_wait < 10:
        if cli_proc.poll() is not None:
            print(f"SUCCESS: CLI process exited after parent death with code {cli_proc.returncode}")
            return True
        time.sleep(0.5)
    
    print("FAIL: CLI process stayed alive longer than 10 seconds after parent death")
    cli_proc.terminate()
    return False

if __name__ == "__main__":
    if test_parent_pid_cleanup():
        print("\nTEST PASSED")
        sys.exit(0)
    else:
        print("\nTEST FAILED")
        sys.exit(1)
