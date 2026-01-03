import os
import sys
import shutil
import time
import subprocess
import zipfile
import psutil
from pathlib import Path
from typing import List, Callable, Optional

def run_install_test(
    test_name: str,
    zip_glob_pattern: str,
    installer_cmd: List[str],
    expected_files: List[Path],
    launch_cmd: List[str],
    launch_marker_text: str,
    is_new_installer: bool = False,
    installer_env: Optional[dict] = None,
    archive_extract_subdir: Optional[str] = None,
    installer_input: str = "\n"
):
    repo_root = Path(__file__).resolve().parent.parent
    build_dir = repo_root / "build"
    test_dir_name = f"tmp_test_install_{test_name}"
    test_dir = repo_root / "tmp" / test_dir_name
    
    print(f"[*] Repo root: {repo_root}")
    print(f"[*] Test name: {test_name}")
    print(f"[*] Installer type: {'New (Python)' if is_new_installer else 'Legacy'}")

    # 1. Run release.py
    print(f"[*] Step 1: Running release.py {'-ro -n' if is_new_installer else '-ro'}...")
    release_script = repo_root / "dev" / "release.py"
    release_args = [sys.executable, str(release_script), "-ro"]
    if is_new_installer:
        release_args.append("-n")
    subprocess.run(release_args, check=True)

    # 2. Locate the package
    print(f"[*] Step 2: Locating package with pattern '{zip_glob_pattern}'...")
    zips = list(build_dir.glob(zip_glob_pattern))
    if not zips:
        print(f"[!] Error: No installer zip found matching '{zip_glob_pattern}' in build directory.")
        sys.exit(1)
    latest_zip = sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    print(f"[*] Found latest zip: {latest_zip.name}")

    # 3. Extract the package
    print(f"[*] Step 3: Extracting to {test_dir}...")
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(latest_zip, 'r') as zip_ref:
        zip_ref.extractall(test_dir)

    # 4. Run the installer
    print("[*] Step 4: Running the installer...")
    work_dir = test_dir
    if archive_extract_subdir:
        work_dir = test_dir / archive_extract_subdir
    env = os.environ.copy()
    if installer_env:
        env.update(installer_env)
    
    old_cwd = os.getcwd()
    os.chdir(work_dir)
    try:
        result = subprocess.run(installer_cmd, env=env, input=installer_input, text=True)
        if result.returncode != 0:
            print(f"[!] Installer returned non-zero code: {result.returncode}")
            sys.exit(1)
    finally:
        os.chdir(old_cwd)

    # 5. Verify installer worked
    print("[*] Step 5: Verifying installer worked...")
    all_found = True
    for f in expected_files:
        actual_path = work_dir / f if not f.is_absolute() else f
        if not actual_path.exists():
            print(f"[!] Missing expected file: {actual_path}")
            all_found = False
        else:
            print(f"[*] Found: {actual_path.name}")
    if not all_found:
        print("[!] Verification failed.")
        sys.exit(1)

    # 6. Launch the app
    print(f"[*] Step 6: Launching the app via {launch_cmd}...")
    app_env = env.copy()
    app_env["PYTHONUNBUFFERED"] = "1"
    found_marker = False
    
    def stream_output(process):
        nonlocal found_marker
        for line in iter(process.stdout.readline, ''):
            sys.stdout.write(line)
            sys.stdout.flush()
            if launch_marker_text in line:
                found_marker = True

    proc = subprocess.Popen(
        launch_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        env=app_env,
        cwd=work_dir,
        text=True,
        bufsize=1
    )
    
    try:
        try:
            proc.stdin.write("\n")
            proc.stdin.flush()
        except: pass

        import threading
        thread = threading.Thread(target=stream_output, args=(proc,))
        thread.daemon = True
        thread.start()

        print(f"[*] App launched with PID {proc.pid}. Streaming output for 10s...")
        time.sleep(10)
        
        if not found_marker:
            print(f"[!] Launch marker NOT found: '{launch_marker_text}'")
            sys.exit(1)
        else:
            print("[*] Launch marker found!")
            print("[*] Core test logic PASSED.")
    finally:
        print("[*] Terminating app...")
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            gone, alive = psutil.wait_procs(parent.children(recursive=True) + [parent], timeout=5)
            for p in alive: p.kill()
        except psutil.NoSuchProcess: pass

        # 7. Final Cleanup
        print("[*] Step 7: Final cleanup...")
        os.chdir(repo_root)
        if test_dir.exists():
            time.sleep(2)
            def on_rm_error(func, path, exc_info):
                import stat
                try:
                    os.chmod(path, stat.S_IWUSR)
                    func(path)
                except: pass
            try:
                shutil.rmtree(test_dir, onerror=on_rm_error)
                print("[*] Test finished cleanup.")
            except Exception as e:
                print(f"[!] Warning: Cleanup failed (likely file lock): {e}")
                print("[*] This is non-fatal for the test result.")

    return True
