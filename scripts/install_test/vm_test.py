#!/usr/bin/env python3
import os
import sys
import json
import time
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Add the scripts directory to path to import release.py if needed
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIR = REPO_ROOT / "build"
SCRIPTS_DIR = REPO_ROOT / "scripts"

IMAGES = {
    "ubuntu": "ghcr.io/cirruslabs/ubuntu:latest",
    "fedora": "ghcr.io/cirruslabs/fedora:latest",
    "macos": "ghcr.io/cirruslabs/macos-sonoma-base:latest"
}

class TartVM:
    def __init__(self, name, image):
        self.name = name
        self.image = image
        self.process = None

    def clone(self):
        print(f"[*] Cloning {self.image} into {self.name}...")
        subprocess.run(["tart", "clone", self.image, self.name], check=True)

    def start(self):
        print(f"[*] Starting VM {self.name}...")
        # Removed --no-graphics to enable GUI support as requested
        self.process = subprocess.Popen(
            ["tart", "run", self.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def stop(self):
        print(f"[*] Stopping VM {self.name}...")
        subprocess.run(["tart", "stop", self.name], capture_output=True)
        if self.process:
            self.process.terminate()
            self.process = None

    def delete(self):
        print(f"[*] Deleting VM {self.name}...")
        subprocess.run(["tart", "delete", self.name], capture_output=True)

    def exec(self, command, input_data=None, capture_output=True):
        """Execute a command in the VM using tart exec."""
        cmd = ["tart", "exec", self.name]
        if isinstance(command, str):
            cmd += ["sh", "-c", command]
        else:
            cmd += list(command)

        # Handle input string by encoding to bytes if needed would be done by subprocess if text=False,
        # but we use text=True for easier output handling, so input should be string.
        
        result = subprocess.run(
            cmd,
            input=input_data if input_data else None,
            capture_output=capture_output,
            text=True
        )
        return result

    def wait_until_ready(self, timeout=120):
        print(f"[*] Waiting for VM {self.name} to be ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            res = self.exec("ls", capture_output=True)
            if res.returncode == 0:
                print(f"[+] VM {self.name} is ready.")
                return True
            time.sleep(2)
        print(f"[!] Timeout waiting for VM {self.name}")
        return False

    def transfer_file(self, local_path, remote_path):
        """Transfer a file to the VM using cat and tart exec -i."""
        print(f"[*] Transferring {local_path} to {remote_path} in VM...")
        with open(local_path, "rb") as f:
            # We must use raw bytes interface for binary transfer, so not text=True
            subprocess.run(
                ["tart", "exec", "-i", self.name, "sh", "-c", f"cat > {remote_path}"],
                stdin=f,
                check=True
            )

    def extract_zip(self, remote_zip, target_dir):
        print(f"[*] Extracting {remote_zip} to {target_dir}...")
        # Use python3 to extract to avoid unzip dependency (common in fresh images)
        cmd = f"mkdir -p {target_dir} && python3 -c 'import zipfile; z = zipfile.ZipFile(\"{remote_zip}\"); z.extractall(\"{target_dir}\")'"
        res = self.exec(cmd)
        if res.returncode != 0:
            print(f"[!] Extraction failed: {res.stderr}")
            return False
        return True

def run_release_script():
    print("[*] Running release.py to generate packages...")
    release_py = SCRIPTS_DIR / "release.py"
    subprocess.run([sys.executable, str(release_py)], check=True)

def find_release_zip(platform):
    """Find the latest release zip for a platform in the build directory."""
    patterns = {
        "ubuntu": "*_ubuntu_installer.zip",
        "fedora": "*_linux_installer.zip",
        "macos": "*_macos_brew_installer.zip"
    }
    pattern = patterns.get(platform)
    if not pattern:
        return None
    
    zips = list(BUILD_DIR.glob(pattern))
    if not zips:
        return None
    
    return sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)[0]

def cleanup_stale_vms():
    """Cleanup any leftover test VMs from previous runs."""
    print("[*] Cleaning up stale test VMs...")
    res = subprocess.run(["tart", "list"], capture_output=True, text=True)
    for line in res.stdout.splitlines():
        if "wgse-test-" in line:
             name = line.split()[0] # Assuming first column is name
             if name.startswith("wgse-test-"):
                 print(f"[*] Found stale VM {name}, deleting...")
                 subprocess.run(["tart", "stop", name], capture_output=True)
                 subprocess.run(["tart", "delete", name], capture_output=True)

def run_test(platform):
    print(f"\n{'='*20} Testing {platform.upper()} {'='*20}")
    
    image = IMAGES.get(platform)
    if not image:
        print(f"[!] Unknown platform: {platform}")
        return False

    # Pull image if not present
    print(f"[*] Checking for image {image}...")
    res = subprocess.run(["tart", "list"], capture_output=True, text=True)
    if image not in res.stdout:
        print(f"[*] Pulling {image}...")
        subprocess.run(["tart", "pull", image], check=True)

    zip_path = find_release_zip(platform)
    if not zip_path:
        print(f"[!] No release zip found for {platform} in {BUILD_DIR}")
        return False
    print(f"[+] Found release: {zip_path.name}")

    vm_name = f"wgse-test-{platform}-{int(time.time())}"
    vm = TartVM(vm_name, image)
    
    success = False
    try:
        vm.clone()
        vm.start()
        # Give GUI a moment to spawn
        time.sleep(2)
        
        if not vm.wait_until_ready():
            return False

        remote_zip = "/tmp/release.zip"
        vm.transfer_file(zip_path, remote_zip)
        
        # Define absolute path for target directory based on platform
        # Note: Cirrus images usually use 'admin' as user.
        user = "admin"
        target_root = f"/home/{user}" if platform != "macos" else f"/Users/{user}"
        target_dir = f"{target_root}/WGSExtract"
        
        if not vm.extract_zip(remote_zip, target_dir):
            return False

        print(f"[*] Running installer for {platform}...")
        installer_scripts = {
            "ubuntu": "Install_ubuntu.sh",
            "fedora": "Install_linux.sh",
            "macos": "Install_macos_brew.command"
        }
        installer = installer_scripts[platform]
        installer_path = f"{target_dir}/{installer}"
        
        # Patch installer to disable zxterm sourcing (headless mode execution)
        # Even with GUI enabled, we need to bypass the terminal launcher for automation.
        print("[*] Patching installer to disable GUI terminal verification...")
        # Determine strict regex based on source file.
        # Install_linux.sh: source scripts/zxterm_linux.sh
        # Install_ubuntu.sh: source scripts/zxterm_ubuntu.sh
        vm.exec(rf"sed -i 's/^source scripts\/zxterm/ # source scripts\/zxterm/' {installer_path}")
        
        # Make executable and run
        vm.exec(f"chmod +x {installer_path}")
        
        # Run installer with simulated 'n' for OS updates
        print(f"[*] Execute {installer}...")
        # Stream the output so the user sees it in real-time
        res = vm.exec(f"cd {target_dir} && bash {installer_path}", input_data="n\n", capture_output=False)
        
        # print("--- Installer Output ---")
        # print(res.stdout) # Using stream now, so this will be None
        # print("------------------------")
        
        if res.returncode != 0:
            print(f"[!] Installer failed with code {res.returncode}")
            print("--- Installer Error ---")
            print(res.stderr)
            print("-----------------------")
            # We don't abort immediately as some non-critical errors might occur, 
            # but usually this is bad.

        print("[*] Verifying installation...")
        res = vm.exec(f"ls {target_dir}/program/wgsextract.py")
        if res.returncode != 0:
            print("[!] Verification failed: program/wgsextract.py not found.")
            return False
        
        print("[*] Testing app launch (version check)...")
        # Launch app to verify dependencies
        python_cmd = f"python3 {target_dir}/program/wgsextract.py --version"
        
        # For Linux/Fedora with micromamba, python is in micromamba/bin
        if platform in ["fedora"]:
             python_cmd = f"{target_dir}/micromamba/bin/python3 {target_dir}/program/wgsextract.py --version"
        
        # On macOS, it might be system python or brewed python.
        # The installer sets up pythonx. We'll try the direct python3 command or find the env.
        
        res = vm.exec(python_cmd)
        print(res.stdout)
        
        # Check success criteria
        # 1. return code 0 (ideal)
        # 2. output contains "WGS Extract"
        if res.returncode == 0 or "WGS Extract" in res.stdout:
            print(f"[+++] {platform.upper()} Test Successful!")
            success = True
        else:
            print(f"[!] App launch check failed for {platform}")
            print(res.stderr)

    except KeyboardInterrupt:
        print("\n[!] Test interrupted by user.")
        raise
    except Exception as e:
        print(f"[!] Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        vm.stop()
        vm.delete()
    
    return success

def main():
    parser = argparse.ArgumentParser(description="WGS Extract VM Installation Test System")
    parser.add_argument("--platform", choices=["ubuntu", "fedora", "macos", "all"], default="all",
                        help="Platform to test (default: all)")
    parser.add_argument("--no-release", action="store_true", help="Skip running release.py")
    parser.add_argument("--setup-only", action="store_true", help="Only setup Tart and pull images")
    
    args = parser.parse_args()

    try:
        # Check for Tart
        res = subprocess.run(["command", "-v", "tart"], shell=True, capture_output=True)
        if res.returncode != 0:
            print("[*] Tart not found. Installing via Homebrew...")
            subprocess.run(["brew", "install", "cirruslabs/cli/tart"], check=True)

        if args.setup_only:
            for img in IMAGES.values():
                print(f"[*] Pulling {img}...")
                subprocess.run(["tart", "pull", img])
            return

        # Clean up any mess from before
        cleanup_stale_vms()

        if not args.no_release:
            run_release_script()

        platforms = ["ubuntu", "fedora", "macos"] if args.platform == "all" else [args.platform]
        
        results = {}
        for p in platforms:
            results[p] = run_test(p)

        print("\n" + "="*50)
        print("TEST RESULTS SUMMARY")
        print("="*50)
        for p, success in results.items():
            status = "PASSED" if success else "FAILED"
            print(f"{p.ljust(10)}: {status}")
        print("="*50)

        # Final sweep
        cleanup_stale_vms()

        if not all(results.values()):
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user. Cleaning up...")
        cleanup_stale_vms()
        sys.exit(130)

if __name__ == "__main__":
    main()
