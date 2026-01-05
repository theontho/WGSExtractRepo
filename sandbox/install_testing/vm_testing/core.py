
import subprocess
import time
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BUILD_DIR = REPO_ROOT / "out" / "installer_builds"
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

    def start(self, gui=False):
        print(f"[*] Starting VM {self.name}...")
        # Default networking (shared) is used.
        # We avoid --net-softnet as it may require host-side sudo to set SUID bits.
        cmd = ["tart", "run"]
        if not gui:
            cmd.append("--no-graphics")
        cmd.append(self.name)
        
        self.process = subprocess.Popen(cmd)

    def stop(self):
        print(f"[*] Stopping VM {self.name}...")
        subprocess.run(["tart", "stop", self.name], capture_output=True)
        if self.process:
            self.process.terminate()
            self.process = None

    def delete(self):
        print(f"[*] Deleting VM {self.name}...")
        subprocess.run(["tart", "delete", self.name], capture_output=True)

    def exec(self, command, input_data=None, capture_output=True, user=None):
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
        macos_interface_fix_attempted = False
        macos_dns_fix_attempted = False
        tools_installed = False
        
        while time.time() - start_time < timeout:
            # Check if VM is responsive
            res = self.exec("ls", capture_output=True)
            if res.returncode == 0:
                # Ensure net-tools and ping are installed on Linux if missing
                if not tools_installed and ("ubuntu" in self.image or "fedora" in self.image):
                    print("[*] Ensuring network tools are installed...")
                    if "ubuntu" in self.image:
                        self.exec("echo admin | sudo -S apt-get update && echo admin | sudo -S apt-get install -y net-tools iputils-ping curl")
                    else:
                        self.exec("echo admin | sudo -S dnf install -y net-tools iputils curl")
                    tools_installed = True

                # Check for internet access
                net_res = self.exec("ping -c 1 8.8.8.8", capture_output=True)
                if net_res.returncode == 0:
                    # Internet by IP is good. Now check DNS resolution.
                    dns_res = self.exec("curl -I https://www.google.com", capture_output=True)
                    if dns_res.returncode == 0:
                        print(f"[+] VM {self.name} is ready and online (DNS working).")
                        return True
                    else:
                        print(f"[*] VM {self.name} online by IP but DNS failing.")
                        # If macOS, try to force DNS
                        if not macos_dns_fix_attempted and ("macos" in self.image or "macos" in self.name):
                             print("[*] Attempting macOS DNS fix (setting 8.8.8.8)...")
                             # Try both Ethernet and Wi-Fi to be safe, ignore errors if one doesn't exist
                             self.exec("echo admin | sudo -S /usr/sbin/networksetup -setdnsservers Ethernet 8.8.8.8 || true")
                             self.exec("echo admin | sudo -S /usr/sbin/networksetup -setdnsservers Wi-Fi 8.8.8.8 || true")
                             macos_dns_fix_attempted = True
                else:
                    print(f"[*] VM {self.name} responsive but offline (ping failed).")
                    # If macOS and we haven't tried fix, maybe it needs a nudge
                    if not macos_interface_fix_attempted and ("macos" in self.image or "macos" in self.name):
                         print("[*] Attempting macOS interface fix...")
                         self.exec("echo admin | sudo -S /usr/sbin/ipconfig set en0 DHCP")
                         macos_interface_fix_attempted = True
            
            time.sleep(5)
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
