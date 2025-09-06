import logging
log = logging.getLogger("mpgdb.mp")
from typing import Callable, Generic, TypeVar, Iterable, Generator
import abc
T = TypeVar("T")
from . import file
import gdb
import functools

# functools.partial(file.micropython.lookup_static_symbol, domain=gdb.SYMBOL_TYPE_DOMAIN)

_MISSING = object()

class _Lookup(abc.ABC, Generic[T]):
    @abc.abstractmethod
    def _lookup(self, name: str) -> T:
        raise NotImplementedError
    
    _cache: dict[str, T|None]
    _strict: bool

    def __init__(self, names:Iterable[str], strict:bool=False):
        self._cache = dict.fromkeys(names, _MISSING)
        self._strict = strict
    
    def _get(self, name:str, default:T=None) -> T:
        try:
            value = self._cache[name]
        except KeyError:
            value = _MISSING
            if self._strict:
                return default
        
        if value is not _MISSING:
            return value
        
        try:
            value = self._lookup(name)
        except Exception:
            del self._cache[name]
            return default
        else:
            self._cache[name] = value
            return value

    def __getattr__(self, name:str) -> T:
        value = self._get(name, default=_MISSING)
        if value is _MISSING:
            raise AttributeError(f"Can't find {name}.", name=name, obj=self)
        else:
            return value
    
    def __dir__(self):
        yield from super().__dir__()
        yield from self
    
    def __getitem__(self, key:str) -> T:
        value = self._get(key, default=_MISSING)
        if value is _MISSING:
            raise KeyError(f"Can't find {key}.", key)
        else:
            return value


    def __iter__(self) -> Generator[T,None,None]:
        for name in list(self._cache.keys()):
            if self._get(name, default=_MISSING) is not _MISSING:
                yield name

class _MpObjLookup(_Lookup[gdb.Type]):
    def _lookup(self, name):
        fullname = "mp_obj_{}_t".format(name)
        symbol = file.micropython.lookup_static_symbol(fullname, gdb.SYMBOL_TYPE_DOMAIN)
        return symbol.type.pointer()

obj = _MpObjLookup([
    # whole-codebase search for mp_obj_(.*)_t
    'module',
    'dict',
    'fun_bc',
    'base',
    'full_type',
    'list',
    'factorial',
    'type',
    'usb_device',
    'task',
    'task_queue',
    'iter_buf',
    'array',
    'bluetooth_uuid',
    'bluetooth_ble',
    'tuple',
    'new',
    'btree',
    'aes',
    'deflateio_read',
    'deflateio_write',
    'deflateio',
    'framebuf',
    'cast',
    'hash',
    'is',
    'stringio',
    'code',
    're',
    'match',
    'get',
    'poll',
    'ssl_context',
    'ssl_socket',
    'str',
    'uctypes_struct',
    'get_int',
    'webrepl',
    'websocket',
    'fat_vfs',
    'vfs_lfs1',
    'vfs_lfs1_file',
    'vfs_lfs2',
    'vfs_lfs2_file',
    'vfs_posix_file',
    'vfs_posix',
    'listdir',
    'vfs_rom_file',
    'vfs_rom',
    'new_str_of',
    'float',
    'complex',
    'int',
    'streamtest',
    'fun_builtin_fixed',
    'opaque',
    'ffimod',
    'ffivar',
    'ffifunc',
    'fficallback',
    'jclass',
    'jobject',
    'jmethod',
    'fdfile',
    'socket',
    'jsproxy',
    'exception',
    'fun_builtin_var',
    'sensor',
    'instance',
    'bufwriter',
    'thread_lock',
    'empty_type',
    'is_exact',
    'cell',
    'slice',
    'static_class_method',
    'array_it',
    'bool',
    'bound_meth',
    'closure',
    'colines_iter',
    'deque',
    'deque_it',
    'dict_view_it',
    'dict_view',
    'enumerate',
    'exception_clear',
    'exception_add',
    'exception_get',
    'filter',
    'fun_asm',
    'gen_instance',
    'gen_instance_native',
    'getitem_iter',
    'list_it',
    'map',
    'namedtuple_type',
    'namedtuple',
    'new_namedtuple',
    'none',
    'object',
    'is_instance',
    'polymorph_iter',
    'polymorph_iter_with_finaliser',
    'polymorph_with_finaliser_iter',
    'property',
    'range_it',
    'range',
    'reversed',
    'set',
    'set_it',
    'singleton',
    'new_str',
    'str8_it',
    'str_it',
    'tuple_it',
    'super',
    'zip',
    'frame',
    'checked_fun',
])

class _MpTypeLookup(_Lookup[gdb.Value]):
    def _lookup(self, name):
        fullname = "mp_type_{}".format(name)
        symbol = file.micropython.lookup_global_symbol(fullname, gdb.SYMBOL_VAR_DOMAIN)
        return symbol.value().address

type = _MpTypeLookup([
    # From obj.h
    "type",
    "object",
    "NoneType",
    "bool",
    "int",
    "str",
    "bytes",
    "bytearray",
    "memoryview",
    "float",
    "complex",
    "tuple",
    "list",
    "map",
    "enumerate",
    "filter",
    "deque",
    "dict",
    "ordereddict",
    "range",
    "set",
    "frozenset",
    "slice",
    "zip",
    "array",
    "super",
    "gen_wrap",
    "native_gen_wrap",
    "gen_instance",
    "fun_builtin_0",
    "fun_builtin_1",
    "fun_builtin_2",
    "fun_builtin_3",
    "fun_builtin_var",
    "fun_bc",
    "fun_native",
    "fun_viper",
    "fun_asm",
    "code",
    "module",
    "staticmethod",
    "classmethod",
    "bound_meth",
    "property",
    "stringio",
    "bytesio",
    "ringio",
    "reversed",
    "polymorph_iter",
    "polymorph_iter_with_finaliser",
    "BaseException",
    "ArithmeticError",
    "AssertionError",
    "AttributeError",
    "EOFError",
    "Exception",
    "GeneratorExit",
    "ImportError",
    "IndentationError",
    "IndexError",
    "KeyboardInterrupt",
    "KeyError",
    "LookupError",
    "MemoryError",
    "NameError",
    "NotImplementedError",
    "OSError",
    "OverflowError",
    "RuntimeError",
    "StopAsyncIteration",
    "StopIteration",
    "SyntaxError",
    "SystemExit",
    "TypeError",
    "UnicodeError",
    "ValueError",
    "ViperTypeError",
    "ZeroDivisionError",

    # whole-codebase search for MP_DEFINE_CONST_OBJ_TYPE
    "usb_device_builtin_default",
    "usb_device_builtin_none",
    "bluetooth_uuid",
    "bluetooth_ble",
    "framebuf",
    "poll",
    "vfs_fat_fileio",
    "vfs_fat_textio",
    "vfs_posix_fileio",
    "vfs_posix_textio",
    "vfs_posix",
    "vfs_rom_fileio",
    "vfs_rom_textio",
    "vfs_rom",
    "stest_fileio",
    "stest_textio2",
    "socket",
    "jsproxy_gen",
    "jsproxy",
    "undefined",
    "iobase",
    "bufwriter",
    "thread_lock",
    "array",
    "bytearray",
    "memoryview",
    "array_it",
    "attrtuple",
    "bound_meth",
    "closure",
    "code",
    "code",
    "complex",
    "deque",
    "dict_view_it",
    "dict_view",
    "dict",
    "ordereddict",
    "enumerate",
    "BaseException",
    "filter",
    "float",
    "fun_builtin_0",
    "fun_builtin_1",
    "fun_builtin_2",
    "fun_builtin_3",
    "fun_builtin_var",
    "fun_bc",
    "fun_native",
    "fun_viper",
    "fun_asm",
    "gen_wrap",
    "native_gen_wrap",
    "gen_instance",
    "it",
    "int",
    "list",
    "map",
    "module",
    "NoneType",
    "object",
    "polymorph_iter",
    "polymorph_iter_with_finaliser",
    "property",
    "range_it",
    "range",
    "reversed",
    "ringio",
    "set",
    "frozenset",
    "singleton",
    "slice",
    "str",
    "bytes",
    "stringio",
    "bytesio",
    "str",
    "tuple",
    "type",
    "super",
    "staticmethod",
    "classmethod",
    "zip",
    "frame",
    "checked_fun",
])


