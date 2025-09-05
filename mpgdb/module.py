import warnings
import gdb
from . import file

NAMES_MP = dict.fromkeys([ # mp_module_{}
    '__main__',
    'alif',
    'asyncio',
    'btree',
    'builtins',
    'cmath',
    'deflate',
    'espnow',
    'ffi',
    'framebuf',
    'gc',
    'jni',
    'js',
    'jsffi',
    'lwip',
    'marshal',
    'math',
    'micropython',
    'mimxrt',
    'network',
    'onewire',
    'renesas',
    'rp2',
    'samd',
    'subsystem',
    'sys',
    'termios',
    'thread',
    'tls',
    'ubluepy',
    'uctypes',
    'vfs',
    'webrepl',
    'zephyr',
    'zsensor',
])

NAMES_MODULE = dict.fromkeys([ # {}_module
    'ble',
    'board',
    'esp32',
    'esp',
    'microbit',
    'music',
    'myport',
    'nrf',
    'openamp',
    'pyb',
    'spiflash',
    'stm',
    'wipy',
])

def _lookup_mp(name: str) -> gdb.Symbol:
    fullname = "mp_module_{}".format(name)
    symbol = file.micropython.lookup_global_symbol(fullname, gdb.SYMBOL_VAR_DOMAIN)
    return symbol
    # return symbol[0].value().address

def _lookup_module(name: str) -> gdb.Symbol:
    fullname = "{}_module".format(name)
    symbol = file.micropython.lookup_global_symbol(fullname, gdb.SYMBOL_VAR_DOMAIN)
    return symbol
    # return symbol[0].value().address

def __getattr__(name: str) -> gdb.Symbol:
    symbol = NAMES_MP.get(name, None)
    if symbol is not None:
        return symbol
    
    symbol = NAMES_MODULE.get(name, None)
    if symbol is not None:
        return symbol
    
    symbol = _lookup_mp(name)
    if symbol is not None:
        NAMES_MP[name] = symbol
        return symbol
    
    symbol = _lookup_module(name)
    if symbol is not None:
        NAMES_MODULE[name] = symbol
        return symbol
    
    if name in NAMES_MP:
        del NAMES_MP[name]

    if name in NAMES_MODULE:
        del NAMES_MODULE[name]

    raise AttributeError(f"Can't find mp_module_{name} or {name}_module.", name=name)
    
def __dir__() -> list[str]:
    return list(NAMES_MP) + list(NAMES_MODULE)
