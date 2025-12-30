
import subprocess
import time
from pathlib import Path

# Paths
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
        # We remove --net-softnet to avoid sudo prompts in automated environments.
        # Default networking should be sufficient for basic connectivity.
        self.process = subprocess.Popen(
            ["tart", "run", self.name]
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

    def wait_until_ready(self, timeout=300):
        print(f"[*] Waiting for VM {self.name} to be ready and have network...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if VM is responsive
            res = self.exec("ls", capture_output=True)
            if res.returncode == 0:
                # Check for internet access
                net_res = self.exec("ping -c 1 8.8.8.8", capture_output=True)
                if net_res.returncode == 0:
                    print(f"[+] VM {self.name} is ready and online.")
                    return True
                else:
                    print(f"[*] VM {self.name} responsive but offline (ping failed).")
            
            time.sleep(2)
        print(f"[!] Timeout waiting for VM {self.name} (ready/online check)")
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
