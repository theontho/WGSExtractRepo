#!/usr/bin/env python3
from brew_test_common import run_brew_install_test

def main():
    run_brew_install_test(test_name="new", is_new_installer=True)

if __name__ == "__main__":
    main()
