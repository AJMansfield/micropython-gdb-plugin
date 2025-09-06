from __future__ import annotations
import logging, sys, os, importlib, enum, functools, re
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("gdb.micropython")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    sys.path.append('/usr/local/share/gdb/python')
    import gdb

try:
    if TYPE_CHECKING:
        import mpy_tool
    else:
        if "mpy-tool" not in sys.modules:
            mpy_tools_folder = os.path.normpath(os.path.join(gdb.current_objfile().filename, "..", "..", "..", "..", "tools"))
            log.info("Importing mpy-tool from %s.", mpy_tools_folder)

            sys.modules["makeqstrdata"]={}
            sys.path.append(mpy_tools_folder)
            mpy_tool = importlib.import_module("mpy-tool")
        mpy_tool = sys.modules["mpy-tool"]
    log.info("Imported mpy-tool.")
    has_mpy_tool = True
except ImportError:
    log.warning("Cannot import mpy-tool. Disassembly will be unavailable.")
    has_mpy_tool = False

try:
    import pydot
    has_pydot = True
except ImportError:
    log.warning("Cannot import pydot. Heap graph output will be unavailable.")
    has_pydot = False


try:
    import mpgdb as mp
except Exception as e:
    log.exception("%r", e, exc_info=True, stack_info=True)
    raise e

log.info("Loaded mpgdb")


class Mpy(gdb.Command):
    """Examine MicroPython interpreter state."""
    def __init__(self):
        super(Mpy, self).__init__("mpy", gdb.COMMAND_USER, gdb.COMPLETE_COMMAND, True)
        log.info("Registered group: mpy")
Mpy()

def get_pystate(frame):
    try:
        return frame.read_var("code_state")
    except ValueError:
        return get_pystate(frame.older())
    except AttributeError:
        return None
        
class MpyState(gdb.Command):
    """Show the MicroPython stack.
    Usage: mpy state
    """
    def __init__(self):
        super(MpyState, self).__init__("mpy state", gdb.COMMAND_STACK, gdb.COMPLETE_NONE)
        log.info("Registered command: mpy state")
    
    def invoke(self, args, from_tty):
        frame = gdb.selected_frame()
        code_state = get_pystate(frame)
        n_state = int(code_state["n_state"])
        state = code_state["state"]
        for i in range(n_state):
            print(get_pyobj_str(state[i]))
MpyState()


def get_pyobj_str(value) -> str:
    if int(value) & 1:
        return str(int(value) >> 1)
    if (int(value) & 7) == 2:
        qstr = mp.qstr.get(int(value) >> 3)
        if qstr:
            return "'" + qstr + "'"
    if int(value) == 0:
        return "None"
    objtype = value.cast(mp.obj.base_t)["type"]
    if int(objtype) == int(mp.obj.dict_t):
        dic = value.cast(mp.obj.dict_t)
        vals = int(dic["map"]["alloc"])
        strs = ""
        for i in range(vals):
            entry = dic["map"]["table"][i]
            strs += get_pyobj_str(entry["key"]) + ": " + get_pyobj_str(entry["value"]) + ",\n "
        return "dict: {" + strs + "}"
    if int(objtype) == int(mp.type.module) and False:
        print("module")
        dic = value.cast(mp.obj.module_t)
        print(dic)
        return "module(" + get_pyobj_str(dic["globals"]) + ")"
    obj = str(objtype).split(" ")
    if len(obj) == 1:
        obj = obj[0]
    else:
        obj = obj[1]
    return "object(" + hex(value) + ") " + obj

class MpyObj(gdb.Command):
    """Pretty-print a MicroPython object.
    Usage: mpy obj VALUE
    """
    def __init__(self):
        super(MpyObj, self).__init__("mpy obj", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)
        log.info("Registered command: mpy obj")

    def complete(self, text, word):
        return gdb.COMPLETE_NONE

    def invoke(self, args, from_tty):
        print(get_pyobj_str(gdb.parse_and_eval(args)))
MpyObj()




def get_pydis(bc):
    sig = MPY_BC_Sig()
    sig.load(bc, 0)
    sig.print()
    mpy_disassemble(bc, sig.end, None)

class MpyDis(gdb.Command):
    """Dissasemble MicroPython bytecode.
    Usage: mpy dis VALUE
    """
    def __init__(self):
        super(MpyDis, self).__init__("mpy dis", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)
        log.info("Registered command: mpy dis")

    def invoke(self, args, from_tty):
        value = gdb.parse_and_eval(args)
        objtype = value.cast(mp.obj.base_t)["type"]
        if int(objtype) == int(mp.type.fun_bc):
            get_pydis(value.cast(mp.obj.fun_bc_t))

if has_mpy_tool:
    MpyDis()


