This repository contains a gdb plugin for micropython on the rp2040, debugged under gdb.

To use this plugin you need a firmware.elf-file from the target firmware with debug symbols (the binary can be compiled in release mode though).
Additionally, for feeding stdin, and capturing ethernet/bluetooth, you need debugging-hook.patch.
This patch adds "trap" instructions to strategic positions, which allows breaking there without sacrificing one of the two precious hardware breakpoings.

The following gdb commands are implemented:
* `set debugging=3`, `feed_stdin 1+2`: Send "1+2" to the REPL wait for a response and print the captured stdout it. If `debugging` is not set, only stdin is set, and the execution needs to be resumed manually with `continue`.
* `poll_stdout`, look for output buffered in stdout.
* `pcap`: start capturing all ethernet frames and write a pcap file to `/tmp/picotrace.pcap`. That file can be live inspected with wireshark: `tail -n+0 -f /tmp/picotrace.pcap | wireshark -k -i -`
* `bpcap`: start capturing all bluetooth hci frame and write a pcap file to `/tmp/picoblue.pcap`. That file can be live inspected with wireshark: `tail -n+0 -f /tmp/picoblue.pcap | wireshark -k -i -`
* `qstr 42`: locate qstring 42 and print it
* `pystate` print all python objects for the current method's `code_state`.
* `pyobj 0xpyobj` print the micropython object `0xpyobj`.
* `pydis 0xpyobj` disassemble the code of a `mp_fun_bc`-object. You might need to make sure gdb finds `mp-tool` from `micropython/tools` for this command.

Also `backtrace` has been enriched with a frame filter to display python function calls and parameters instead of `execute_bytecode`.

Other features I thought about:
- Line info is also there and could be parsed, to enable source-line-stepping from bytecode-instruction-stepping.
- In order to step single bytecode instructions I would need to identify an instruction inside `execute_bytecode` that dispatches the next instruction, and that seems non-trivial. Especially as the source tries to avoid the existance of such an instruction.