class _MpModuleLookup(_Lookup[gdb.Value]):
    def _lookup(self, name: str) -> T:
        fullname = "mp_module_{}".format(name)
        symbol = file.micropython.lookup_global_symbol(fullname, gdb.SYMBOL_VAR_DOMAIN)
        return symbol.value().address

module = _MpModuleLookup([
    "__main__",
    "alif",
    "asyncio",
    "btree",
    "builtins",
    "cmath",
    "deflate",
    "espnow",
    "ffi",
    "framebuf",
    "gc",
    "jni",
    "js",
    "jsffi",
    "lwip",
    "marshal",
    "math",
    "micropython",
    "mimxrt",
    "network",
    "onewire",
    "renesas",
    "rp2",
    "samd",
    "subsystem",
    "sys",
    "termios",
    "thread",
    "tls",
    "ubluepy",
    "uctypes",
    "vfs",
    "webrepl",
    "zephyr",
    "zsensor",
])

class _MpExtmodLookup(_Lookup[gdb.Value]):
    def _lookup(self, name: str) -> T:
        fullname = "{}_module".format(name)
        symbol = file.micropython.lookup_global_symbol(fullname, gdb.SYMBOL_VAR_DOMAIN)
        return symbol.value().address

extmod = _MpExtmodLookup([
    "ble",
    "board",
    "esp32",
    "esp",
    "microbit",
    "music",
    "myport",
    "nrf",
    "openamp",
    "pyb",
    "spiflash",
    "stm",
    "wipy",
])

def _macro_expand(macro):
    return gdb.execute(f"macro expand {macro}", from_tty=False, to_string=True).removeprefix("expands to: ").removesuffix("\n")

def _macro_eval(macro):
    return gdb.parse_and_eval(macro, True)

def _format_macro_arg(arg):
    if isinstance(arg, gdb.Value):
        content = arg.format_string(raw=True, symbols=False, address=True, deref_refs=False)
        return f"(({arg.type}){content})"
    else:
        return str(arg)

def _macro_call(macro, *args):
    args_list = ",".join(_format_macro_arg(arg) for arg in args)
    return _macro_eval(f"{macro}({args_list})")

def _macro_eval_template(template, *args):
    expr = template.format(*(_format_macro_arg(arg) for arg in args))
    return _macro_eval(expr)


class _MacroConstLookup(_Lookup[gdb.Value]):
    def _lookup(self, name):
        return _macro_eval(name)
    # _lookup = _macro_eval

