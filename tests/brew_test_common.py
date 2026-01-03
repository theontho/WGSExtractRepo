#!/usr/bin/env python3
import os
import sys
import shutil
import sh
import time
import psutil
from pathlib import Path

def run_brew_install_test(test_name: str, is_new_installer: bool):
    repo_root = Path(__file__).resolve().parent.parent
    build_dir = repo_root / "build"
    test_dir_name = f"tmp_test_install_{test_name}"
    test_dir = repo_root / "tmp" / test_dir_name
    
    print(f"[*] Repo root: {repo_root}")
    print(f"[*] Test name: {test_name}")
    print(f"[*] Installer type: {'New (Python)' if is_new_installer else 'Legacy (Bash)'}")

    try:
        # 1. Run release.py
        print(f"[*] Step 1: Running release.py {'-ro -n' if is_new_installer else '-ro'}...")
        release_script = repo_root / "dev" / "release.py"
        args = ["-ro"]
        if is_new_installer:
            args.append("-n")
            
        try:
            sh.python3(str(release_script), *args, _out=sys.stdout, _err=sys.stderr)
        except sh.ErrorReturnCode as e:
            print(f"[!] Error running release script: {e}")
            sys.exit(1)

        # 2. Locate the mac_homebrew package
        print("[*] Step 2: Locating mac_homebrew package...")
        zips = list(build_dir.glob("*_macos_brew_installer.zip"))
        if not zips:
            print("[!] Error: No macOS brew installer zip found in build directory.")
            sys.exit(1)
        
        # Sort by mtime to get the latest
        latest_zip = sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        print(f"[*] Found latest zip: {latest_zip.name}")

        # 3. Extract the package
        print(f"[*] Step 3: Extracting to {test_dir}...")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir(parents=True, exist_ok=True)

        import zipfile
        with zipfile.ZipFile(latest_zip, 'r') as zip_ref:
            zip_ref.extractall(test_dir)

        # 4. Run the installer
        print("[*] Step 4: Running the installer...")
        os.chdir(test_dir)
        
        env = os.environ.copy()
        
        if is_new_installer:
            installer_script = test_dir / "new_scripts" / "install_macos_brew.py"
            try:
                sh.python3(str(installer_script), _out=sys.stdout, _err=sys.stderr, _env=env)
            except sh.ErrorReturnCode as e:
                print(f"[!] Installer returned non-zero code: {e.exit_code}")
                sys.exit(1)
            except Exception as e:
                print(f"[!] Error running installer: {e}")
                sys.exit(1)
        else:
            installer_script = test_dir / "Install_macos_brew.command"
            try:
                sh.bash(str(installer_script), _in="\n", _out=sys.stdout, _err=sys.stderr, _env=env)
            except sh.ErrorReturnCode as e:
                print(f"[!] Installer returned non-zero code: {e.exit_code}")
                sys.exit(1)
            except Exception as e:
                print(f"[!] Error running installer: {e}")
                sys.exit(1)

        # 5. Verify installer worked
        print("[*] Step 5: Verifying installer worked...")
        expected_files = [
            test_dir / "WGSExtract.command",
            test_dir / "program" / "wgsextract.py",
            test_dir / "jartools" # Should be populated
        ]
        
        all_found = True
        for f in expected_files:
            if not f.exists():
                print(f"[!] Missing expected file: {f}")
                all_found = False
            else:
                print(f"[*] Found: {f.name}")
                
        if not all_found:
            print("[!] Verification failed.")
            sys.exit(1)

        # 6. Launch the app
        print("[*] Step 6: Launching the app via WGSExtract.command...")
        app_script = test_dir / "WGSExtract.command"
        
        # Set environment for unbuffered output
        env["PYTHONUNBUFFERED"] = "1"
        
        found_marker = False
        marker_text = "This command script window shows what WGSExtract is doing"
        
        def process_output(line):
            nonlocal found_marker
            sys.stdout.write(line)
            sys.stdout.flush()
            if marker_text in line:
                found_marker = True

        try:
            # Start in background using sh
            process = sh.bash(str(app_script), _bg=True, _in="\n", _out=process_output, _err=sys.stderr, _env=env)
            
            print(f"[*] App launched with PID {process.pid}. Streaming output for 5s...")
            
            # We wait for 5s while the callback handles printing and searching
            time.sleep(5)
            
            # Check if still running
            if process.is_alive():
                print("[*] App is still running after 5s. Success!")
            else:
                print(f"[!] App closed prematurely. Exit code: {process.exit_code}")
                sys.exit(1)

            if not found_marker:
                print(f"[!] Launch marker NOT found: '{marker_text}'")
                sys.exit(1)
            else:
                print("[*] Launch marker found!")
            
            # Terminating app robustly
            print("[*] Terminating app...")
            try:
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                # Wait for processes to exit
                gone, alive = psutil.wait_procs(parent.children(recursive=True) + [parent], timeout=5)
                for p in alive:
                    p.kill()
            except psutil.NoSuchProcess:
                pass
                
        except Exception as e:
            print(f"[!] Error launching app: {e}")
            sys.exit(1)

    finally:
        # 7. Final Cleanup
        print("[*] Step 7: Final cleanup...")
        os.chdir(repo_root) # Go back to root before deleting
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print("[*] Test finished cleanup.")
