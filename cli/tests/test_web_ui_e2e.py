import pytest
from nicegui import ui
from nicegui.testing import User
from wgsextract_cli.ui.web_gui_parts.state import state
from wgsextract_cli.ui.web_gui_parts.controller import controller
from wgsextract_cli.core.messages import GUI_LABELS
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_navigation(user: User):
    """Test that clicking sidebar buttons changes the active tab."""
    await user.open('/')
    assert state.active_tab == 'flow'
    
    user.find(GUI_LABELS['tab_vcf']).click()
    assert state.active_tab == 'vcf'
    
    user.find(GUI_LABELS['tab_fastq']).click()
    assert state.active_tab == 'fastq'

@pytest.mark.asyncio
async def test_settings_interaction(user: User):
    """Test that input fields in settings bind correctly to state."""
    state.ref_path = ""
    await user.open('/')
    user.find('settings').click() 
    
    user.find(ui.input).type('/tmp/test_ref')
    assert state.ref_path == '/tmp/test_ref'

@patch('wgsextract_cli.ui.web_gui_parts.common.run_generic_cmd')
@pytest.mark.asyncio
async def test_command_trigger(mock_run, user: User):
    """Test that clicking a command button triggers the command."""
    # Ensure button is enabled
    state.fastq_path = "test.bam"
    state.active_tab = "fastq"
    await user.open('/')
    
    # Standard label 'Index' should work now that logic in fastq.py is fixed
    user.find('Index').click()

    mock_run.assert_called_once()
    assert mock_run.call_args[0][0]['cmd'] == 'index'

@pytest.mark.asyncio
async def test_log_display(user: User):
    """Test that log messages appear in the UI."""
    await user.open('/')
    controller.log("Test log message", tab="Main")
    await user.should_see("Test log message")