macro = _MacroConstLookup(strict=True, names=[
    # from mpconfig.h
    "MICROPY_VERSION_MAJOR",
    "MICROPY_VERSION_MINOR",
    "MICROPY_VERSION_MICRO",
    "MICROPY_VERSION_PRERELEASE",
    "MICROPY_VERSION",
    "MICROPY_VERSION_STRING_BASE",
    "MICROPY_VERSION_STRING",
    "MICROPY_VERSION_STRING",
    "MICROPY_PREVIEW_VERSION_2",
    "MICROPY_CONFIG_ROM_LEVEL_MINIMUM",
    "MICROPY_CONFIG_ROM_LEVEL_CORE_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_BASIC_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_EXTRA_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_FULL_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_EVERYTHING",
    "MICROPY_CONFIG_ROM_LEVEL",
    "MICROPY_CONFIG_ROM_LEVEL_AT_LEAST_CORE_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_AT_LEAST_BASIC_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_AT_LEAST_EXTRA_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_AT_LEAST_FULL_FEATURES",
    "MICROPY_CONFIG_ROM_LEVEL_AT_LEAST_EVERYTHING",
    "MICROPY_OBJ_REPR_A",
    "MICROPY_OBJ_REPR_B",
    "MICROPY_OBJ_REPR_C",
    "MICROPY_OBJ_REPR_D",
    "MICROPY_OBJ_REPR",
    "MICROPY_OBJ_IMMEDIATE_OBJS",
    "MICROPY_BYTES_PER_GC_BLOCK",
    "MICROPY_ALLOC_GC_STACK_SIZE",
    "MICROPY_GC_STACK_ENTRY_TYPE",
    "MICROPY_GC_CONSERVATIVE_CLEAR",
    "MICROPY_GC_ALLOC_THRESHOLD",
    "MICROPY_ALLOC_QSTR_CHUNK_INIT",
    "MICROPY_ALLOC_LEXER_INDENT_INIT",
    "MICROPY_ALLOC_LEXEL_INDENT_INC",
    "MICROPY_ALLOC_PARSE_RULE_INIT",
    "MICROPY_ALLOC_PARSE_RULE_INC",
    "MICROPY_ALLOC_PARSE_RESULT_INIT",
    "MICROPY_ALLOC_PARSE_RESULT_INC",
    "MICROPY_ALLOC_PARSE_INTERN_STRING_LEN",
    "MICROPY_ALLOC_PARSE_CHUNK_INIT",
    "MICROPY_ALLOC_SCOPE_ID_INIT",
    "MICROPY_ALLOC_SCOPE_ID_INC",
    "MICROPY_ALLOC_PATH_MAX",
    "MICROPY_MODULE_DICT_SIZE",
    "MICROPY_LOADED_MODULES_DICT_SIZE",
    "MICROPY_MALLOC_USES_ALLOCATED_SIZE",
    "MICROPY_QSTR_BYTES_IN_LEN",
    "MICROPY_QSTR_BYTES_IN_HASH",
    "MICROPY_QSTR_BYTES_IN_HASH",
    "MICROPY_QSTR_BYTES_IN_HASH",
    "MICROPY_STACKLESS",
    "MICROPY_STACKLESS_STRICT",
    "MICROPY_PERSISTENT_CODE_LOAD",
    "MICROPY_PERSISTENT_CODE_SAVE",
    "MICROPY_PERSISTENT_CODE_SAVE_FILE",
    "MICROPY_PERSISTENT_CODE_SAVE_FUN",
    "MICROPY_PERSISTENT_CODE",
    "MICROPY_EMIT_BYTECODE_USES_QSTR_TABLE",
    "MICROPY_EMIT_X64",
    "MICROPY_EMIT_X86",
    "MICROPY_EMIT_THUMB",
    "MICROPY_EMIT_THUMB_ARMV7M",
    "MICROPY_EMIT_INLINE_THUMB",
    "MICROPY_EMIT_INLINE_THUMB_FLOAT",
    "MICROPY_EMIT_ARM",
    "MICROPY_EMIT_XTENSA",
    "MICROPY_EMIT_INLINE_XTENSA",
    "MICROPY_EMIT_INLINE_XTENSA_UNCOMMON_OPCODES",
    "MICROPY_EMIT_XTENSAWIN",
    "MICROPY_EMIT_RV32",
    "MICROPY_EMIT_INLINE_RV32",
    "MICROPY_EMIT_NATIVE_DEBUG",
    "MICROPY_EMIT_NATIVE",
    "MICROPY_EMIT_NATIVE_PRELUDE_SEPARATE_FROM_MACHINE_CODE",
    "MICROPY_EMIT_INLINE_ASM",
    "MICROPY_EMIT_MACHINE_CODE",
    "MICROPY_ENABLE_COMPILER",
    "MICROPY_DYNAMIC_COMPILER",
    "MICROPY_COMP_ALLOW_TOP_LEVEL_AWAIT",
    "MICROPY_COMP_CONST_FOLDING",
    "MICROPY_COMP_CONST_TUPLE",
    "MICROPY_COMP_CONST_LITERAL",
    "MICROPY_COMP_MODULE_CONST",
    "MICROPY_COMP_CONST",
    "MICROPY_COMP_CONST_FLOAT",
    "MICROPY_COMP_DOUBLE_TUPLE_ASSIGN",
    "MICROPY_COMP_TRIPLE_TUPLE_ASSIGN",
    "MICROPY_COMP_RETURN_IF_EXPR",
    "MICROPY_MEM_STATS",
    "MICROPY_DEBUG_PRINTER",
    "MICROPY_DEBUG_PRINTERS",
    "MICROPY_DEBUG_VERBOSE",
    "MICROPY_DEBUG_MP_OBJ_SENTINELS",
    "MICROPY_DEBUG_PARSE_RULE_NAME",
    "MICROPY_DEBUG_VM_STACK_OVERFLOW",
    "MICROPY_DEBUG_VALGRIND",
    "MICROPY_OPT_COMPUTED_GOTO",
    "MICROPY_OPT_LOAD_ATTR_FAST_PATH",
    "MICROPY_OPT_MAP_LOOKUP_CACHE",
    "MICROPY_OPT_MAP_LOOKUP_CACHE_SIZE",
    "MICROPY_OPT_MPZ_BITWISE",
    "MICROPY_OPT_MATH_FACTORIAL",
    "MICROPY_NLR_THUMB_USE_LONG_JUMP",
    "MICROPY_ENABLE_EXTERNAL_IMPORT",
    "MICROPY_READER_POSIX",
    "MICROPY_READER_VFS",
    "MICROPY_HAS_FILE_READER",
    "MICROPY_ENABLE_GC",
    "MICROPY_GC_SPLIT_HEAP",
    "MICROPY_GC_SPLIT_HEAP_AUTO",
    "MICROPY_TRACKED_ALLOC",
    "MICROPY_ENABLE_FINALISER",
    "MICROPY_ENABLE_PYSTACK",
    "MICROPY_PYSTACK_ALIGN",
    "MICROPY_STACK_CHECK",
    "MICROPY_STACK_CHECK_MARGIN",
    "MICROPY_ENABLE_EMERGENCY_EXCEPTION_BUF",
    "MICROPY_EMERGENCY_EXCEPTION_BUF_SIZE",
    "MICROPY_KBD_EXCEPTION",
    "MICROPY_ASYNC_KBD_INTR",
    "MICROPY_HELPER_REPL",
    "MICROPY_REPL_INFO",
    "MICROPY_REPL_EMACS_KEYS",
    "MICROPY_REPL_EMACS_WORDS_MOVE",
    "MICROPY_REPL_EMACS_EXTRA_WORDS_MOVE",
    "MICROPY_REPL_AUTO_INDENT",
    "MICROPY_REPL_EVENT_DRIVEN",
    "MICROPY_READLINE_HISTORY_SIZE",
    "MICROPY_HELPER_LEXER_UNIX",
    "MICROPY_LONGINT_IMPL_NONE",
    "MICROPY_LONGINT_IMPL_LONGLONG",
    "MICROPY_LONGINT_IMPL_MPZ",
    "MICROPY_LONGINT_IMPL",
    "MICROPY_ENABLE_SOURCE_LINE",
    "MICROPY_ENABLE_DOC_STRING",
    "MICROPY_ERROR_REPORTING_NONE",
    "MICROPY_ERROR_REPORTING_TERSE",
    "MICROPY_ERROR_REPORTING_NORMAL",
    "MICROPY_ERROR_REPORTING_DETAILED",
    "MICROPY_ERROR_REPORTING",
    "MICROPY_ERROR_REPORTING",
    "MICROPY_ERROR_REPORTING",
    "MICROPY_WARNINGS",
    "MICROPY_WARNINGS_CATEGORY",
    "MICROPY_ERROR_PRINTER",
    "MICROPY_FLOAT_IMPL_NONE",
    "MICROPY_FLOAT_IMPL_FLOAT",
    "MICROPY_FLOAT_IMPL_DOUBLE",
    "MICROPY_FLOAT_IMPL",
    "MICROPY_PY_BUILTINS_FLOAT",
    "MICROPY_PY_BUILTINS_FLOAT",
    "MICROPY_PY_BUILTINS_FLOAT",
    "MICROPY_PY_BUILTINS_COMPLEX",
    "MICROPY_FLOAT_FORMAT_IMPL_BASIC",
    "MICROPY_FLOAT_FORMAT_IMPL_APPROX",
    "MICROPY_FLOAT_FORMAT_IMPL_EXACT",
    "MICROPY_FLOAT_FORMAT_IMPL",
    "MICROPY_FLOAT_FORMAT_IMPL",
    "MICROPY_FLOAT_FORMAT_IMPL",
    "MICROPY_FLOAT_USE_NATIVE_FLT16",
    "MICROPY_FLOAT_USE_NATIVE_FLT16",
    "MICROPY_FLOAT_HIGH_QUALITY_HASH",
    "MICROPY_CPYTHON_COMPAT",
    "MICROPY_FULL_CHECKS",
    "MICROPY_EPOCH_IS_2000",
    "MICROPY_EPOCH_IS_1970",
    "MICROPY_EPOCH_IS_1970",
    "MICROPY_EPOCH_IS_2000",
    "MICROPY_TIME_SUPPORT_Y1969_AND_BEFORE",
    "MICROPY_TIME_SUPPORT_Y1969_AND_BEFORE",
    "MICROPY_TIME_SUPPORT_Y2100_AND_BEYOND",
    "MICROPY_TIMESTAMP_IMPL_LONG_LONG",
    "MICROPY_TIMESTAMP_IMPL_UINT",
    "MICROPY_TIMESTAMP_IMPL_TIME_T",
    "MICROPY_TIMESTAMP_IMPL",
    "MICROPY_TIMESTAMP_IMPL",
    "MICROPY_STREAMS_NON_BLOCK",
    "MICROPY_STREAMS_POSIX_API",
    "MICROPY_MODULE___ALL__",
    "MICROPY_MODULE___FILE__",
    "MICROPY_MODULE_ATTR_DELEGATION",
    "MICROPY_MODULE_BUILTIN_INIT",
    "MICROPY_MODULE_BUILTIN_SUBPACKAGES",
    "MICROPY_MODULE_GETATTR",
    "MICROPY_MODULE_OVERRIDE_MAIN_IMPORT",
    "MICROPY_MODULE_FROZEN_STR",
    "MICROPY_MODULE_FROZEN_MPY",
    "MICROPY_MODULE_FROZEN",
    "MICROPY_CAN_OVERRIDE_BUILTINS",
    "MICROPY_BUILTIN_METHOD_CHECK_SELF_ARG",
    "MICROPY_USE_INTERNAL_ERRNO",
    "MICROPY_USE_INTERNAL_PRINTF",
    "MICROPY_INTERNAL_PRINTF_PRINTER",
    "MICROPY_ENABLE_VM_ABORT",
    "MICROPY_ENABLE_SCHEDULER",
    "MICROPY_SCHEDULER_STATIC_NODES",
    "MICROPY_SCHEDULER_DEPTH",
    "MICROPY_VFS",
    "MICROPY_VFS_WRITABLE",
    "MICROPY_VFS_ROM_IOCTL",
    "MICROPY_VFS_POSIX",
    "MICROPY_VFS_POSIX_WRITABLE",
    "MICROPY_VFS_FAT",
    "MICROPY_VFS_LFS1",
    "MICROPY_VFS_LFS2",
    "MICROPY_VFS_ROM",
    "MICROPY_MULTIPLE_INHERITANCE",
    "MICROPY_PY_FUNCTION_ATTRS",
    "MICROPY_PY_FUNCTION_ATTRS_CODE",
    "MICROPY_PY_BOUND_METHOD_FULL_EQUALITY_CHECK",
    "MICROPY_PY_DESCRIPTORS",
    "MICROPY_PY_DELATTR_SETATTR",
    "MICROPY_PY_ASYNC_AWAIT",
    "MICROPY_PY_FSTRINGS",
    "MICROPY_PY_ASSIGN_EXPR",
    "MICROPY_PY_GENERATOR_PEND_THROW",
    "MICROPY_PY_STR_BYTES_CMP_WARN",
    "MICROPY_PY_BUILTINS_BYTES_HEX",
    "MICROPY_PY_BUILTINS_STR_UNICODE",
    "MICROPY_PY_BUILTINS_STR_UNICODE_CHECK",
    "MICROPY_PY_BUILTINS_STR_CENTER",
    "MICROPY_PY_BUILTINS_STR_COUNT",
    "MICROPY_PY_BUILTINS_STR_OP_MODULO",
    "MICROPY_PY_BUILTINS_STR_PARTITION",
    "MICROPY_PY_BUILTINS_STR_SPLITLINES",
    "MICROPY_PY_BUILTINS_BYTEARRAY",
    "MICROPY_PY_BUILTINS_CODE_NONE",
    "MICROPY_PY_BUILTINS_CODE_MINIMUM",
    "MICROPY_PY_BUILTINS_CODE_BASIC",
    "MICROPY_PY_BUILTINS_CODE_FULL",
    "MICROPY_PY_BUILTINS_CODE",
    "MICROPY_PY_BUILTINS_DICT_FROMKEYS",
    "MICROPY_PY_BUILTINS_MEMORYVIEW",
    "MICROPY_PY_BUILTINS_MEMORYVIEW_ITEMSIZE",
    "MICROPY_PY_BUILTINS_SET",
    "MICROPY_PY_BUILTINS_SLICE",
    "MICROPY_PY_BUILTINS_SLICE_ATTRS",
    "MICROPY_PY_BUILTINS_SLICE_INDICES",
    "MICROPY_PY_BUILTINS_FROZENSET",
    "MICROPY_PY_BUILTINS_PROPERTY",
    "MICROPY_PY_BUILTINS_RANGE_ATTRS",
    "MICROPY_PY_BUILTINS_RANGE_BINOP",
    "MICROPY_PY_BUILTINS_NEXT2",
    "MICROPY_PY_BUILTINS_ROUND_INT",
    "MICROPY_PY_ALL_SPECIAL_METHODS",
    "MICROPY_PY_ALL_INPLACE_SPECIAL_METHODS",
    "MICROPY_PY_REVERSE_SPECIAL_METHODS",
    "MICROPY_PY_BUILTINS_COMPILE",
    "MICROPY_PY_BUILTINS_ENUMERATE",
    "MICROPY_PY_BUILTINS_EVAL_EXEC",
    "MICROPY_PY_BUILTINS_EXECFILE",
    "MICROPY_PY_BUILTINS_FILTER",
    "MICROPY_PY_BUILTINS_REVERSED",
    "MICROPY_PY_BUILTINS_NOTIMPLEMENTED",
    "MICROPY_PY_BUILTINS_INPUT",
    "MICROPY_PY_BUILTINS_MIN_MAX",
    "MICROPY_PY_BUILTINS_POW3",
    "MICROPY_PY_BUILTINS_HELP",
    "MICROPY_PY_BUILTINS_HELP_TEXT",
    "MICROPY_PY_BUILTINS_HELP_MODULES",
    "MICROPY_PY_MICROPYTHON_MEM_INFO",
    "MICROPY_PY_MICROPYTHON_STACK_USE",
    "MICROPY_PY_MICROPYTHON_HEAP_LOCKED",
    "MICROPY_PY_MICROPYTHON_RINGIO",
    "MICROPY_PY_ARRAY",
    "MICROPY_PY_ARRAY_SLICE_ASSIGN",
    "MICROPY_PY_ATTRTUPLE",
    "MICROPY_PY_COLLECTIONS",
    "MICROPY_PY_COLLECTIONS_DEQUE",
    "MICROPY_PY_COLLECTIONS_DEQUE_ITER",
    "MICROPY_PY_COLLECTIONS_DEQUE_SUBSCR",
    "MICROPY_PY_COLLECTIONS_ORDEREDDICT",
    "MICROPY_PY_COLLECTIONS_NAMEDTUPLE__ASDICT",
    "MICROPY_PY_MARSHAL",
    "MICROPY_PY_MATH",
    "MICROPY_PY_MATH_CONSTANTS",
    "MICROPY_PY_MATH_SPECIAL_FUNCTIONS",
    "MICROPY_PY_MATH_FACTORIAL",
    "MICROPY_PY_MATH_ISCLOSE",
    "MICROPY_PY_MATH_ATAN2_FIX_INFNAN",
    "MICROPY_PY_MATH_FMOD_FIX_INFNAN",
    "MICROPY_PY_MATH_MODF_FIX_NEGZERO",
    "MICROPY_PY_MATH_POW_FIX_NAN",
    "MICROPY_PY_MATH_GAMMA_FIX_NEGINF",
    "MICROPY_PY_CMATH",
    "MICROPY_PY_MICROPYTHON",
    "MICROPY_PY_GC",
    "MICROPY_PY_GC_COLLECT_RETVAL",
    "MICROPY_PY_IO",
    "MICROPY_PY_IO_IOBASE",
    "MICROPY_PY_IO_BYTESIO",
    "MICROPY_PY_IO_BUFFEREDWRITER",
    "MICROPY_PY_STRUCT",
    "MICROPY_PY_STRUCT_UNSAFE_TYPECODES",
    "MICROPY_PY_SYS",
    "MICROPY_PY_SYS_PATH_ARGV_DEFAULTS",
    "MICROPY_PY_SYS_MAXSIZE",
    "MICROPY_PY_SYS_MODULES",
    "MICROPY_PY_SYS_EXC_INFO",
    "MICROPY_PY_SYS_EXECUTABLE",
    "MICROPY_PY_SYS_INTERN",
    "MICROPY_PY_SYS_EXIT",
    "MICROPY_PY_SYS_ATEXIT",
    "MICROPY_PY_SYS_PATH",
    "MICROPY_PY_SYS_ARGV",
    "MICROPY_PY_SYS_PS1_PS2",
    "MICROPY_PY_SYS_SETTRACE",
    "MICROPY_PY_SYS_GETSIZEOF",
    "MICROPY_PY_SYS_STDFILES",
    "MICROPY_PY_SYS_STDIO_BUFFER",
    "MICROPY_PY_SYS_TRACEBACKLIMIT",
    "MICROPY_PY_SYS_ATTR_DELEGATION",
    "MICROPY_PY_ERRNO",
    "MICROPY_PY_ERRNO_ERRORCODE",
    "MICROPY_PY_SELECT",
    "MICROPY_PY_SELECT_POSIX_OPTIMISATIONS",
    "MICROPY_PY_SELECT_SELECT",
    "MICROPY_PY_TIME",
    "MICROPY_PY_TIME_GMTIME_LOCALTIME_MKTIME",
    "MICROPY_PY_TIME_TIME_TIME_NS",
    "MICROPY_PY_TIME_TICKS_PERIOD",
    "MICROPY_PY_THREAD",
    "MICROPY_PY_THREAD_GIL",
    "MICROPY_PY_THREAD_GIL_VM_DIVISOR",
    "MICROPY_PY_THREAD_RECURSIVE_MUTEX",
    "MICROPY_PY_ASYNCIO",
    "MICROPY_PY_ASYNCIO_TASK_QUEUE_PUSH_CALLBACK",
    "MICROPY_PY_UCTYPES",
    "MICROPY_PY_UCTYPES_NATIVE_C_TYPES",
    "MICROPY_PY_DEFLATE",
    "MICROPY_PY_DEFLATE_COMPRESS",
    "MICROPY_PY_JSON",
    "MICROPY_PY_JSON_SEPARATORS",
    "MICROPY_PY_OS",
    "MICROPY_PY_OS_STATVFS",
    "MICROPY_PY_RE",
    "MICROPY_PY_RE_DEBUG",
    "MICROPY_PY_RE_MATCH_GROUPS",
    "MICROPY_PY_RE_MATCH_SPAN_START_END",
    "MICROPY_PY_RE_SUB",
    "MICROPY_PY_HEAPQ",
    "MICROPY_PY_HASHLIB",
    "MICROPY_PY_HASHLIB_MD5",
    "MICROPY_PY_HASHLIB_SHA1",
    "MICROPY_PY_HASHLIB_SHA256",
    "MICROPY_PY_CRYPTOLIB",
    "MICROPY_PY_CRYPTOLIB_CTR",
    "MICROPY_PY_CRYPTOLIB_CONSTS",
    "MICROPY_PY_BINASCII",
    "MICROPY_PY_BINASCII_CRC32",
    "MICROPY_PY_RANDOM",
    "MICROPY_PY_RANDOM_EXTRA_FUNCS",
    "MICROPY_PY_MACHINE",
    "MICROPY_PY_MACHINE_RESET",
    "MICROPY_PY_MACHINE_FREQ_NUM_ARGS_MAX",
    "MICROPY_PY_MACHINE_BITSTREAM",
    "MICROPY_PY_MACHINE_PULSE",
    "MICROPY_PY_MACHINE_MEMX",
    "MICROPY_PY_MACHINE_SIGNAL",
    "MICROPY_PY_MACHINE_I2C",
    "MICROPY_PY_MACHINE_I2C_TRANSFER_WRITE1",
    "MICROPY_PY_MACHINE_SOFTI2C",
    "MICROPY_PY_MACHINE_SPI",
    "MICROPY_PY_MACHINE_SOFTSPI",
    "MICROPY_PY_MACHINE_SPI_MSB",
    "MICROPY_PY_MACHINE_SPI_LSB",
    "MICROPY_PY_MACHINE_TIMER",
    "MICROPY_PY_SOCKET_LISTEN_BACKLOG_DEFAULT",
    "MICROPY_PY_SSL",
    "MICROPY_PY_SSL_FINALISER",
    "MICROPY_PY_SSL_MBEDTLS_NEED_ACTIVE_CONTEXT",
    "MICROPY_PY_SSL_DTLS",
    "MICROPY_PY_VFS",
    "MICROPY_PY_WEBSOCKET",
    "MICROPY_PY_FRAMEBUF",
    "MICROPY_PY_BTREE",
    "MICROPY_PY_ONEWIRE",
    "MICROPY_PY_PLATFORM",
    "MICROPY_BANNER_NAME_AND_VERSION",
    "MICROPY_BANNER_NAME_AND_VERSION",
    "MICROPY_BANNER_MACHINE",
    "MICROPY_BANNER_MACHINE",
    "MP_BYTES_PER_OBJ_WORD",
    "MP_BITS_PER_BYTE",
    "MP_OBJ_WORD_MSBIT_HIGH",
    "MP_ENDIANNESS_BIG",
    "MP_ENDIANNESS_LITTLE",
    "MP_ENDIANNESS_LITTLE",
    "MP_ENDIANNESS_LITTLE",
    "MP_ENDIANNESS_LITTLE",
    "MP_ENDIANNESS_LITTLE",
    "MP_ENDIANNESS_BIG",
    "MICROPY_PERSISTENT_CODE_TRACK_FUN_DATA",
    "MICROPY_PERSISTENT_CODE_TRACK_BSS_RODATA",
    "MICROPY_PERSISTENT_CODE_TRACK_FUN_DATA",
    "MICROPY_PERSISTENT_CODE_TRACK_BSS_RODATA",
    "MICROPY_PERSISTENT_CODE_TRACK_FUN_DATA",
    "MICROPY_PERSISTENT_CODE_TRACK_BSS_RODATA",
    "MP_SSIZE_MAX",
    "UINT_FMT",
    "INT_FMT",
    "HEX_FMT",
    "UINT_FMT",
    "INT_FMT",
    "HEX_FMT",
    "UINT_FMT",
    "INT_FMT",
    "HEX_FMT",
    "MP_NORETURN",
    "NORETURN",
    "MP_WEAK",
    "MP_NOINLINE",
    "MP_ALWAYSINLINE",
    "MP_UNREACHABLE",
    "MP_UNREACHABLE",
    "MP_FALLTHROUGH",

    # from obj.h
    "MP_OBJ_NULL",
    "MP_OBJ_STOP_ITERATION",
    "MP_OBJ_SENTINEL",
    "MP_OBJ_NULL",
    "MP_OBJ_STOP_ITERATION",
    "MP_OBJ_SENTINEL",
    "MP_ROM_NONE",
    "MP_ROM_NONE",
    "MP_ROM_FALSE",
    "MP_ROM_TRUE",
    "MP_ROM_FALSE",
    "MP_ROM_TRUE",
    "MP_OBJ_FUN_ARGS_MAX",
    "MP_TYPE_FLAG_NONE",
    "MP_TYPE_FLAG_IS_SUBCLASSED",
    "MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS",
    "MP_TYPE_FLAG_EQ_NOT_REFLEXIVE",
    "MP_TYPE_FLAG_EQ_CHECKS_OTHER_TYPE",
    "MP_TYPE_FLAG_EQ_HAS_NEQ_TEST",
    "MP_TYPE_FLAG_BINDS_SELF",
    "MP_TYPE_FLAG_BUILTIN_FUN",
    "MP_TYPE_FLAG_ITER_IS_GETITER",
    "MP_TYPE_FLAG_ITER_IS_ITERNEXT",
    "MP_TYPE_FLAG_ITER_IS_CUSTOM",
    "MP_TYPE_FLAG_ITER_IS_STREAM",
    "MP_TYPE_FLAG_INSTANCE_TYPE",
    "MP_TYPE_FLAG_SUBSCR_ALLOWS_STACK_SLICE",
    "MP_TYPE_FLAG_IS_INSTANCED",
    "MP_TYPE_FLAG_HAS_FINALISER",
    "MP_OBJ_ITER_BUF_NSLOTS",
    "MP_BUFFER_READ",
    "MP_BUFFER_WRITE",
    "MP_BUFFER_RW",
    "MP_BUFFER_RAISE_IF_UNSUPPORTED",
])

