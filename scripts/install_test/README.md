# WGS Extract VM Testing System

This system uses [Tart](https://tart.run/) to run automated installation tests on fresh macOS and Linux virtual machines.

## Prerequisites

- macOS with Apple Silicon (Tart is Apple Silicon only for macOS VMs)
- Homebrew (to install Tart)

## How to Run

To run all tests (includes release generation):

```bash
python3 scripts/install_test/vm_test.py
```

To run a specific platform test:

```bash
python3 scripts/install_test/vm_test.py --platform ubuntu
```

### Options

- `--platform {ubuntu,fedora,macos,all}`: Specify which OS to test.
- `--no-release`: Skip generating new release zips (uses existing ones in `build/`).
- `--setup-only`: Only ensure Tart is installed and pull base images.

## Script Details

- `vm_test.py`: A unified Python script that manages the entire VM lifecycle. It uses the `subprocess` module to control `tart` and clones, runs, and deletes VMs automatically.


## Notes

- The tests use unique VM names based on timestamps to avoid conflicts.
- VMs are automatically deleted after each test run (even on failure, via `cleanup_vms`).
- Base images used:
  - macOS: `ghcr.io/cirruslabs/macos-sonoma-base:latest`
  - Linux: `ghcr.io/cirruslabs/ubuntu:latest`
