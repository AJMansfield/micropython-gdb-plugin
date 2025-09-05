import warnings
import gdb
from . import file

NAMES = dict.fromkeys([ # struct _mp_obj_{}
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

def _lookup(name: str) -> gdb.Symbol:
    fullname = "_mp_obj_{}".format(name)
    symbol = file.micropython.lookup_static_symbol(fullname, gdb.SYMBOL_STRUCT_DOMAIN)
    return symbol.type

def __getattr__(name: str) -> gdb.Symbol:
    symbol = NAMES.get(name, None)
    if symbol is not None:
        return symbol
    
    symbol = _lookup(name)
    if symbol is not None:
        NAMES[name] = symbol
        return symbol
    
    if name in NAMES:
        del NAMES[name]

    raise AttributeError(f"Can't find struct _mp_obj_{name}.", name=name)
    
def __dir__() -> list[str]:
    return list(NAMES)