class ReprParameter(gdb.Parameter):
    """Configure what mp_obj_t repr to decode with.
    filled = Show only filled map slots.
    all = Show all slots, including [sentinel] and [null].
    """
    REPR_A = "REPR_A"
    REPR_B = "REPR_B"
    REPR_C = "REPR_C"
    REPR_D = "REPR_D"
    ENUM = [REPR_A, REPR_B, REPR_C, REPR_D]
    def __init__ (self, name:str):
        self.set_doc = "Configure what mp_obj_t repr to decode with."
        super().__init__(name, gdb.COMMAND_DATA, gdb.PARAM_ENUM, self.ENUM)
        log.info("Registered parameter: %s", name)
        self._unset = True

    def get_set_string(self):
        self._unset = False
        return ""
    
    def get_show_string(self, svalue):
        if self._maybe_do_guess():
            return self.value
        else:
            return svalue

    def _maybe_do_guess(self):
        if self._unset:
            self.value = self._guess()
            self._unset = False
            return True
        else:
            return False
        
    def _guess(self):
        try:
            repr_value = macro.MICROPY_OBJ_REPR
        except AttributeError:
            pass
        else:
            if repr_value == macro.MICROPY_OBJ_REPR_A:
                return self.REPR_A
            if repr_value == macro.MICROPY_OBJ_REPR_B:
                return self.REPR_B
            if repr_value == macro.MICROPY_OBJ_REPR_C:
                return self.REPR_C
            if repr_value == macro.MICROPY_OBJ_REPR_D:
                return self.REPR_D
            log.warning("Unknown repr %s", repr_value)
            
        log.warning("Assuming %s", self.value)
        return self.value
    
    def _fallback_macro_templates(self):
        self._maybe_do_guess()
        all_fallbacks = {
            self.REPR_A:{
                "MP_OBJ_FROM_PTR": "((mp_obj_t)({0}))",
                "MP_OBJ_TO_PTR": "((void *)({0}))",
                "MP_OBJ_IS_SMALL_INT": "(((mp_int_t)({0})) & 1) != 0",
                "MP_OBJ_SMALL_INT_VALUE": "(((mp_int_t)({0})) >> 1)",
                "MP_OBJ_NEW_SMALL_INT": "((mp_obj_t)((((mp_uint_t)({0})) << 1) | 1))",
                "MP_OBJ_IS_QSTR": "(((mp_int_t)({0})) & 7) == 2",
                "MP_OBJ_QSTR_VALUE": "(((mp_uint_t)({0})) >> 3)",
                "MP_OBJ_NEW_QSTR": "((mp_obj_t)((((mp_uint_t)({0})) << 3) | 2))", 
                "MP_OBJ_IS_IMMEDIATE_OBJ": "(((mp_int_t)({0})) & 7) == 6",
                "MP_OBJ_IMMEDIATE_OBJ_VALUE": "(((mp_uint_t)({0})) >> 3)",
                "MP_OBJ_NEW_IMMEDIATE_OBJ": "((mp_obj_t)((({0}) << 3) | 6))",
                "MP_OBJ_IS_OBJ": "(((mp_int_t)({0})) & 3) == 0",
                "MP_OBJ_TYPE_HAS_SLOT": "(((mp_obj_type_t *){0})->slot_index_{1})",
                "MP_OBJ_TYPE_GET_SLOT": "(_MP_OBJ_TYPE_SLOT_TYPE_{1}((mp_obj_type_t *){0})->slots[((mp_obj_type_t *){0})->slot_index_{1} - 1])",
            },
            self.REPR_B:{
                "MP_OBJ_FROM_PTR": "((mp_obj_t)({0}))",
                "MP_OBJ_TO_PTR": "((void *)({0}))",
                "MP_OBJ_IS_SMALL_INT": "(((mp_int_t)({0})) & 3) == 1",
                "MP_OBJ_SMALL_INT_VALUE": "(((mp_int_t)({0})) >> 2)",
                "MP_OBJ_NEW_SMALL_INT": "((mp_obj_t)((((mp_uint_t)({0})) << 2) | 1))",
                "MP_OBJ_IS_QSTR": "(((mp_int_t)({0})) & 7) == 3",
                "MP_OBJ_QSTR_VALUE": "(((mp_uint_t)({0})) >> 3)",
                "MP_OBJ_NEW_QSTR": "((mp_obj_t)((((mp_uint_t)({0})) << 3) | 3))", 
                "MP_OBJ_IS_IMMEDIATE_OBJ": "(((mp_int_t)({0})) & 7) == 7",
                "MP_OBJ_IMMEDIATE_OBJ_VALUE": "(((mp_uint_t)({0})) >> 3)",
                "MP_OBJ_NEW_IMMEDIATE_OBJ": "((mp_obj_t)((({0}) << 3) | 7))",
                "MP_OBJ_IS_OBJ": "(((mp_int_t)({0})) & 1) == 0",
                "MP_OBJ_TYPE_HAS_SLOT": "(((mp_obj_type_t *){0})->slot_index_{1})",
                "MP_OBJ_TYPE_GET_SLOT": "(_MP_OBJ_TYPE_SLOT_TYPE_{1}((mp_obj_type_t *){0})->slots[((mp_obj_type_t *){0})->slot_index_{1} - 1])",
            },
            self.REPR_C:{
                "MP_OBJ_FROM_PTR": "((mp_obj_t)({0}))",
                "MP_OBJ_TO_PTR": "((void *)({0}))",
                "MP_OBJ_IS_SMALL_INT": "(((mp_int_t)({0})) & 1) != 0",
                "MP_OBJ_SMALL_INT_VALUE": "(((mp_int_t)({0})) >> 1)",
                "MP_OBJ_NEW_SMALL_INT": "((mp_obj_t)((((mp_uint_t)({0})) << 1) | 1))",
                "MP_OBJ_IS_QSTR": "(((mp_uint_t)({0})) & 0xff80000f) == 0x00000006",
                "MP_OBJ_QSTR_VALUE": "(((mp_uint_t)({0})) >> 4)",
                "MP_OBJ_NEW_QSTR": "((mp_obj_t)((((mp_uint_t)({0})) << 4) | 0x00000006))", 
                "MP_OBJ_IS_IMMEDIATE_OBJ": "(((mp_uint_t)({0})) & 0xff80000f) == 0x0000000e",
                "MP_OBJ_IMMEDIATE_OBJ_VALUE": "(((mp_uint_t)({0})) >> 4)",
                "MP_OBJ_NEW_IMMEDIATE_OBJ": "((mp_obj_t)((({0}) << 4) | 0xe))",
                "MP_OBJ_IS_OBJ": "(((mp_int_t)({0})) & 3) == 0",
                "MP_OBJ_TYPE_HAS_SLOT": "(((mp_obj_type_t *){0})->slot_index_{1})",
                "MP_OBJ_TYPE_GET_SLOT": "(_MP_OBJ_TYPE_SLOT_TYPE_{1}((mp_obj_type_t *){0})->slots[((mp_obj_type_t *){0})->slot_index_{1} - 1])",
            },
            self.REPR_D:{
                "MP_OBJ_FROM_PTR": "((mp_obj_t)((uintptr_t)({0})))",
                "MP_OBJ_TO_PTR": " ((void *)(uintptr_t)({0}))",
                "MP_OBJ_IS_SMALL_INT": "(((uint64_t)({0})) & 0xffff000000000000) == 0x0001000000000000",
                "MP_OBJ_SMALL_INT_VALUE": "((mp_int_t)(({0}) << 16)) >> 17",
                "MP_OBJ_NEW_SMALL_INT": "(((((uint64_t)({0})) & 0x7fffffffffff) << 1) | 0x0001000000000001)",
                "MP_OBJ_IS_QSTR": "(((uint64_t)({0})) & 0xffff000000000000) == 0x0002000000000000",
                "MP_OBJ_QSTR_VALUE": "((((uint32_t)({0})) >> 1) & 0xffffffff)",
                "MP_OBJ_NEW_QSTR": "((mp_obj_t)(((uint64_t)(((uint32_t)({0})) << 1)) | 0x0002000000000001))", 
                "MP_OBJ_IS_IMMEDIATE_OBJ": "(((uint64_t)({0})) & 0xffff000000000000) == 0x0003000000000000",
                "MP_OBJ_IMMEDIATE_OBJ_VALUE": "((((uint32_t)({0})) >> 46) & 3)",
                "MP_OBJ_NEW_IMMEDIATE_OBJ": "(((uint64_t)({0}) << 46) | 0x0003000000000000)",
                "MP_OBJ_IS_OBJ": "(((uint64_t)({0})) & 0xffff000000000000) == 0x0000000000000000",
                "MP_OBJ_TYPE_HAS_SLOT": "(((mp_obj_type_t *){0})->slot_index_{1})",
                "MP_OBJ_TYPE_GET_SLOT": "(_MP_OBJ_TYPE_SLOT_TYPE_{1}((mp_obj_type_t *){0})->slots[((mp_obj_type_t *){0})->slot_index_{1} - 1])",
            },
        }
        return all_fallbacks[self.value]
