
import sys
import time
from tests.vm_testing.wsl import WSLVM

def main():
    print("Debug WSL User Creation")
    vm = WSLVM("test-debug-wsl", "ubuntu")
    try:
        vm.clone()
        vm.start()
        
        print("--- /etc/passwd before ---")
        vm.exec("cat /etc/passwd", capture_output=False)
        print("--------------------------")

        # 2. Setup user
        print("Setting up user 'admin'...")
        vm.setup_user("admin")
        
        print("--- /etc/passwd after ---")
        vm.exec("cat /etc/passwd", capture_output=False)
        print("-------------------------")
        
        # 3. Verify user exists
        res = vm.exec("id admin")
        print(f"id admin result: {res.returncode}")
        
    except Exception as e:
        print(f"Exception: {e}")
    finally:
        print("Cleaning up...")
        vm.delete()

if __name__ == "__main__":
    main()
