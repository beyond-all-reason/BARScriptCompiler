import struct
import os
import sys
from collections import defaultdict

# RASC binary format constants
RASC_MAGIC = 0x43534152
RASC_VERSION = 1

# Header: 12 LE int32 fields = 48 bytes
HEADER_FMT = "<12I"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
HEADER_FIELDS = [
    "magic", "version", "numScripts", "numPieces", "numStaticVars",
    "numSounds", "numInstructions", "offsetScriptNames", "offsetPieceNames",
    "offsetScriptInfo", "offsetDecoded", "offsetSoundNames",
]

# ScriptInfo: 16 bytes each
SCRIPT_INFO_FMT = "<iiBB6x"
SCRIPT_INFO_SIZE = struct.calcsize(SCRIPT_INFO_FMT)

# RasInstr: 10 bytes packed
INSTR_FMT = "<BBii"
INSTR_SIZE = struct.calcsize(INSTR_FMT)

# Dense byte opcodes (matches RasOpCodes.h RAS_OPCODE_LIST)
OPCODES = {
    'MOVE': 0x01, 'TURN': 0x02, 'SPIN': 0x03, 'STOP_SPIN': 0x04,
    'SHOW': 0x05, 'HIDE': 0x06, 'CACHE': 0x28, 'DONT_CACHE': 0x29,
    'MOVE_NOW': 0x0B, 'TURN_NOW': 0x0C, 'SHADE': 0x0D, 'DONT_SHADE': 0x0E,
    'EMIT_SFX': 0x0F, 'SCALE': 0x0A, 'SCALE_NOW': 0x10,
    'WAIT_TURN': 0x11, 'WAIT_MOVE': 0x12, 'SLEEP': 0x13, 'WAIT_SCALE': 0x14,
    'PUSH_CONSTANT': 0x21, 'PUSH_LOCAL_VAR': 0x22, 'PUSH_STATIC': 0x23,
    'CREATE_LOCAL_VAR': 0x24, 'POP_LOCAL_VAR': 0x25, 'POP_STATIC': 0x26,
    'POP_STACK': 0x27, 'PUSH_STATIC_IDX': 0x2A, 'POP_STATIC_IDX': 0x2B,
    'ADD': 0x31, 'SUB': 0x32, 'MUL': 0x33, 'DIV': 0x34, 'MOD': 0x30,
    'BITWISE_AND': 0x35, 'BITWISE_OR': 0x36, 'BITWISE_XOR': 0x37,
    'BITWISE_NOT': 0x38, 'ABSOLUTE': 0x39, 'MINIMUM': 0x3A, 'MAXIMUM': 0x3B,
    'SIGN': 0x3C, 'CLAMP': 0x3D, 'DELTAHEADING': 0x3E, 'MSINE': 0x3F,
    'MCOSINE': 0x40, 'ADDI': 0x4B, 'MULI': 0x4C, 'TURN_REL': 0x4D,
    'MOVE_REL': 0x4E, 'EXPLODE_REL': 0x4F, 'SCALE_REL': 0x50,
    'RAND': 0x41, 'GET_UNIT_VALUE': 0x42, 'GET': 0x43,
    'SET_LESS': 0x51, 'SET_LESS_OR_EQUAL': 0x52, 'SET_GREATER': 0x53,
    'SET_GREATER_OR_EQUAL': 0x54, 'SET_EQUAL': 0x55, 'SET_NOT_EQUAL': 0x56,
    'LOGICAL_AND': 0x57, 'LOGICAL_OR': 0x58, 'LOGICAL_XOR': 0x59,
    'LOGICAL_NOT': 0x5A,
    'START_SCRIPT': 0x61, 'CALL_SCRIPT': 0x62,
    'JUMP': 0x64, 'RETURN': 0x65, 'JUMP_NOT_EQUAL': 0x66,
    'SIGNAL': 0x67, 'SET_SIGNAL_MASK': 0x68,
    'LUA_CALL': 0x69, 'BATCH_LUA': 0x6A, 'LUA_UNSYNCED': 0x6B,
    'EXPLODE': 0x71, 'PLAY_SOUND': 0x72,
    'SET': 0x82, 'ATTACH': 0x83, 'DROP': 0x84,
    'SIGNATURE_LUA': 0x90,
    'BADOPCODE': 0xFF,
}