obj_repr = ReprParameter("mpy repr")

class _MacroFuncLookup(_Lookup[Callable]):
    def _lookup(self, name: str) -> Callable:
        try:
            # validate that the macro exists before we return the curried function
            original = name+"(0)"
            expanded = _macro_expand(original)
            nargs = 1
        except gdb.error as e:
            msg: str = e.args[0]
            # Holotype: "Wrong number of arguments to macro `MICROPY_MAKE_VERSION' (expected 3, got 1)."
            if not msg.startswith("Wrong number of arguments to macro `"):
                raise e
            expanded = None
            nargs = int(msg.split(",")[0].split(" ")[-1])

        fallback_template = obj_repr._fallback_macro_templates()[name]

        if original == expanded: # valid but nonexistent macro name
            def f(*args):
                return _macro_eval_template(fallback_template, *args)
            
        else:
            def f(*args):
                if len(args) != nargs:
                    raise ValueError(f"{name} requires {nargs} arguments")
                try:
                    return _macro_call(name, *args)
                except gdb.error as e:
                    msg: str = e.args[0]
                    # Holotype: 'No symbol "mp_obj_is_small_int" in current context.'
                    if not msg.startswith("No symbol "):
                        raise e
                return _macro_eval_template(fallback_template, *args)
                
        f.__name__ = name
        return f

