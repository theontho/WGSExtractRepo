The cli re-implementaiton in the cli/ directory is a completely independent reimplementation of the legacy GUI application in the root directory.  Do not share or link code in it, instead reimplement it in ideally python, referencing the legacy app as a source of truth.

We do not want to manage installing dependencies for users, just validate that they are installed before running the feature. You can add library dependencies as part of the pyproject.toml file.

In general, test and run the code you write.  You are not done if all you do is edit code.  Make sure to test small test genome extraction versions and then full genome versions once the small extraction works. Issues often pop up in full genome runs that don't show up in small test data runs.

You have a large budget and a lot of time to do things correctly.  Favor 'the best practice' or 'correct' way over trying to achieve a solution quickly.  This does not mean doing something in an overly verbose way is "correct", conciseness is it's own virtue.

When outputting test run results, logs, or stdout captures, **always** put them in a gitignored `out/` or `tmp/` directory (or a subdirectory within them). Never output these files to the repository root.

## Python Formatting & Linting

- **Always** run `uv run ruff check --fix {file_path}` and `uv run ruff format {file_path}` after editing a Python file in this directory.
- **Always** run `uv run mypy {file_path}` (or `uv run mypy src/wgsextract_cli`) to check for type errors before concluding a task.
- Ensure that you are in the `cli` directory when running these commands if they are scoped to the `cli` project.