def mpy_disassemble(fun_bc, ptr, current_ptr):
    Opcode = mpy_tool.Opcode

    bc = fun_bc["bytecode"]
    qstr_table = fun_bc["context"]["constants"]["qstr_table"]
    obj_table = fun_bc["context"]["constants"]["obj_table"]
    biggest_jump = 0
    instructions = []
    offsets = []
    labels = dict()
    ip = ptr
    while True:
        offsets.append(ptr)
        op = int(bc[ip])
        fmt, sz, arg, _ = mpy_tool.mp_opcode_decode(bc, ip)
        if (bc[ip] & 0xf0) == Opcode.MP_BC_BASE_JUMP_E:
            biggest_jump = max(biggest_jump, ip + arg)
        if bc[ip] == Opcode.MP_BC_LOAD_CONST_OBJ:
            arg = get_pyobj_str(obj_table[arg])
            pass
        if fmt == mpy_tool.MP_BC_FORMAT_QSTR:
            arg = mp.qstr.get(qstr_table[arg]).string()
        elif fmt in (mpy_tool.MP_BC_FORMAT_VAR_UINT, mpy_tool.MP_BC_FORMAT_OFFSET):
            pass
        else:
            arg = ""
        print(
            "  %04x %s %s" % (ip - ptr, Opcode.mapping[bc[ip]], arg)
        )
        if bc[ip] == Opcode.MP_BC_RETURN_VALUE:
            if biggest_jump < ip:
                break
        ip += sz
        #self.disassemble_children()

# bytecode layout:
#
#  func signature  : var uint
#      contains six values interleaved bit-wise as: xSSSSEAA [xFSSKAED repeated]
#          x = extension           another byte follows
#          S = n_state - 1         number of entries in Python value stack
#          E = n_exc_stack         number of entries in exception stack
#          F = scope_flags         four bits of flags, MP_SCOPE_FLAG_xxx
#          A = n_pos_args          number of arguments this function takes
#          K = n_kwonly_args       number of keyword-only arguments this function takes
#          D = n_def_pos_args      number of default positional arguments
#
#  prelude size    : var uint
#      contains two values interleaved bit-wise as: xIIIIIIC repeated
#          x = extension           another byte follows
#          I = n_info              number of bytes in source info section (always > 0)
#          C = n_cells             number of bytes/cells in closure section
#
#  source info section:
#      simple_name : var qstr      always exists
#      argname0    : var qstr
#      ...         : var qstr
#      argnameN    : var qstr      N = num_pos_args + num_kwonly_args - 1
#      <line number info>
#
#  closure section:
#      local_num0  : byte
#      ...         : byte
#      local_numN  : byte          N = n_cells-1
#
#  <bytecode>                   // bytecode layout:
class MPY_BC_Sig:
    def __init__(self):
        pass

    def load(self, fun_bc, ip):
        bytecode = fun_bc["bytecode"]
        qstr_table = fun_bc["context"]["constants"]["qstr_table"]
        sig = mpy_tool.extract_prelude(bytecode, ip)
        (self.S, self.E, self.F, self.A, self.K, self.D) = sig[5]
        (self.I, self.C) = sig[6]
        self.end = sig[4]
        self.lines = []
        print(qstr_table[0])
        self.function_name = MpyQstr.mp.qstr.get(qstr_table[sig[7][0]]).string()
        self.args = [mp.qstr.get(qstr_table[int(i)]).string() for i in sig[7][1:]]
        self.source = get_qstr(qstr_table[0])
            
        #now 1 qstr function name
        #now A + K strings, args
        source_line = 1
        ptr = sig[2]
        while ptr < sig[3]:
            c = int(bytecode[ptr])
            b = 0
            l = 0
            if (c & 0x80) == 0:
                # 0b0LLBBBBB encoding
                b = c & 0x1f
                l = c >> 5
                ptr += 1
            else:
                # 0b1LLLBBBB 0bLLLLLLLL encoding (l's LSB in second byte)
                b = c & 0xf
                l = ((c << 4) & 0x700) | int(bytecode[ptr + 1])
                ptr += 2
            self.lines.append((l,b))

    def set_val(self, S, E, F, A, K, D, C, I):
        self.S = S
        self.E = E
        self.F = F
        self.A = A
        self.K = K
        self.D = D
        self.C = C
        self.I = I

    def map_line(self, ip):
        line = 1
        for (l, b) in self.lines:
            if b > ip:
                break
            line += l
            ip -= b
        return line

    def print(self):
        print("state: " + str(self.S) + ", exc: " + str(self.E) + ", scope: " + str(self.F) + ", pos_args: " + str(self.A) + ", kwonly_args: " + str(self.K) + ", def_args: " + str(self.D) + ", info: " + str(self.I) + ", cells: " + str(self.C))


