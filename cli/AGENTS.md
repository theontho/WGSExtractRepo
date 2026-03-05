The cli re-implementaiton in the cli/ directory is a completely independent reimplementation of the legacy GUI application in the root directory.  Do not share or link code in it, instead reimplement it in ideally python, referencing the legacy app as a source of truth.

We do not want to manage installing dependencies for users, just validate that they are installed before running the feature. You can add library dependencies as part of the pyproject.toml file.

## Python Formatting & Linting

- **Always** run `uv run ruff check --fix {file_path}` and `uv run ruff format {file_path}` after editing a Python file in this directory.
- **Always** run `uv run mypy {file_path}` (or `uv run mypy src/wgsextract_cli`) to check for type errors before concluding a task.
- Ensure that you are in the `cli` directory when running these commands if they are scoped to the `cli` project.
