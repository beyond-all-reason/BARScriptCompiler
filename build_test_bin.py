import sys
sys.path.insert(0, '.')
import rasc_file

instructions = []
main_start = 0

def emit(op, flags=0, a=0, b=0):
    instructions.append((op, flags, a, b))

# Opcodes
MOVE = 0x01; TURN = 0x02; SPIN = 0x03; STOP_SPIN = 0x04
SHOW = 0x05; HIDE = 0x06; SCALE = 0x0A; MOVE_NOW = 0x0B
TURN_NOW = 0x0C; SHADE = 0x0D; DONT_SHADE = 0x0E; EMIT_SFX = 0x0F
SCALE_NOW = 0x10; WAIT_TURN = 0x11; WAIT_MOVE = 0x12
SLEEP = 0x13; WAIT_SCALE = 0x14
PUSH_CONSTANT = 0x21; PUSH_LOCAL_VAR = 0x22; PUSH_STATIC = 0x23
CREATE_LOCAL_VAR = 0x24; POP_LOCAL_VAR = 0x25; POP_STATIC = 0x26
POP_STACK = 0x27; CACHE = 0x28; DONT_CACHE = 0x29
ADD = 0x31; SUB = 0x32; MUL = 0x33; DIV = 0x34; MOD = 0x30
BITWISE_AND = 0x35; BITWISE_OR = 0x36; BITWISE_XOR = 0x37; BITWISE_NOT = 0x38
ABSOLUTE = 0x39; MINIMUM = 0x3A; MAXIMUM = 0x3B; SIGN = 0x3C; CLAMP = 0x3D
DELTAHEADING = 0x3E; MSINE = 0x3F; MCOSINE = 0x40
ADDI = 0x4B; MULI = 0x4C; TURN_REL = 0x4D; MOVE_REL = 0x4E
EXPLODE_REL = 0x4F; SCALE_REL = 0x50
RAND = 0x41; GET_UNIT_VALUE = 0x42; GET = 0x43
SET_LESS = 0x51; SET_LESS_OR_EQUAL = 0x52; SET_GREATER = 0x53
SET_GREATER_OR_EQUAL = 0x54; SET_EQUAL = 0x55; SET_NOT_EQUAL = 0x56
LOGICAL_AND = 0x57; LOGICAL_OR = 0x58; LOGICAL_XOR = 0x59; LOGICAL_NOT = 0x5A
START_SCRIPT = 0x61; CALL_SCRIPT = 0x62
JUMP = 0x64; RETURN = 0x65; JUMP_NOT_EQUAL = 0x66
SIGNAL = 0x67; SET_SIGNAL_MASK = 0x68
LUA_CALL = 0x69; BATCH_LUA = 0x6A; LUA_UNSYNCED = 0x6B
SIGNATURE_LUA = 0x90
EXPLODE = 0x71; PLAY_SOUND = 0x72
SET = 0x82; ATTACH = 0x83; DROP = 0x84