class InlinedFrameDecorator(gdb.FrameDecorator.FrameDecorator):

    def __init__(self, fobj):
        super(InlinedFrameDecorator, self).__init__(fobj)
        self.elided_frames = []
        frame = self.inferior_frame()
        self.sig = MPY_BC_Sig()
        self.sig.load(frame.read_var("code_state")["fun_bc"], 0)

    def function(self):
        frame = self.inferior_frame()
        state = frame.read_var("code_state")["state"]
        name = self.sig.function_name
        narg = 0
        if len(self.sig.args) != 0:
            name += "("
            for arg in self.sig.args:
                name += arg + "=" + str(get_pyobj_str(state[self.sig.S - 1 - narg])) + ","
                narg += 1
            name = name[:-1]+")"
        return name


    #def elided(self):
    #    return self.elided_frames

    def filename(self):
        return self.sig.source

    def line(self):
        frame = self.inferior_frame()
        ip = int(frame.read_var("code_state")["ip"]) - int(frame.read_var("code_state")["fun_bc"]["bytecode"][0].address)
        return self.sig.map_line(ip)

def decorate(frames):
    try:
        while True:
            frame = next(frames)
            if frame.inferior_frame().name() == "mp_execute_bytecode":
                out = InlinedFrameDecorator(frame)
                frame = next(frames)
                if frame.inferior_frame().name() == "fun_bc_call":
                    out.elided_frames.append(frame)
                    frame = next(frames)
                    if frame.inferior_frame().name() == "mp_call_function_n_kw":
                        out.elided_frames.append(frame)
                        frame = None
                yield out
                if frame is not None:
                    yield frame
            else:
                yield frame
    except StopIteration:
        pass
    
class FrameFilter():
    def __init__(self):
        self.name = "mpy_frame"
        self.priority = 100
        self.enabled = True

        # Register this frame filter with the global frame_filters
        # dictionary.
        gdb.frame_filters[self.name] = self
        
        log.info("Registered frame filter: %s", self.name)

    def filter(self, frame_iter):
        return iter(decorate(frame_iter))
    
if has_mpy_tool:
    FrameFilter()


# class MpyMem(gdb.Command):
#     """Examine MicroPython heap memory state."""
#     def __init__(self):
#         super(Mpy, self).__init__("mpy mem", gdb.COMMAND_USER, gdb.COMPLETE_COMMAND, True)
#         log.info("Registered group: mpy mem")
# MpyMem()

class MpyGcDumpInfo(gdb.Command):
    """Dump the garbage collector's statistics.
    Usage: mpy mem dump_info
    """
    def __init__(self):
        super(MpyGcDumpInfo, self).__init__("mpy gc_dump_info", gdb.COMMAND_DATA, gdb.COMPLETE_NONE)
        log.info("Registered command: mpy gc_dump_info")

    def invoke(self, args, from_tty):
        print(gdb.execute("call gc_dump_info(&mp_plat_print)", False, True))
        # return gdb.execute("call gc_dump_info(&mp_sys_stdout_print)", False, True)
MpyGcDumpInfo()
    
class MpyGcDumpAllocTable(gdb.Command):
    """Dump the garbage collector's allocation table.
    Usage: mpy mem dump_alloc_table
    """
    def __init__(self):
        super(MpyGcDumpAllocTable, self).__init__("mpy gc_dump_alloc_table", gdb.COMMAND_DATA, gdb.COMPLETE_NONE)
        log.info("Registered command: mpy gc_dump_alloc_table")

    def invoke(self, args, from_tty):
        print(gdb.execute("call gc_dump_alloc_table(&mp_plat_print)", False, True))
        # return gdb.execute("call gc_dump_alloc_table(&mp_sys_stdout_print)", False, True)
MpyGcDumpAllocTable()


def all_heap_areas(mem_state):
    heap_area = mem_state["area"]
    while heap_area:
        yield heap_area
        try:
            heap_area = heap_area["next"]
        except gdb.error:
            return
        
class BlockTable:
    def __init_subclass__(cls, blocks_per_byte:int=4, table_name:str="gc_alloc_table_start"):
        cls.blocks_per_byte = blocks_per_byte
        cls.bits_per_block = 8 // cls.blocks_per_byte
        cls.block_mask = ~(-1 << cls.bits_per_block)
        cls.table_name = table_name
    @classmethod
    def lookup(cls, area, block:int):
        index, shift = divmod(block, cls.blocks_per_byte)
        shift *= cls.bits_per_block
        mask = cls.block_mask
        return int(area[cls.table_name][index]) >> shift & mask

class ATB(BlockTable, enum.IntEnum, blocks_per_byte=4, table_name="gc_alloc_table_start"):
    FREE = 0
    HEAD = 1
    TAIL = 2
    MARK = 3

class FTB(BlockTable, enum.IntEnum, blocks_per_byte=8, table_name="gc_finaliser_table_start"):
    CLEAR = 0
    SET = 1


