from new_scripts.core.common import *
from new_scripts.core.logging import *
from new_scripts.core.genomes import *
from new_scripts.core.library import *

import platform

if platform.system() == "Linux":
    from new_scripts.core.linux import *
elif platform.system() == "Darwin":
    from new_scripts.core.macos import *
