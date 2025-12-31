
import subprocess
import time
import os
import shutil
from pathlib import Path
from .core import IMAGES, REPO_ROOT

class WSLImageManager:
    """Manages downloading and caching of rootfs tarballs for WSL."""
    
    DOWNLOAD_DIR = REPO_ROOT / "download_tmp"
    
    # URL mapping for rootfs tarballs
    # Ubuntu: Cloud images from cloud-images.ubuntu.com
    # Fedora: Container base images from download.fedoraproject.org
    URLS = {
        "ubuntu": "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64-root.tar.xz",
        "fedora": "https://github.com/fedora-cloud/docker-brew-fedora/raw/master/40/x86_64/fedora-40-x86_64.tar.xz" # Using a stable distinct source or direct fedora link if possible. 
        # Actually, for Fedora, "Container Base" is best for WSL. 
        # Let's use a known working mirror or the official one.
        # "https://download.fedoraproject.org/pub/fedora/linux/releases/40/Container/x86_64/images/Fedora-Container-Base-Base-Layer-40-1.14.x86_64.tar.xz"
        # However, finding a stable direct link can be tricky.
        # Alternative: Use "docker export" if docker were available, but it's not.
        # Let's try to find a direct link to a recent rootfs.
    }
    
    # Fallback/Constants
    # Ubuntu 22.04 LTS (WSL-specific rootfs)
    UBUNTU_URL = "https://cloud-images.ubuntu.com/wsl/releases/22.04/current/ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz"
    
    # Fedora 41 (Stable) - Github Mirror for Docker Library
    FEDORA_URL = "https://github.com/fedora-cloud/docker-brew-fedora/raw/41/x86_64/fedora-41-x86_64.tar.xz"

    def __init__(self):
        self.DOWNLOAD_DIR.mkdir(exist_ok=True)

    def get_image_path(self, platform):
        filename = f"{platform}-rootfs.tar.gz" # Simplify extension
        path = self.DOWNLOAD_DIR / filename
        
        if path.exists():
            return path
            
        url = ""
        if platform == "ubuntu":
            url = self.UBUNTU_URL
        elif platform == "fedora":
            url = self.FEDORA_URL
        else:
            raise ValueError(f"Unsupported WSL platform: {platform}")
            
        print(f"[*] Downloading {platform} rootfs from {url}...")
        
        # Use curl to download
        subprocess.run(["curl", "-L", "-o", str(path), url], check=True)
        return path

