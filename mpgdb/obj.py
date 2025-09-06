import warnings
import gdb
import logging
from . import file
from . import macro
from . import qstr
from . import type

log = logging.getLogger("mpgdb.obj")

NAMES = dict.fromkeys([ # mp_obj_{}
    'module_t',
    'dict_t',
    'fun_bc_t',
    'base_t',
    'full_type_t',
    'list_t',
    'factorial_t',
    'type_t',
    'usb_device_t',
    'task_t',
    'task_queue_t',
    'iter_buf_t',
    'array_t',
    'bluetooth_uuid_t',
    'bluetooth_ble_t',
    'tuple_t',
    'new_t',
    'btree_t',
    'aes_t',
    'deflateio_read_t',
    'deflateio_write_t',
    'deflateio_t',
    'framebuf_t',
    'cast_t',
    'hash_t',
    'is_t',
    'stringio_t',
    'code_t',
    're_t',
    'match_t',
    'get_t',
    'poll_t',
    'ssl_context_t',
    'ssl_socket_t',
    'str_t',
    'uctypes_struct_t',
    'get_int_t',
    'webrepl_t',
    'websocket_t',
    'fat_vfs_t',
    'vfs_lfs1_t',
    'vfs_lfs1_file_t',
    'vfs_lfs2_t',
    'vfs_lfs2_file_t',
    'vfs_posix_file_t',
    'vfs_posix_t',
    'listdir_t',
    'vfs_rom_file_t',
    'vfs_rom_t',
    'new_str_of_t',
    'float_t',
    'complex_t',
    'int_t',
    'streamtest_t',
    'fun_builtin_fixed_t',
    'opaque_t',
    'ffimod_t',
    'ffivar_t',
    'ffifunc_t',
    'fficallback_t',
    'jclass_t',
    'jobject_t',
    'jmethod_t',
    'fdfile_t',
    'socket_t',
    'jsproxy_t',
    'exception_t',
    'fun_builtin_var_t',
    'sensor_t',
    'instance_t',
    'bufwriter_t',
    'thread_lock_t',
    'empty_type_t',
    'is_exact_t',
    'cell_t',
    'slice_t',
    'static_class_method_t',
    'array_it_t',
    'bool_t',
    'bound_meth_t',
    'closure_t',
    'colines_iter_t',
    'deque_t',
    'deque_it_t',
    'dict_view_it_t',
    'dict_view_t',
    'enumerate_t',
    'exception_clear_t',
    'exception_add_t',
    'exception_get_t',
    'filter_t',
    'fun_asm_t',
    'gen_instance_t',
    'gen_instance_native_t',
    'getitem_iter_t',
    'list_it_t',
    'map_t',
    'namedtuple_type_t',
    'namedtuple_t',
    'new_namedtuple_t',
    'none_t',
    'object_t',
    'is_instance_t',
    'polymorph_iter_t',
    'polymorph_iter_with_finaliser_t',
    'polymorph_with_finaliser_iter_t',
    'property_t',
    'range_it_t',
    'range_t',
    'reversed_t',
    'set_t',
    'set_it_t',
    'singleton_t',
    'new_str_t',
    'str8_it_t',
    'str_it_t',
    'tuple_it_t',
    'super_t',
    'zip_t',
    'frame_t',
    'checked_fun_t'
])

def _lookup(name: str) -> gdb.Type:
    fullname = "mp_obj_{}".format(name)
    symbol = file.micropython.lookup_static_symbol(fullname, gdb.SYMBOL_TYPE_DOMAIN)
    return symbol.type.pointer()

def __getattr__(name: str) -> gdb.Type:
    symbol = NAMES.get(name, None)
    if symbol is not None:
        return symbol
    
    symbol = _lookup(name)
    if symbol is not None:
        NAMES[name] = symbol
        return symbol
    
    if name in NAMES:
        del NAMES[name]

    raise AttributeError(f"Can't find mp_obj_{name}.", name=name)
    
def __dir__() -> list[str]:
    return list(NAMES)

obj_t = file.micropython.lookup_static_symbol('mp_obj_t', gdb.SYMBOL_TYPE_DOMAIN).type
const_obj_t = file.micropython.lookup_static_symbol('mp_const_obj_t', gdb.SYMBOL_TYPE_DOMAIN).type
rom_obj_t = file.micropython.lookup_static_symbol('mp_rom_obj_t', gdb.SYMBOL_TYPE_DOMAIN).type

