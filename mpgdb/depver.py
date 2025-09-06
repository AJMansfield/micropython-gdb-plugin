import logging
log = logging.getLogger("mpgdb.depver")

from distutils.version import StrictVersion
from types import ModuleType
import sys, os, importlib

def check_gdb():
    try:
        import gdb
    except ImportError:
        log.error("Cannot import GDB!")
        return None
    
    v = StrictVersion(gdb.VERSION)

    if v < "16.0":
        log.error("GDB %s < 16.0, this will not work!", v)

    elif v < "17.0":
        log.warning("GDB %s < 17.0, some features disabled.", v)

    return v

def import_mpytool() -> ModuleType:
    from . import file

    try:
        return importlib.import_module("mpy-tool")
    except ImportError:
        mpy_tools_folder = os.path.normpath(os.path.join(file.micropython.filename, "..", "..", "..", "..", "tools"))
        if mpy_tools_folder not in sys.path:
            sys.path.append(mpy_tools_folder)
        sys.modules["makeqstrdata"]={}
        
        return importlib.import_module("mpy-tool")

def check_mpytool():
    try:
        mpytool = import_mpytool()
        return True
    except ImportError:
        log.error("Cannot import mpy-tool!")
        return False

GDB = check_gdb()
MPY = check_mpytool()