macro_fn = _MacroFuncLookup(strict=True, names=[
    # from mpconfig.h
    "MICROPY_MAKE_VERSION",
    "MICROPY_GC_HOOK_LOOP",
    "MICROPY_FLOAT_CONST",
    "MICROPY_FLOAT_C_FUN",
    "MICROPY_FLOAT_CONST",
    "MICROPY_FLOAT_C_FUN",
    "MICROPY_WRAP_MP_BINARY_OP",
    "MICROPY_WRAP_MP_EXECUTE_BYTECODE",
    "MICROPY_WRAP_MP_LOAD_GLOBAL",
    "MICROPY_WRAP_MP_LOAD_NAME",
    "MICROPY_WRAP_MP_MAP_LOOKUP",
    "MICROPY_WRAP_MP_OBJ_GET_TYPE",
    "MICROPY_WRAP_MP_SCHED_EXCEPTION",
    "MICROPY_WRAP_MP_SCHED_KEYBOARD_INTERRUPT",
    "MICROPY_WRAP_MP_SCHED_SCHEDULE",
    "MICROPY_WRAP_MP_SCHED_VM_ABORT",
    "MICROPY_MAKE_POINTER_CALLABLE",
    "MP_PLAT_ALLOC_EXEC",
    "MP_PLAT_FREE_EXEC",
    "MP_PLAT_ALLOC_HEAP",
    "MP_PLAT_FREE_HEAP",
    "MP_PLAT_PRINT_STRN",
    "MP_LIKELY",
    "MP_UNLIKELY",
    "MP_HTOBE16",
    "MP_BE16TOH",
    "MP_HTOBE16",
    "MP_BE16TOH",
    "MP_HTOBE32",
    "MP_BE32TOH",
    "MP_HTOBE32",
    "MP_BE32TOH",
    "MP_WARN_CAT",
    "MP_WARN_CAT",
    
    # from obj.h
    "MP_OBJ_SMALL_INT_VALUE",
    "MP_OBJ_NEW_SMALL_INT",
    "MP_OBJ_QSTR_VALUE",
    "MP_OBJ_NEW_QSTR",
    "MP_OBJ_IMMEDIATE_OBJ_VALUE",
    "MP_OBJ_NEW_IMMEDIATE_OBJ",
    "MP_OBJ_SMALL_INT_VALUE",
    "MP_OBJ_NEW_SMALL_INT",
    "MP_OBJ_QSTR_VALUE",
    "MP_OBJ_NEW_QSTR",
    "MP_OBJ_IMMEDIATE_OBJ_VALUE",
    "MP_OBJ_NEW_IMMEDIATE_OBJ",
    "MP_OBJ_SMALL_INT_VALUE",
    "MP_OBJ_NEW_SMALL_INT",
    "MP_OBJ_NEW_CONST_FLOAT",
    "MP_OBJ_QSTR_VALUE",
    "MP_OBJ_NEW_QSTR",
    "MP_OBJ_IMMEDIATE_OBJ_VALUE",
    "MP_OBJ_NEW_IMMEDIATE_OBJ",
    "MP_OBJ_SMALL_INT_VALUE",
    "MP_OBJ_NEW_SMALL_INT",
    "MP_OBJ_QSTR_VALUE",
    "MP_OBJ_NEW_QSTR",
    "MP_OBJ_IMMEDIATE_OBJ_VALUE",
    "MP_OBJ_NEW_IMMEDIATE_OBJ",
    "MP_OBJ_TO_PTR",
    "MP_OBJ_FROM_PTR",
    "MP_ROM_INT",
    "MP_ROM_QSTR",
    "MP_ROM_PTR",
    "MP_ROM_PTR",
    "MP_OBJ_TO_PTR",
    "MP_OBJ_FROM_PTR",
    "MP_ROM_INT",
    "MP_ROM_QSTR",
    "MP_ROM_PTR",
    "MP_ROM_INT",
    "MP_ROM_QSTR",
    "MP_ROM_PTR",
    "MP_DECLARE_CONST_FUN_OBJ_0",
    "MP_DECLARE_CONST_FUN_OBJ_1",
    "MP_DECLARE_CONST_FUN_OBJ_2",
    "MP_DECLARE_CONST_FUN_OBJ_3",
    "MP_DECLARE_CONST_FUN_OBJ_VAR",
    "MP_DECLARE_CONST_FUN_OBJ_VAR_BETWEEN",
    "MP_DECLARE_CONST_FUN_OBJ_KW",
    "MP_OBJ_FUN_MAKE_SIG",
    "MP_DEFINE_CONST_FUN_OBJ_0",
    "MP_DEFINE_CONST_FUN_OBJ_1",
    "MP_DEFINE_CONST_FUN_OBJ_2",
    "MP_DEFINE_CONST_FUN_OBJ_3",
    "MP_DEFINE_CONST_FUN_OBJ_VAR",
    "MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN",
    "MP_DEFINE_CONST_FUN_OBJ_KW",
    "MP_DEFINE_CONST_MAP",
    "MP_DEFINE_CONST_DICT_WITH_SIZE",
    "MP_DEFINE_CONST_DICT",
    "MP_DECLARE_CONST_STATICMETHOD_OBJ",
    "MP_DECLARE_CONST_CLASSMETHOD_OBJ",
    "MP_DEFINE_CONST_STATICMETHOD_OBJ",
    "MP_DEFINE_CONST_CLASSMETHOD_OBJ",
    "MP_REGISTER_MODULE",
    "MP_REGISTER_EXTENSIBLE_MODULE",
    "MP_REGISTER_MODULE_DELEGATION",
    "MP_REGISTER_ROOT_POINTER",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_0",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_1",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_2",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_3",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_4",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_5",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_6",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_7",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_8",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_9",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_10",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_11",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS_12",
    "MP_OBJ_TYPE_HAS_SLOT",
    "MP_OBJ_TYPE_GET_SLOT",
    "MP_OBJ_TYPE_GET_SLOT_OR_NULL",
    "MP_OBJ_TYPE_SET_SLOT",
    "MP_OBJ_TYPE_OFFSETOF_SLOT",
    "MP_OBJ_TYPE_HAS_SLOT_BY_OFFSET",
    "MP_DEFINE_CONST_OBJ_TYPE_EXPAND",
    "MP_DEFINE_CONST_OBJ_TYPE_NARGS",
    "MP_DEFINE_CONST_OBJ_TYPE",
    
    "MP_OBJ_IS_SMALL_INT",
    "MP_OBJ_IS_QSTR",
    "MP_OBJ_IS_OBJ",
    "MP_OBJ_IS_INT",
    "MP_OBJ_IS_TYPE",
    "MP_OBJ_IS_STR",
    "MP_OBJ_IS_STR_OR_BYTES",
    "MP_OBJ_IS_FUN",
    "MP_OBJ_IS_IMMEDIATE_OBJ",
    "MP_MAP_SLOT_IS_FILLED",
    "MP_SET_SLOT_IS_FILLED",
])