# === Script 0: "main" ===
emit(SHOW, 0, 0)              # 0: show barrel1
emit(SHOW, 0, 1)              # 1: show turret1
emit(SHOW, 0, 2)              # 2: show base
emit(CREATE_LOCAL_VAR)        # 3: var x
emit(CREATE_LOCAL_VAR)        # 4: var y
emit(PUSH_CONSTANT, 0, 100)   # 5
emit(POP_LOCAL_VAR, 0, 0)     # 6: x = 100
emit(PUSH_CONSTANT, 0, 200)   # 7
emit(POP_LOCAL_VAR, 0, 1)     # 8: y = 200
emit(PUSH_LOCAL_VAR, 0, 0)    # 9
emit(PUSH_LOCAL_VAR, 0, 1)    # 10
emit(ADD)                     # 11
emit(POP_LOCAL_VAR, 0, 0)     # 12: x = x + y
emit(PUSH_LOCAL_VAR, 0, 0)    # 13
emit(PUSH_CONSTANT, 0, 50)    # 14
emit(MOVE, 0, 0, 0)           # 15: move barrel1 x-axis speed 50
emit(PUSH_CONSTANT, 0, 90)    # 16
emit(PUSH_CONSTANT, 0, 30)    # 17
emit(TURN, 0, 1, 1)           # 18: turn turret1 y-axis 90 speed 30
emit(PUSH_CONSTANT, 0, 50)    # 19
emit(SCALE, 0, 2)             # 20: scale base z-axis 50
emit(PUSH_CONSTANT, 0, 100)   # 21
emit(SLEEP)                   # 22: sleep 100
emit(CALL_SCRIPT, 0, 1, 0)    # 23: call helper
emit(PUSH_CONSTANT, 0, 1)     # 24
emit(EXPLODE, 0, 0)           # 25: explode barrel1 type 1
emit(PLAY_SOUND, 0, 0)        # 26: play sound 0
emit(PUSH_LOCAL_VAR, 0, 0)    # 27
emit(PUSH_CONSTANT, 0, 50)    # 28
emit(SUB)                     # 29
emit(POP_LOCAL_VAR, 0, 0)     # 30: x = x - 50
# if (x > 100) { x = 100 } else { x = 50 }
emit(PUSH_LOCAL_VAR, 0, 0)    # 31
emit(PUSH_CONSTANT, 0, 100)   # 32
emit(SET_GREATER)             # 33
emit(JUMP_NOT_EQUAL, 0, 38)   # 34: if !cond jump to else(38)
emit(PUSH_CONSTANT, 0, 100)   # 35: then: x = 100
emit(POP_LOCAL_VAR, 0, 0)     # 36
emit(JUMP, 0, 40)             # 37: jump to while(40)
emit(PUSH_CONSTANT, 0, 50)    # 38: else: x = 50
emit(POP_LOCAL_VAR, 0, 0)     # 39
# while (x > 0) { x = x - 1; sleep 10 }
emit(PUSH_LOCAL_VAR, 0, 0)    # 40: while start
emit(PUSH_CONSTANT, 0, 0)     # 41
emit(SET_GREATER)             # 42
emit(JUMP_NOT_EQUAL, 0, 53)   # 43: if !cond jump to return(53)
emit(PUSH_LOCAL_VAR, 0, 0)    # 44
emit(PUSH_CONSTANT, 0, 1)     # 45
emit(SUB)                     # 46
emit(POP_LOCAL_VAR, 0, 0)     # 47: x = x - 1
emit(PUSH_CONSTANT, 0, 10)    # 48
emit(SLEEP)                   # 49: sleep 10
emit(JUMP, 0, 40)             # 50: back to while
emit(PUSH_CONSTANT, 0, 0)     # 51
emit(RETURN)                  # 52: return 0

main_end = len(instructions)  # 53
helper_start = main_end

# === Script 1: "helper" ===
emit(CREATE_LOCAL_VAR)        # 53: var result
emit(PUSH_CONSTANT, 0, 42)    # 54
emit(POP_LOCAL_VAR, 0, 0)     # 55: result = 42
emit(PUSH_CONSTANT, 0, 20)    # 56
emit(PUSH_CONSTANT, 0, 0)     # 57
emit(SPIN, 0, 0, 0)           # 58: spin barrel1 x-axis speed 20
emit(PUSH_CONSTANT, 0, 0)     # 59
emit(PUSH_CONSTANT, 0, 0)     # 60
emit(STOP_SPIN, 0, 0, 0)      # 61: stop-spin barrel1 x-axis
emit(PUSH_CONSTANT, 0, 0)     # 62
emit(HIDE, 0, 1)              # 63: hide turret1
emit(PUSH_LOCAL_VAR, 0, 0)    # 64
emit(RETURN)                  # 65: return result

helper_end = len(instructions)  # 66

script_infos = [
    (main_start, 3, 1, 0),
    (helper_start, 2, 1, 0),
]

rasc = rasc_file.RascFile(
    script_names=["main", "helper"],
    piece_names=["barrel1", "turret1", "base"],
    static_vars=["globalTimer"],
    sound_names=["explosion.wav"],
    instructions=instructions,
    script_infos=script_infos,
)

data = rasc.get_content()
with open("BARScriptCompiler/test_decompile.bin", "wb") as f:
    f.write(data)

print(f"Written {len(data)} bytes, {len(instructions)} instructions")
print(f"main: [{main_start}, {main_end}), helper: [{helper_start}, {helper_end})")
