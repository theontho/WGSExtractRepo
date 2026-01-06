from core.common import *
from core.logging import *
from core.genomes import *
from core.library import *

import platform

if platform.system() == "Linux":
    from core.linux import *
elif platform.system() == "Darwin":
    from core.macos import *
