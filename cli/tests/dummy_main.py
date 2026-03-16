from nicegui import ui
from wgsextract_cli.ui.web_gui import main_page

@ui.page('/')
def index():
    main_page()

ui.run()