# ATB_BLOCKS_PER_BYTE = 4
# ATB_BITS_PER_BLOCK = 8 // ATB_BLOCKS_PER_BYTE
# ATB_BLOCK_MASK = (1<<ATB_BITS_PER_BLOCK) - 1
# def atb_coordinates(block:int) -> tuple[int,int,int]:
#     index, shift = divmod(block, ATB_BLOCKS_PER_BYTE)
#     shift *= ATB_BITS_PER_BLOCK
#     return index, shift, ATB_BLOCK_MASK
# def atb_get(area, block:int) -> ATB:
#     index, shift, mask = atb_coordinates(block)
#     numeric_kind = int(area["gc_alloc_table_start"][index]) >> shift & mask
#     return ATB(numeric_kind)

# FTB_BLOCKS_PER_BYTE = 8
# FTB_BITS_PER_BLOCK = 8 // FTB_BLOCKS_PER_BYTE
# FTB_BLOCK_MASK = (1<<FTB_BITS_PER_BLOCK) - 1
# def ftb_coordinates(block:int) -> tuple[int,int,int]:
#     index, shift = divmod(block, ATB_BLOCKS_PER_BYTE)
#     shift *= ATB_BITS_PER_BLOCK
#     return index, shift, ATB_BLOCK_MASK
# def ftb_get_has_finaliser(area, block:int):
#     (area["gc_finaliser_table_start"][(block) // BLOCKS_PER_FTB] >> ((block) & 7)) & 1

BYTES_PER_WORD = 4
BYTES_PER_BLOCK = 4 * BYTES_PER_WORD
WORDS_PER_BLOCK = BYTES_PER_BLOCK // BYTES_PER_WORD

def block_from_ptr(area, ptr):
    return (int(ptr) - int(area["gc_pool_start"])) // BYTES_PER_BLOCK
def ptr_from_block(area, block):
    return area["gc_pool_start"][block * BYTES_PER_BLOCK].address
def get_ptr_area(mem_state, ptr, aligned=True) -> tuple[int,Any]:
    ptr = int(ptr)
    if aligned:
        if ptr & (BYTES_PER_BLOCK - 1) != 0:
            return None # must be aligned on a block
    for area_num, heap_area in enumerate(all_heap_areas(mem_state)):
        start = int(heap_area["gc_pool_start"])
        end = int(heap_area["gc_pool_end"])
        if start <= ptr and ptr < end:
            return area_num, heap_area
    else:
        return None

def get_previous_head(area, block):
    orig_block = block
    while block >= 0:
        kind = ATB.lookup(area, block)
        if kind == ATB.FREE:
            return orig_block
        elif kind == ATB.TAIL:
            block -= 1
        else: #if kind in {ATB.HEAD, ATB.MARK}:
            return block
    else:
        return orig_block
    
def enumerate_ptrs_in_block(mem_state, area, block):
    for i in range(WORDS_PER_BLOCK):
        src_ptr = area["gc_pool_start"][block*BYTES_PER_BLOCK + i*BYTES_PER_WORD].address
        dst_ptr = src_ptr.cast(gdb.lookup_type("uintptr_t").pointer())[0]
        if get_ptr_area(mem_state, dst_ptr, aligned=True):
            yield (i, src_ptr, dst_ptr)

def heap_stats_node(mem_state):
    entries = []
    for stat in ["total_bytes_allocated", "current_bytes_allocated", "peak_bytes_allocated"]:
        stat_short = stat.removesuffix("_bytes_allocated")
        value = int(mem_state[stat])
        entries.append(f"<dt>{stat_short}</dt><dd>{value}</dd>")
    label = "<<dl>" + "".join(entries) + "</dl>>"
    return pydot.Node("stats", shape="plaintext", label=label)

def get_immediate(ptr) -> str|None:
    if int(ptr) & 1:
        return f"mp_int({str(int(ptr) >> 1)})"
    elif (int(ptr) & 7) == 2:
        qstr = get_qstr(int(ptr) >> 3)
        if qstr:
            return f"mp_qstr({qstr!r})"
        else:
            return None
    elif int(ptr) == 0:
        return "MP_OBJ_NULL"
    elif int(ptr) == 4:
        return "MP_OBJ_STOP_ITERATION"
    elif int(ptr) == 8:
        return "MP_OBJ_SENTINEL"
    elif int(ptr)>>3 == 0:
        return "mp_const_none"
    elif int(ptr)>>3 == 1:
        return "mp_const_false"
    elif int(ptr)>>3 == 3:
        return "mp_const_true"
    else:
        return None
    
