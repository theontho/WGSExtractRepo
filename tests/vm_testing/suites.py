
import time
from .core import TartVM, IMAGES, REPO_ROOT, BUILD_DIR
from .utils import find_release_zip, create_repo_zip

def run_platform_test(platform):
    print(f"\n{'='*20} Testing {platform.upper()} {'='*20}")
    
    image = IMAGES.get(platform)
    if not image:
        print(f"[!] Unknown platform: {platform}")
        return False

    # Pull image if not present (simplified check using subprocess in runner or here if needed, 
    # but let's assume runner or main setup handles large pulls, or we do it here lazily)
    # The original code did it inside run_test too.
    
    import subprocess
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
        
        if res.returncode != 0:
            print(f"[!] Installer failed with code {res.returncode}")
            print("--- Installer Error ---")
            print(res.stderr)
            print("-----------------------")

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

def run_aptfile_test():
    """Test the Aptfile installation on an Ubuntu VM."""
    print(f"\n{'='*20} Testing Aptfile on UBUNTU {'='*20}")
    platform = "ubuntu"
    image = IMAGES.get(platform)
    
    import subprocess
    # Pull image if not present
    print(f"[*] Checking for image {image}...")
    res = subprocess.run(["tart", "list"], capture_output=True, text=True)
    if image not in res.stdout:
        print(f"[*] Pulling {image}...")
        subprocess.run(["tart", "pull", image], check=True)

    aptfile_path = REPO_ROOT / "Aptfile"
    if not aptfile_path.exists():
        print(f"[!] Aptfile not found at {aptfile_path}")
        return False

    vm_name = f"wgse-apt-test-{int(time.time())}"
    vm = TartVM(vm_name, image)
    
    success = False
    try:
        vm.clone()
        vm.start()
        time.sleep(2)
        
        if not vm.wait_until_ready():
            return False

        remote_aptfile = "/home/admin/Aptfile"
        vm.transfer_file(aptfile_path, remote_aptfile)
        
        print("[*] Updating apt...")
        vm.exec("sudo apt-get update")

        print("[*] Installing packages from Aptfile...")
        install_cmd = (
            "grep -vE '^\\s*#' Aptfile | "
            "grep -vE '^\\s*$' | "
            "tr '\\n' ' ' | "
            "xargs sudo apt-get install -y"
        )
        
        res = vm.exec(f"cd /home/admin && {install_cmd}", capture_output=False)
        
        if res.returncode == 0:
            print("[+++] Aptfile Installation Successful!")
            success = True
        else:
            print(f"[!] Aptfile Installation Failed with code {res.returncode}")
    
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

