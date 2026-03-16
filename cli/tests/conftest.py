import pytest
from pathlib import Path

# Provide the plugin
pytest_plugins = ['nicegui.testing.plugin']

@pytest.fixture(autouse=True)
def mock_get_path_to_main_file(monkeypatch):
    # This is a bit of a hack to satisfy the plugin's requirement for a main_file
    # while our app is actually a package. 
    # We point it to a dummy file that just imports our app.
    root = Path(__file__).parent.parent
    dummy_main = root / 'tests' / 'dummy_main.py'
    if not dummy_main.exists():
        with open(dummy_main, 'w') as f:
            f.write("from wgsextract_cli.ui.web_gui import main_page\nmain_page()\n")
    
    monkeypatch.setattr('nicegui.testing.general_fixtures.get_path_to_main_file', lambda _: str(dummy_main))