def get_heap_type(ptr) -> str|None:
    value = get_immediate(ptr)
    if value is not None:
        return value
    
    objtype = ptr.cast(mp.obj.base_t)["type"]
    for typename in mp.type.NAMES:
        try:
            mptype = mp.type._lookup(typename)
        except KeyError:
            continue
        if int(objtype) == int(mptype):
            return typename
    return None

def get_block_anchor(area_num, block):
    return f"<a{area_num}.b{block}>"
def get_node_name(ptr):
    return f"{int(ptr):#08x}"

def get_pointer_edge_ref(mem_state, ptr, heap_only=False):
    ptr_area = get_ptr_area(mem_state, ptr, False)
    if ptr_area:
        area_num, area = ptr_area
        block = block_from_ptr(area, ptr)
        head_block = get_previous_head(area, block)
        head_ptr = ptr_from_block(area, head_block)
        return f"{int(head_ptr):#08x}:a{area_num}.b{block}"
    elif not heap_only:
        return f"{int(ptr):#08x}"
    else:
        return None

def add_heap_ptr(dot_graph:pydot.Graph, mem_state, src_ref:str, dst_ptr, heap_only=False):
    if int(dst_ptr) == 0:
        # dst_ref = "null_" + src_ref.split(":")[0]
        # dot_graph.add_node(pydot.Node(dst_ref, shape="plaintext", label="null"))
        return False
    else:
        dst_ref = get_pointer_edge_ref(mem_state, dst_ptr, heap_only=heap_only)
    if dst_ref is not None:
        dot_graph.add_edge(pydot.Edge(src_ref, dst_ref))
        return True
    else:
        return False

def add_mem_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state):
    sub_nodes = pydot.Subgraph("heap", cluster=True, color="blue", label="heap")
    nodes.add_subgraph(sub_nodes)

    for area_num, area in enumerate(all_heap_areas(mem_state)):

        atb_len = int(area["gc_alloc_table_byte_len"])
        block_count = atb_len * ATB.blocks_per_byte

        head_ptr = None
        node_lines = None

        for block in range(block_count):
            ptr = ptr_from_block(area, block)
            kind = ATB.lookup(area, block)

            if kind in {ATB.HEAD, ATB.MARK, ATB.FREE}: # chain ends, write out current and clear
                if head_ptr is not None:
                    head_block = block_from_ptr(area, head_ptr)
                    head_kind = ATB.lookup(area, head_block)
                    head_final = FTB.lookup(area, head_block)
                    
                    fillcolor = {
                        ATB.FREE: "gray",
                        ATB.HEAD: "aliceblue",
                        ATB.TAIL: "lightgray",
                        ATB.MARK: "lightcoral",
                    }[head_kind]
                    style = '"filled,dashed"' if head_final == FTB.SET else "filled"

                    node = pydot.Node(
                        get_node_name(head_ptr),
                        label='"' + "|".join(node_lines) + '"',
                        shape="record", style=style, fillcolor=fillcolor,
                        sortv=int(head_ptr),
                    )
                    sub_nodes.add_node(node)
                head_ptr = None
                node_lines = None
            
            if kind in {ATB.HEAD, ATB.MARK, ATB.TAIL}: # add to chain
                anchor = get_block_anchor(area_num, block)
                if head_ptr is None:
                    head_ptr = ptr
                    node_lines = []
                    name = get_node_name(ptr)
                    obj = get_heap_type(ptr)
                    if obj:
                        line = f"{anchor}{name}\\n{obj}"
                    else:
                        line = f"{anchor}{name}"
                else:
                    line = anchor
                node_lines.append(line)

                # add all pointers in the block
                for i, src_ptr, dst_ptr in enumerate_ptrs_in_block(mem_state, area, block):
                    src_name = get_pointer_edge_ref(mem_state, src_ptr)
                    # src_name = f"{int(head_ptr):#08x}:a{area_num}.b{block}"
                    dst_name = get_pointer_edge_ref(mem_state, dst_ptr)
                    edges.add_edge(pydot.Edge(src_name, dst_name))

def struct_get_checked(parent_struct, name, unless_disabled=None):
    try:
        return parent_struct[name]
    except gdb.error as e:
        if unless_disabled:
            log.warning("%s is disabled, skipping %s", unless_disabled, name)
            return None
        else:
            raise e

def add_ptr_block(edges:pydot.Graph, nodes:pydot.Graph, mem_state, parent_struct, name:str, unless_disabled=None):
    ptr = struct_get_checked(parent_struct, name, unless_disabled)
    if ptr is None:
        return
    nodes.add_node(pydot.Node(name, shape="record"))
    add_heap_ptr(edges, mem_state, name, ptr)