def run_dev_scripts_test(platform):
    """Test dev_init.py and dev_launch.py on the specified platform."""
    if platform not in ["ubuntu", "macos"]:
        print(f"[!] Dev scripts testing only supported on Ubuntu and MacOS (requested: {platform})")
        return False

    print(f"\n{'=' * 20} Testing Dev Scripts on {platform.upper()} {'=' * 20}")
    
    image = IMAGES.get(platform)
    import subprocess
    
    # Check/Pull Image
    print(f"[*] Checking for image {image}...")
    res = subprocess.run(["tart", "list"], capture_output=True, text=True)
    if image not in res.stdout:
        print(f"[*] Pulling {image}...")
        subprocess.run(["tart", "pull", image], check=True)

    # Prepare Repo Zip
    zip_path = REPO_ROOT / "download_tmp" / "repo_test.zip"
    zip_path.parent.mkdir(exist_ok=True)
    create_repo_zip(zip_path)

    vm_name = f"wgse-dev-test-{platform}-{int(time.time())}"
    vm = TartVM(vm_name, image)
    
    success = False
    try:
        vm.clone()
        vm.start()
        time.sleep(2)  # Wait for boot
        
        if not vm.wait_until_ready():
            return False

        # Define paths
        user = "admin"
        target_root = f"/home/{user}" if platform != "macos" else f"/Users/{user}"
        target_dir = f"{target_root}/WGSExtract_Dev"
        remote_zip = f"{target_root}/repo.zip"

        # Transfer and unzip
        vm.transfer_file(zip_path, remote_zip)
        if not vm.extract_zip(remote_zip, target_dir):
            return False
            
        print("[*] Repo extracted.")

        # Handle Download Cache
        local_cache_dir = REPO_ROOT / "download_tmp"
        if local_cache_dir.exists() and any(local_cache_dir.iterdir()):
             print("[*] Found local download cache. Preparing to transfer...")
             cache_zip_path = REPO_ROOT / "download_tmp" / "cache_transfer.zip"
             
             # Create a zip of the cache content
             # We want the files in download_tmp to be inside target_dir/download_tmp
             import zipfile
             with zipfile.ZipFile(cache_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                 for item in local_cache_dir.iterdir():
                     if item.name == "cache_transfer.zip" or item.name == "repo_test.zip":
                         continue
                     if item.is_file():
                         zf.write(item, item.name)
            
             remote_cache_zip = f"{target_root}/cache.zip"
             vm.transfer_file(cache_zip_path, remote_cache_zip)
             
             # Extract to target_dir/download_tmp
             # Ensure directory exists first
             vm.exec(f"mkdir -p {target_dir}/download_tmp")
             
             print("[*] Extracting cache in VM...")
             cmd = f"python3 -c 'import zipfile; z = zipfile.ZipFile(\"{remote_cache_zip}\"); z.extractall(\"{target_dir}/download_tmp\")'"
             vm.exec(cmd)
             
             # Clean up remote zip
             vm.exec(f"rm {remote_cache_zip}")
             # Clean up local zip
             if cache_zip_path.exists():
                 cache_zip_path.unlink()
             print("[+] Cache transferred.")

        print("[*] Verifying internet access from guest...")
        vm.exec("ip addr show || ifconfig")
        res = vm.exec("curl -I https://google.com", capture_output=True)
        if res.returncode != 0:
            print(f"[!] Warning: Initial connectivity test failed: {res.stderr}")
        else:
            print("[+] Guest has internet access.")

        print("[*] Installing uv...")
        res = vm.exec("curl -LsSf https://astral.sh/uv/install.sh | sh", capture_output=True)
        if res.returncode != 0:
            print(f"[!] UV Install Failed: {res.stderr}")
            return False
        
        # Verify and link (it installs to ~/.local/bin often)
        # Check standard locations
        uv_bin = "/home/admin/.local/bin/uv"
        
        res = vm.exec(f"ls {uv_bin}")
        if res.returncode != 0:
             # Fallback check
             uv_bin = "/home/admin/.cargo/bin/uv"
             res = vm.exec(f"ls {uv_bin}")
             if res.returncode != 0:
                 print("[!] uv binary not found in .local/bin or .cargo/bin.")
                 return False
             
        # Symlink to global path so direct subprocess calls find it easily without PATH dancing
        vm.exec(f"sudo ln -sf {uv_bin} /usr/local/bin/uv")
        
        print("[*] Running dev_init.py...")
        
        # Reset init_cmd to simple invocation now that we have global link
        init_cmd = f"cd {target_dir} && python3 dev_init.py"
        
        res = vm.exec(init_cmd, capture_output=False)
        if res.returncode != 0:
            print(f"[!] dev_init.py failed with code {res.returncode}")
            return False
        
        print("[+++] dev_init.py completed successfully.")
        
        # Verify venv creation
        res = vm.exec(f"ls {target_dir}/.venv/bin/python")
        if res.returncode != 0:
            print("[!] .venv not found or invalid.")
            return False

        print("[*] Testing dev_launch.py...")

        mock_msg = "MOCK_LAUNCH_SUCCESS"
        mock_script_content = f"#!/bin/bash\\necho {mock_msg}\\nexit 0"
        
        script_to_patch = "WGSExtract_ubuntu.sh" if platform == "ubuntu" else "WGSExtract.command"
        patch_path = f"{target_dir}/installer_scripts/{script_to_patch}"
        
        print(f"[*] Patching {script_to_patch} for mock execution...")
        vm.exec(f"echo '{mock_script_content}' > {patch_path}")
        vm.exec(f"chmod +x {patch_path}")
        
        launch_cmd = f"cd {target_dir} && python3 dev_launch.py"
        res = vm.exec(launch_cmd, capture_output=True)
        
        print(res.stdout)
        
        if res.returncode == 0 and mock_msg in res.stdout:
            print("[+++] dev_launch.py launch test successful!")
            success = True
        else:
            print(f"[!] dev_launch.py failed. Code: {res.returncode}")
            print("Output:", res.stdout)
            print("Stderr:", res.stderr)

    except KeyboardInterrupt:
        print("\n[!] Test interrupted.")
        raise
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        vm.stop()
        vm.delete()

    return success