# Reverse lookup: byte -> name
OP_NAME = {v: k for k, v in OPCODES.items()}

# Operand count per opcode (matches RasOpOperandWords in RasOpCodes.h)
OP_OPERANDS = {
    0x01: 2, 0x02: 2, 0x03: 2, 0x04: 2,
    0x05: 1, 0x06: 1, 0x28: 1, 0x29: 1,
    0x0B: 2, 0x0C: 2, 0x0D: 1, 0x0E: 1,
    0x0F: 1, 0x0A: 1, 0x10: 1,
    0x11: 1, 0x12: 1, 0x13: 0, 0x14: 1,
    0x21: 1, 0x22: 1, 0x23: 1, 0x24: 0,
    0x25: 1, 0x26: 1, 0x27: 0, 0x2A: 1, 0x2B: 1,
    0x31: 0, 0x32: 0, 0x33: 0, 0x34: 0, 0x30: 0,
    0x35: 0, 0x36: 0, 0x37: 0, 0x38: 0,
    0x39: 0, 0x3A: 0, 0x3B: 0, 0x3C: 0, 0x3D: 0,
    0x3E: 0, 0x3F: 0, 0x40: 0,
    0x4B: 1, 0x4C: 1, 0x4D: 0, 0x4E: 0, 0x4F: 0, 0x50: 0,
    0x41: 0, 0x42: 0, 0x43: 0,
    0x51: 0, 0x52: 0, 0x53: 0, 0x54: 0, 0x55: 0, 0x56: 0,
    0x57: 0, 0x58: 0, 0x59: 0, 0x5A: 0,
    0x61: 2, 0x62: 2,
    0x64: 1, 0x65: 0, 0x66: 1,
    0x67: 0, 0x68: 1,
    0x69: 2, 0x6A: 2, 0x6B: 2,
    0x90: 0,
    0x71: 1, 0x72: 1,
    0x82: 0, 0x83: 0, 0x84: 0,
}

# Opcodes that take a piece index in operand a
PIECE_OPCODES = {
    0x01, 0x02, 0x03, 0x04,  # MOVE, TURN, SPIN, STOP_SPIN
    0x0B, 0x0C,              # MOVE_NOW, TURN_NOW
    0x05, 0x06,              # SHOW, HIDE
    0x0D, 0x0E,              # SHADE, DONT_SHADE
    0x28, 0x29,              # CACHE, DONT_CACHE
    0x0F,                    # EMIT_SFX
    0x0A, 0x10,              # SCALE, SCALE_NOW
    0x11, 0x12, 0x14,        # WAIT_TURN, WAIT_MOVE, WAIT_SCALE
    0x4D, 0x4E, 0x4F, 0x50,  # TURN_REL, MOVE_REL, EXPLODE_REL, SCALE_REL
    0x71,                    # EXPLODE
}

# Opcodes where operand a is a script/function index
SCRIPT_OPCODES = {0x61, 0x62, 0x69, 0x6A, 0x6B}  # START, CALL, LUA_CALL, BATCH_LUA, LUA_UNSYNCED


def read_null_terminated(data, offset):
    end = data.find(b"\x00", offset)
    if end == -1:
        return data[offset:].decode("utf-8", errors="replace")
    return data[offset:end].decode("utf-8", errors="replace")


def read_string_table(data, offset, count):
    strings = []
    pos = offset
    for _ in range(count):
        s = read_null_terminated(data, pos)
        strings.append(s)
        pos = data.find(b"\x00", pos) + 1
    return strings


def op_name_str(op):
    return OP_NAME.get(op, f"UNKNOWN_0x{op:02X}")