def add_array_block(edges:pydot.Graph, nodes:pydot.Graph, mem_state, parent_struct, name:str, unless_disabled=None):
    arr = struct_get_checked(parent_struct, name, unless_disabled)
    if arr is None:
        return
    arr_size = arr.type.sizeof // arr[0].type.sizeof
    lines = []
    for i in range(arr_size):
        lines.append(f"<i{i}>")
        add_heap_ptr(edges, mem_state, f"{name}:i{i}", arr[i])
    lines[0] = f"{lines[0]}{name}"
    node = pydot.Node(
        name,
        label='"' + "|".join(lines) + '"',
        shape="record",
    )
    nodes.add_node(node)

def add_ptr_or_array_block(edges:pydot.Graph, nodes:pydot.Graph, mem_state, parent_struct, name:str, unless_disabled=None):
    value = struct_get_checked(parent_struct, name, unless_disabled)
    if value is None:
        return
    if value.type.strip_typedefs().code == gdb.TYPE_CODE_PTR:
        add_ptr_block(edges, nodes, mem_state, parent_struct, name)
    else:
        add_array_block(edges, nodes, mem_state, parent_struct, name)

def add_substruct_block(edges:pydot.Graph, nodes:pydot.Graph, mem_state, parent_struct, name:str, unless_disabled=None):
    obj = struct_get_checked(parent_struct, name, unless_disabled)
    if obj is None:
        return
    lines = []

    obj_type = get_heap_type(obj.address)

    for i, f in enumerate(obj.type.fields()):
        line_anchor= f"<{f.name}>"
        line_lines = []
        if i == 0:
            line_lines.append(name)

        if i == 0 and obj_type:
            line_lines.append(obj_type)
        elif f.artificial or f.name == None:
            log.warning("field %r omitted", f)
        else:
            value = obj[f.name]

            if f.type.strip_typedefs().code == gdb.TYPE_CODE_PTR:
                add_heap_ptr(edges, mem_state, f"{name}:{f.name}", value)
                line_lines.append(f"*{f.name}")
            else:
                line_lines.append(f"{f.name} = {value!s}")
        lines.append(line_anchor + '\\n'.join(line_lines))
    
    node = pydot.Node(
        name,
        label='"' + "|".join(lines) + '"',
        shape="record",
    )
    nodes.add_node(node)

def add_thread_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state, thread_state):
    sub_nodes = pydot.Subgraph("thread", cluster=True, color="green", label="thread")
    nodes.add_subgraph(sub_nodes)

    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "dict_locals")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "dict_globals")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "nlr_top")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "nlr_jump_callback_top")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "mp_pending_exception")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "stop_iteration_arg")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "prof_trace_callback", unless_disabled="MICROPY_PY_SYS_SETTRACE")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "current_code_state", unless_disabled="MICROPY_PY_SYS_SETTRACE")
    add_ptr_block(edges, sub_nodes, mem_state, thread_state, "tls_ssl_context", unless_disabled="MICROPY_PY_SSL_MBEDTLS_NEED_ACTIVE_CONTEXT")

def add_vm_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state, vm_state):
    sub_nodes = pydot.Subgraph("vm", cluster=True, color="red", label="vm")
    nodes.add_subgraph(sub_nodes)

    add_ptr_block(edges, sub_nodes, mem_state, vm_state, "last_pool")
    add_ptr_block(edges, sub_nodes, mem_state, vm_state, "m_tracked_head", unless_disabled="MICROPY_TRACKED_ALLOC")
    add_substruct_block(edges, sub_nodes, mem_state, vm_state, "mp_emergency_exception_obj")
    add_ptr_or_array_block(edges, sub_nodes, mem_state, vm_state, "mp_emergency_exception_buf", unless_disabled="MICROPY_ENABLE_EMERGENCY_EXCEPTION_BUF")
    add_substruct_block(edges, sub_nodes, mem_state, vm_state, "mp_kbd_exception", unless_disabled="MICROPY_KBD_EXCEPTION")
    add_substruct_block(edges, sub_nodes, mem_state, vm_state, "mp_loaded_modules_dict")
    add_substruct_block(edges, sub_nodes, mem_state, vm_state, "dict_main")
    add_ptr_block(edges, sub_nodes, mem_state, vm_state, "mp_module_builtins_override_dict", unless_disabled="MICROPY_CAN_OVERRIDE_BUILTINS")

    add_registered_blocks(edges, sub_nodes, mem_state, vm_state)
    add_sched_queue_blocks(edges, sub_nodes, mem_state, vm_state)