class WSLVM:
    def __init__(self, name, platform):
        self.name = name
        self.platform = platform
        self.image_manager = WSLImageManager()
        self.install_dir = REPO_ROOT / "temp" / "wsl_vms" / name
        self.install_dir.parent.mkdir(parents=True, exist_ok=True)

    def clone(self):
        tarball = self.image_manager.get_image_path(self.platform)
        print(f"[*] Importing WSL distro {self.name} from {tarball}...")
        # wsl --import <Distro> <InstallLocation> <FileName>
        subprocess.run(
            ["wsl", "--import", self.name, str(self.install_dir), str(tarball)], 
            check=True
        )

    def start(self):
        # WSL starts on demand, but we can boot it to verify
        print(f"[*] Starting WSL distro {self.name}...")
        self.exec("true")

    def stop(self):
        print(f"[*] Stopping WSL distro {self.name}...")
        subprocess.run(["wsl", "-t", self.name], check=False)

    def delete(self):
        print(f"[*] Unregistering WSL distro {self.name}...")
        subprocess.run(["wsl", "--unregister", self.name], check=False)
        if self.install_dir.exists():
            try:
                shutil.rmtree(self.install_dir)
            except Exception as e:
                print(f"[!] Failed to clean up dir {self.install_dir}: {e}")

    def exec(self, command, input_data=None, capture_output=True, user=None):
        cmd = ["wsl", "-d", self.name]
        if user:
            cmd += ["-u", user]
            
        cmd += ["-e", "sh", "-c", command] # Force sh to avoid "command not found" if default shell is weird
        
        # However, complex commands might need quoting. 
        # wsl -e executes the command directly without a shell if we don't specify sh -c.
        # using 'sh -c' allows using pipes and redirects inside the command string.
        
        return subprocess.run(
            cmd,
            input=input_data,
            capture_output=capture_output,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

    def wait_until_ready(self, timeout=60):
        print(f"[*] Waiting for WSL {self.name} connectivity...")
        start = time.time()
        while time.time() - start < timeout:
            res = self.exec("curl -I https://google.com")
            if res.returncode == 0:
                print("[+] WSL connectivity verified.")
                return True
            time.sleep(2)
        print("[!] WSL connectivity check failed.")
        return False

    def transfer_file(self, local_path, remote_path):
        # For WSL, we can just copy to the network share \\wsl$\{name}\...
        # But python path handling for UNC paths can be tricky.
        # 'wsl check' is easier: verify destination dir exists first.
        
        # We can implement 'cat' based transfer for reliability like TartVM
        print(f"[*] Transferring {local_path} to {remote_path} via pipe...")
        with open(local_path, "rb") as f:
            # We construct a command that reads from stdin
                # wsl -d name -e sh -c "cat > remote_path"
            subprocess.run(
                ["wsl", "-d", self.name, "-e", "sh", "-c", f"cat > '{remote_path}'"],
                stdin=f,
                check=True
            )

    def extract_zip(self, remote_zip, target_dir):
        print(f"[*] Extracting {remote_zip} to {target_dir}...")
        # Ensure target dir exists
        self.exec(f"mkdir -p {target_dir}")
        
        # Use python3 if available, or unzip, or tar if it's a tarball (but it's a zip)
        # We'll stick to python3 as typical in the project
        cmd = f"python3 -c 'import zipfile; z = zipfile.ZipFile(\"{remote_zip}\"); z.extractall(\"{target_dir}\")'"
        res = self.exec(cmd)
        if res.returncode != 0:
            print(f"[!] Extraction failed: {res.stderr}")
            # Try to debug what's missing
            self.exec("which python3")
            return False
        return True

    def setup_user(self, username="admin"):
        """
        WSL rootfs images usually just have root.
        We need to create the admin user and give it sudo rights (passwordless).
        """
        print(f"[*] Setting up user '{username}'...")

        # Debug: check current user
        res = self.exec("whoami")
        curr_user = res.stdout.strip()
        print(f"[*] Current default user: {curr_user}")
        
        # Decide if we need to pass -u root
        # If we are already root, passing -u root should be fine, but if it fails we can drop it.
        root_flag = "root" if curr_user != "root" else None
        # Actually, explicitly using 'root' is safer if default isn't root.
        # But if 'root' doesn't strictly exist as a user known to WSL interop yet? (Unlikely)
        
        # Let's try to just run update without user flag if we are root, or with root if we aren't.
        run_as_root = "root"
        
        # 1. Install prerequisites (sudo, python3, curl, unzip, etc)
        print("[*] Installing prerequisites...")
        # Ubuntu vs Fedora
        if "ubuntu" in self.platform:
            # Usually minimal ubuntu doesn't have much
            update_cmd = "apt-get update && apt-get install -y sudo python3 curl tar unzip"
            res = self.exec(update_cmd, user=run_as_root, capture_output=False) 
            if res.returncode != 0:
                 print(f"[!] Prerequisite install failed: {res.returncode}")
                 # Try without user flag?
                 if res.returncode == 4294967295 or "USER_NOT_FOUND" in str(res.stderr):
                     print("[!] Retrying without -u root...")
                     res = self.exec(update_cmd, capture_output=False)

        elif "fedora" in self.platform:
            update_cmd = "dnf install -y sudo python3 curl tar unzip findutils" # findutils for 'xargs' etc
            self.exec(update_cmd, user=run_as_root, capture_output=False)

        # 2. Create user
        # Check if user exists first
        res = self.exec(f"id -u {username}")
        if res.returncode != 0:
            print(f"[*] Creating {username}...")
            # Try /usr/sbin/useradd explicitly
            cmd = f"/usr/sbin/useradd -m -s /bin/bash {username}"
            res = self.exec(cmd, user=run_as_root, capture_output=True)
            print(f"DEBUG: useradd return: {res.returncode}")
            
            # Verify if user exists now
            check = self.exec(f"id -u {username}")
            if check.returncode != 0:
                 print(f"[!] useradd failed or ineffective (ret: {res.returncode}), trying manual method...")
                 # Manual fallback: echo to /etc/passwd and /etc/group
                 # 1000 is standard first user uid
                 self.exec(f"echo '{username}:x:1000:1000:Admin:/home/{username}:/bin/bash' >> /etc/passwd", user=run_as_root)
                 self.exec(f"echo '{username}:x:1000:' >> /etc/group", user=run_as_root)
                 self.exec(f"mkdir -p /home/{username}", user=run_as_root)
                 self.exec(f"chown -R {username}:{username} /home/{username}", user=run_as_root)
                 print(f"[+] Manual user creation applied.")
        else:
            print(f"[*] User {username} already exists.")
        
        # 3. Setup passwordless sudo
        # "echo '{user} ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/{user}"
        print("[*] Configuring sudoers...")
        res = self.exec(f"echo '{username} ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/{username}", user=run_as_root)
        self.exec(f"chmod 0440 /etc/sudoers.d/{username}", user=run_as_root)
        
        print(f"[+] User {username} setup complete.")