def operand_count(op):
    return OP_OPERANDS.get(op, 0)


def resolve_piece_name(idx, pieces):
    if 0 <= idx < len(pieces):
        return pieces[idx]
    return None


def resolve_script_name(idx, scripts):
    if 0 <= idx < len(scripts):
        return scripts[idx]
    return None


def find_script_at_offset(instr_idx, script_infos):
    for i, info in enumerate(script_infos):
        if info["decodedOffset"] <= instr_idx < info["endOffset"]:
            return i
    return -1


def decompile_file(filepath):
    with open(filepath, "rb") as f:
        data = f.read()

    fname = os.path.basename(filepath)
    print(f"=== {fname} ===")

    if len(data) < HEADER_SIZE:
        print(f"Error: file too small ({len(data)} bytes)")
        return None

    header_values = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    header = dict(zip(HEADER_FIELDS, header_values))

    magic = header["magic"]
    if magic != RASC_MAGIC:
        print(f"Error: invalid magic 0x{magic:08X} (expected 0x{RASC_MAGIC:08X})")
        return None

    version = header["version"]
    if version != RASC_VERSION:
        print(f"Warning: unexpected version {version} (expected {RASC_VERSION})")

    num_scripts = header["numScripts"]
    num_pieces = header["numPieces"]
    num_static_vars = header["numStaticVars"]
    num_sounds = header["numSounds"]
    num_instructions = header["numInstructions"]

    print(f"Magic: RASC v{version}")
    print(f"Scripts: {num_scripts}, Pieces: {num_pieces}, StaticVars: {num_static_vars}, "
          f"Sounds: {num_sounds}, Instructions: {num_instructions}")

    # Read piece names
    pieces = []
    if num_pieces > 0 and header["offsetPieceNames"] < len(data):
        pieces = read_string_table(data, header["offsetPieceNames"], num_pieces)
    if pieces:
        print(f"Pieces: {', '.join(pieces)}")

    # Read script names
    scripts = []
    if num_scripts > 0 and header["offsetScriptNames"] < len(data):
        scripts = read_string_table(data, header["offsetScriptNames"], num_scripts)
    if scripts:
        print(f"Scripts: {', '.join(scripts)}")

    # Read sound names
    sounds = []
    if num_sounds > 0 and header["offsetSoundNames"] > 0 and header["offsetSoundNames"] < len(data):
        sounds = read_string_table(data, header["offsetSoundNames"], num_sounds)
    if sounds:
        print(f"Sounds: {', '.join(sounds)}")

    # Read script info
    script_infos = []
    if num_scripts > 0 and header["offsetScriptInfo"] < len(data):
        base = header["offsetScriptInfo"]
        for i in range(num_scripts):
            pos = base + i * SCRIPT_INFO_SIZE
            if pos + SCRIPT_INFO_SIZE > len(data):
                print(f"Warning: truncated script info at index {i}")
                break
            vals = struct.unpack(SCRIPT_INFO_FMT, data[pos:pos + SCRIPT_INFO_SIZE])
            script_infos.append({
                "name": scripts[i] if i < len(scripts) else f"script_{i}",
                "decodedOffset": vals[0],
                "maxStackDepth": vals[1],
                "threadSafe": vals[2],
                "isLuaScript": vals[3],
            })

    # Compute end offsets for each script
    for i, info in enumerate(script_infos):
        if i + 1 < len(script_infos):
            info["endOffset"] = script_infos[i + 1]["decodedOffset"]
        else:
            info["endOffset"] = num_instructions

    # Read decoded instructions
    instructions = []
    if num_instructions > 0 and header["offsetDecoded"] < len(data):
        base = header["offsetDecoded"]
        for i in range(num_instructions):
            pos = base + i * INSTR_SIZE
            if pos + INSTR_SIZE > len(data):
                print(f"Warning: truncated instruction at index {i}")
                break
            vals = struct.unpack(INSTR_FMT, data[pos:pos + INSTR_SIZE])
            instructions.append({
                "op": vals[0],
                "flags": vals[1],
                "a": vals[2],
                "b": vals[3],
            })

    # Disassemble each script
    opcode_freq = defaultdict(int)
    pair_freq = defaultdict(int)
    all_lines = []

    for i, info in enumerate(script_infos):
        start = info["decodedOffset"]
        end = info["endOffset"]
        length = end - start

        safe_str = "safe" if info["threadSafe"] else "unsafe"
        lua_str = " lua" if info["isLuaScript"] else ""
        print(f"\n--- {info['name']} (offset={start}, len={length}, "
              f"stack={info['maxStackDepth']}, {safe_str}{lua_str}) ---")

        if length == 0:
            print(f"  [empty]")
            continue

        prev_op_name = None
        for j in range(start, end):
            if j >= len(instructions):
                print(f"  {j}: [TRUNCATED]")
                break

            instr = instructions[j]
            op = instr["op"]
            flags = instr["flags"]
            a = instr["a"]
            b = instr["b"]

            op_name = op_name_str(op)
            op_cnt = operand_count(op)

            # Build operand string
            parts = []
            if op_cnt >= 1:
                piece_name = None
                if op in PIECE_OPCODES:
                    piece_name = resolve_piece_name(a, pieces)

                if piece_name:
                    parts.append(f"a={a}  ({piece_name})")
                else:
                    parts.append(f"a={a}")
            if op_cnt >= 2:
                parts.append(f"b={b}")

            # Special annotations
            annotations = []

            # Jump target resolution
            if op in (0x64, 0x66):  # JUMP, JUMP_NOT_EQUAL
                target = a
                target_script = find_script_at_offset(target, script_infos)
                if target_script >= 0:
                    annotations.append(f"-> {script_infos[target_script]['name']}")
                annotations.append(f"[{target}]")

            # CALL/START target resolution
            if op in SCRIPT_OPCODES:
                target_name = resolve_script_name(a, scripts)
                if target_name:
                    annotations.append(f"-> {target_name}")
                annotations.append(f"args={b}")

            # Format line
            indent = "  "
            idx_str = f"{j}:"
            opcode_str = f"{op_name:<20}"
            operand_str = "  ".join(parts) if parts else ""
            flag_str = " ".join(annotations) if annotations else ""

            line = f"{indent}{idx_str} {opcode_str}"
            if operand_str:
                line += f"  {operand_str}"
            if flag_str:
                line += f"  {flag_str}"

            print(line)
            all_lines.append((j, op_name))

            # Stats
            opcode_freq[op_name] += 1
            if prev_op_name:
                pair_key = f"{prev_op_name}->{op_name}"
                pair_freq[pair_key] += 1
            prev_op_name = op_name

    # Print statistics
    print("\n=== Opcode Frequency ===")
    for op_name in sorted(opcode_freq.keys(), key=lambda x: -opcode_freq[x]):
        print(f"  {op_name:<20} {opcode_freq[op_name]}")

    print("\n=== Instruction Pairs ===")
    for pair in sorted(pair_freq.keys(), key=lambda x: -pair_freq[x]):
        print(f"  {pair:<40} {pair_freq[pair]}")

    return {
        "instructions": instructions,
        "scripts": script_infos,
        "pieces": pieces,
        "opcode_freq": opcode_freq,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python rasc_decompiler.py <file.rasc> [file2 ...]")
        print("       python rasc_decompiler.py <directory>")
        sys.exit(1)

    args = sys.argv[1:]
    files = []

    for arg in args:
        if os.path.isdir(arg):
            for entry in sorted(os.listdir(arg)):
                if entry.lower().endswith(".rasc"):
                    files.append(os.path.join(arg, entry))
        else:
            if not os.path.exists(arg):
                print(f"Error: {arg} not found")
                sys.exit(1)
            files.append(arg)

    if not files:
        print("No .rasc files found")
        sys.exit(0)

    for filepath in files:
        decompile_file(filepath)
        print()


if __name__ == "__main__":
    main()