ALL_REGISTERED_ROOT_PTRS = set([
    "usbd",
    "bluetooth",
    "lwip_slip_stream",
    "virtio_device",
    "mp_wifi_spi",
    "mp_wifi_spi",
    "mp_wifi_poll_list",
    "vfs_cur",
    "vfs_mount_table",
    "bluetooth_btstack_root_pointers",
    "bluetooth_nimble_memory",
    "bluetooth_nimble_root_pointers",
    "os_term_dup_obj",
    "machine_config_main",
    "esp32_pcnt_obj_head",
    "machine_timer_obj_head",
    "espnow_singleton",
    "uart0_rxbuf",
    "espnow_buffer",
    "machine_rtc_irq_object",
    "mp_bthci_uart",
    "pwm_active_events",
    "pwm_pending_events",
    "pin_class_mapper",
    "pin_class_map_dict",
    "modmusic_music_data",
    "keyboard_interrupt_obj",
    "pyb_config_main",
    "pyb_stdio_uart",
    "pyb_switch_callback",
    "pyb_config_main",
    "pyb_stdio_uart",
    "pin_class_mapper",
    "pin_class_map_dict",
    "subghz_callback",
    "pyb_hid_report_desc",
    "pyb_switch_callback",
    "mmap_region_head",
    "proxy_c_ref",
    "proxy_c_dict",
    "machine_pin_irq_list",
    "machine_timer_obj_head",
    "bluetooth_zephyr_root_pointers",
    "cur_exception",
    "sys_exitfunc",
    "persistent_code_root_pointers",
    "track_reloc_code_list",
    "repl_line",
])
ALL_REGISTERED_ROOT_ARRAYS = set([
    "machine_i2c_target_mem_obj",
    "machine_i2c_target_irq_obj",
    "dupterm_objs",
    "machine_pin_irq_obj",
    "machine_uart_obj_all",
    "pyb_uart_objs",
    "machine_i2s_obj",
    "machine_pin_irq_handler",
    "pin_irq_handler",
    "machine_i2s_obj",
    "machine_pin_irq_objects",
    "async_data",
    "pin_irq_handlers",
    "nrf_uart_irq_obj",
    "pyb_extint_callback",
    "machine_uart_obj_all",
    "pyb_timer_obj_all",
    "machine_i2s_obj",
    "machine_pin_irq_obj",
    "rp2_uart_rx_buffer",
    "rp2_uart_tx_buffer",
    "rp2_uart_irq_obj",
    "rp2_dma_irq_obj",
    "rp2_pio_irq_obj",
    "rp2_state_machine_irq_obj",
    "machine_pin_irq_objects",
    "sercom_table",
    "pyb_extint_callback",
    "machine_i2s_obj",
    "pyb_can_obj_all",
    "pyb_timer_obj_all",
    "machine_uart_obj_all",
    "pyb_usb_vcp_irq",
    "sys_mutable",
])
ALL_REGISTERED_ROOT_STRUCTS = set([
    "mod_network_nic_list",
    "mp_irq_obj_list",
    "pyb_sleep_obj_list",
    "pyb_timer_channel_obj_list",
    "mp_sys_argv_obj",
])
# TODO how to handle: MP_REGISTER_ROOT_POINTER(const char *readline_hist[MICROPY_READLINE_HISTORY_SIZE]);
def add_registered_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state, vm_state):
    sub_nodes = pydot.Subgraph("registered", cluster=True, color="red", style="dashed", label="MP_REGISTER_ROOT_POINTER")
    nodes.add_subgraph(sub_nodes)

    for ptr_name in ALL_REGISTERED_ROOT_PTRS:
        add_ptr_block(edges, sub_nodes, mem_state, vm_state, ptr_name, unless_disabled=ptr_name)
    for array_name in ALL_REGISTERED_ROOT_ARRAYS:
        add_array_block(edges, sub_nodes, mem_state, vm_state, array_name, unless_disabled=array_name)
    for struct_name in ALL_REGISTERED_ROOT_STRUCTS:
        add_substruct_block(edges, sub_nodes, mem_state, vm_state, struct_name, unless_disabled=struct_name)

def add_sched_queue_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state, vm_state):
    sub_nodes = pydot.Subgraph("sched_queue", cluster=True, color="black", label="sched_queue")
    nodes.add_subgraph(sub_nodes)

    sched_queue = struct_get_checked(vm_state, "sched_queue", unless_disabled="MICROPY_ENABLE_SCHEDULER")
    if sched_queue == None:
        return
    sched_queue_size = sched_queue.type.sizeof // sched_queue[0].type.sizeof

    for i in range(sched_queue_size):
        sched_item = sched_queue[i]
        node = pydot.Node(
            f"sched_item_{i}",
            label=f'"<func>sched_queue[{i}]\\nfunc|<arg>arg"',
            shape="record",
        )
        sub_nodes.add_node(node)
        add_heap_ptr(edges, mem_state, f"sched_item_{i}:func", sched_item["func"])
        add_heap_ptr(edges, mem_state, f"sched_item_{i}:arg", sched_item["arg"])