def is_obj(o: gdb.Value) -> bool:
    return o.type.name in [obj_t.name, const_obj_t.name, rom_obj_t.name]

def decode_const_obj(o: gdb.Value) -> str|None:
    if is_obj(o):
        i = int(o)
        if i == macro.OBJ_NULL:
            return "null"
        if i == macro.OBJ_STOP_ITERATION:
            return "StopIteration"
        if i == macro.OBJ_SENTINEL:
            return "sentinel"
        if i == macro.ROM_NONE:
            return "None"
        if i == macro.ROM_FALSE:
            return "False"
        if i == macro.ROM_TRUE:
            return "True"

def decode_immediate_obj(o: gdb.Value) -> int|None:
    if is_obj(o) and macro.OBJ_IS_IMMEDIATE_OBJ(o):  # only valid for REPR_A
        return macro.OBJ_IMMEDIATE_OBJ_VALUE(o)

def decode_smallint_obj(o: gdb.Value) -> int|None:
    if is_obj(o) and macro.OBJ_IS_SMALL_INT(o):  # only valid for REPR_A
        return macro.OBJ_SMALL_INT_VALUE(o)
    
def decode_object_obj(o: gdb.Value) -> int|None:
    if is_obj(o) and macro.OBJ_IS_OBJ(o):  # only valid for REPR_A
        return macro.OBJ_TO_PTR(o).cast(_lookup('object_t'))


class ObjConstPrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        return self.__value

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_const_obj(value)
            if decoded is not None:
                return cls(decoded)
            else:
                return None
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e


class ObjImmediatePrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        return f"imm({self.__value})"

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_immediate_obj(value)
            if decoded is not None:
                return cls(decoded)
            else:
                return None
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

class ObjSmallIntPrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        return self.__value

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_smallint_obj(value)
            if decoded is not None:
                return cls(decoded)
            else:
                return None
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

class ObjObjPrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        try:
            return self.__value.address.format_string(raw=True)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def children(self):
        try:
            for field in  self.__value.type.fields():
                yield (field.name, self.__value[field])
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_object_obj(value)
            if decoded is None:
                return None
                    
            for type_name in type.NAMES:
                type_obj = getattr(type, type_name, None)
                if type_obj is None:
                    continue
                if type_obj != decoded["base"]["type"]:
                    continue
                    
                typedef = _lookup(type_name+"_t")

                decoded = decoded.cast(typedef)
                
            return cls(decoded.dereference())
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

POSSIBLE_SLOTS = [
    "make_new",
    "print",
    "call",
    "unary_op",
    "binary_op",
    "attr",
    "subscr",
    "iter",
    "buffer",
    "protocol",
    "parent",
    "locals_dict",
]

class ObjBasePrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value = value

    def to_string(self):
        try:
            return qstr.lookup(self.__value['type']['name']).string()
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    
    def children(self):
        try:
            yield ("type", self.__value['type'])
            yield ("name", self.__value['type']['name'].cast(qstr.qstr_short_t))
            for slot in POSSIBLE_SLOTS:
                if macro.OBJ_TYPE_HAS_SLOT(self.__value['type'], slot):
                    yield (slot, macro.OBJ_TYPE_GET_SLOT(self.__value['type'], slot))
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

    @classmethod
    def lookup(cls, value):
        if value.type == _lookup("base_t").target():
            return cls(value)
        else:
            return None
        
file.micropython.pretty_printers.append(ObjConstPrinter.lookup)
log.info("Registered pretty printer: %s", ObjConstPrinter.__name__)
file.micropython.pretty_printers.append(ObjImmediatePrinter.lookup)
log.info("Registered pretty printer: %s", ObjImmediatePrinter.__name__)
file.micropython.pretty_printers.append(ObjSmallIntPrinter.lookup)
log.info("Registered pretty printer: %s", ObjSmallIntPrinter.__name__)
file.micropython.pretty_printers.append(ObjObjPrinter.lookup)
log.info("Registered pretty printer: %s", ObjObjPrinter.__name__)
gdb.current_objfile().pretty_printers.append(ObjBasePrinter.lookup)
log.info("Registered pretty printer: %s", ObjBasePrinter.__name__)