def add_cpu_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state):
    sub_nodes = pydot.Subgraph("cpu", cluster=True, color="purple", label="cpu")
    nodes.add_subgraph(sub_nodes)

    for reg in gdb.selected_inferior().architecture().registers("general"):
        value = gdb.newest_frame().read_register(reg)
        imm_val = get_immediate(value)
        
        if imm_val is None:
            node = pydot.Node(
                f"{reg.name}",
                shape="record",
            )
            add_heap_ptr(edges, mem_state, f"{reg.name}", value)
        else:
            node = pydot.Node(
                f"{reg.name}",
                label=f"{reg.name}\\n{imm_val}",
                shape="record",
            )
        sub_nodes.add_node(node)

def add_stack_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state, thread_state):
    sub_nodes = pydot.Subgraph("stack", cluster=True, color="maroon", label="stack")
    nodes.add_subgraph(sub_nodes)

    frame = gdb.selected_frame()
    frame_nodes = pydot.Subgraph(f"level{frame.level()}", cluster=True, color="maroon", style="dashed", label=f"level{frame.level()}")
    sub_nodes.add_subgraph(frame_nodes)

    stack_top = thread_state["stack_top"]
    stack_bot = frame.read_register("sp")
    stack_bot = stack_bot - (int(stack_bot) % BYTES_PER_WORD)

    stack = stack_bot.cast(gdb.lookup_type("uintptr_t").pointer())
    stack_size = int(stack_top - stack_bot) // BYTES_PER_WORD

    for i in range(stack_size):
        value = stack[i]
        name = get_pointer_edge_ref(mem_state, value.address)
        imm_val = get_immediate(value)
        
        try:
            if value.address >= frame.older().read_register("sp"):
                frame = frame.older()
                frame_nodes = pydot.Subgraph(f"level{frame.level()}", cluster=True, color="maroon", style="dashed", label=f"level{frame.level()}")
                sub_nodes.add_subgraph(frame_nodes)
        except AttributeError:
            pass

        node = None
        if imm_val is None:
            if add_heap_ptr(edges, mem_state, name, value, heap_only=True):
                node = pydot.Node(
                    name,
                    shape="record",
                )
        else:
            pass
            # node = pydot.Node(
            #     name,
            #     label=f"{name}\\n{imm_val}",
            #     shape="record",
            # )
        if node:
            frame_nodes.add_node(node)

def all_pthreads():
    try:
        thread = gdb.lookup_symbol("thread")[0].value()
    except AttributeError:
        return
    while int(thread) != 0:
        yield thread[0]
        thread = thread[0]['next']

def add_pthread_blocks(edges:pydot.Graph, nodes:pydot.Graph, mem_state):
    sub_nodes = pydot.Subgraph("stack", cluster=True, color="chartreuse", label="pthreads")
    nodes.add_subgraph(sub_nodes)

    for thread in all_pthreads():
        # log.warning("thread = %r", thread)
        name = get_pointer_edge_ref(mem_state, thread.address)
        tid = int(thread['id'])
        arg = thread['arg']

        node = pydot.Node(
            name,
            label=f"pthread {tid}|<arg>arg",
            shape="record",
        )
        sub_nodes.add_node(node)
        add_heap_ptr(edges, mem_state, f"{name}:arg", arg, heap_only=True)

        # TODO: get other threads' register contents?
        

def print_heap_graph(print):
    dot_graph = pydot.Dot("Heap", graph_type="digraph", fontname="Helvetica,Arial,sans-serif", layout="dot", ranksep="2.0")
    dot_graph.set_graph_defaults(rankdir="LR")
    dot_graph.set_node_defaults(fontsize="16", shape="ellipse", fontname="Helvetica,Arial,sans-serif")
    dot_graph.set_edge_defaults(fontname="Helvetica,Arial,sans-serif")

    state = gdb.lookup_symbol("mp_state_ctx")[0].value()
    mem_state = state["mem"]
    thread_state = state["thread"]
    vm_state = state["vm"]

    add_mem_blocks(dot_graph, dot_graph, mem_state)
    add_thread_blocks(dot_graph, dot_graph, mem_state, thread_state)
    add_vm_blocks(dot_graph, dot_graph, mem_state, vm_state)
    add_cpu_blocks(dot_graph, dot_graph, mem_state)
    add_stack_blocks(dot_graph, dot_graph, mem_state, thread_state)
    add_pthread_blocks(dot_graph, dot_graph, mem_state)
    

    print(dot_graph)
    # return dot_graph


class MpyHeap(gdb.Command):
    """Dissasemble MicroPython bytecode.
    Usage: mpy heap
    """
    def __init__(self):
        super(MpyHeap, self).__init__("mpy heap", gdb.COMMAND_DATA, gdb.COMPLETE_NONE)
        log.info("Registered command: mpy heap")

    def invoke(self, args, from_tty):
        try:
            print_heap_graph(print)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

if has_pydot:
    MpyHeap()


log.info("Loaded MicroPython GDB Plugin")