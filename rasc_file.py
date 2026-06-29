# Written by ashdnazg https://github.com/ashdnazg/bos2cob
# Extended by Beherith to https://github.com/beyond-all-reason/BARScriptCompiler
# RASC format fork for pre-decoded binary output
# released under the GNU GPL v3 license

import struct

# RASC binary format constants (must match RasFile.cpp::loadRascFormat())
RASC_MAGIC = 0x43534152  # "RASC"
RASC_VERSION = 1

# Header layout: 12 LE int32 fields = 48 bytes
# magic, version, numScripts, numPieces, numStaticVars, numSounds,
# numInstructions, offsetScriptNames, offsetPieceNames,
# offsetScriptInfo, offsetDecoded, offsetSoundNames

# ScriptInfo: 16 bytes each
# decodedOffset(int32), maxStackDepth(int32), threadSafe(u8), isLuaScript(u8), padding[6]

# RasInstr: 10 bytes packed
# op(u8), flags(u8), a(int32 LE), b(int32 LE)


def write_le32(value):
	return struct.pack("<I", value & 0xFFFFFFFF)


def write_le32s(value):
	return struct.pack("<i", value)


def write_instr(op, flags, a, b):
	return struct.pack("<BBii", op & 0xFF, flags & 0xFF, a, b)


def write_string_table(strings):
	offsets = []
	content = b""
	for s in strings:
		offsets.append(len(content))
		content += s.encode("utf-8") + b"\x00"
	return offsets, content


class RascFile:
	def __init__(self, script_names, piece_names, static_vars, sound_names,
				 instructions, script_infos):
		"""
		script_names: list of str
		piece_names: list of str
		static_vars: list of str
		sound_names: list of str (may be empty)
		instructions: list of (op, flags, a, b) tuples
		script_infos: list of (decodedOffset, maxStackDepth, threadSafe, isLuaScript)
		"""
		self._script_names = script_names
		self._piece_names = piece_names
		self._static_vars = static_vars
		self._sound_names = sound_names if sound_names else []
		self._instructions = instructions
		self._script_infos = script_infos

	def get_content(self):
		data = bytearray()
		header_offset = 0
		HDR_SIZE = 48

		# ---- Section 1: Script names (null-terminated strings) ----
		off_script_names = HDR_SIZE
		script_name_content = b""
		for s in self._script_names:
			script_name_content += s.encode("utf-8") + b"\x00"
		off_piece_names = off_script_names + len(script_name_content)

		# ---- Section 2: Piece names ----
		piece_name_content = b""
		for s in self._piece_names:
			piece_name_content += s.encode("utf-8") + b"\x00"
		off_script_info = off_piece_names + len(piece_name_content)

		# ---- Section 3: Script info block ----
		script_info_content = b""
		for (decoded_offset, max_stack, ts, is_lua) in self._script_infos:
			script_info_content += write_le32s(decoded_offset)
			script_info_content += write_le32s(max_stack)
			script_info_content += struct.pack("<BB6x",
											   1 if ts else 0,
											   1 if is_lua else 0)
		off_decoded = off_script_info + len(script_info_content)

		# ---- Section 4: Decoded instruction stream ----
		decoded_content = b""
		for (op, flags, a, b) in self._instructions:
			decoded_content += write_instr(op, flags, a, b)
		off_sound_names = off_decoded + len(decoded_content)

		# ---- Section 5: Sound names (TA:K only) ----
		sound_content = b""
		for s in self._sound_names:
			sound_content += s.encode("utf-8") + b"\x00"

		# ---- Build header ----
		header = bytearray()
		header += write_le32(RASC_MAGIC)
		header += write_le32(RASC_VERSION)
		header += write_le32(len(self._script_names))
		header += write_le32(len(self._piece_names))
		header += write_le32(len(self._static_vars))
		header += write_le32(len(self._sound_names))
		header += write_le32(len(self._instructions))
		header += write_le32(off_script_names)
		header += write_le32(off_piece_names)
		header += write_le32(off_script_info)
		header += write_le32(off_decoded)
		header += write_le32(off_sound_names if self._sound_names else 0)

		# ---- Assemble ----
		data = bytes(header)
		data += script_name_content
		data += piece_name_content
		data += script_info_content
		data += decoded_content
		if self._sound_names:
			data += sound_content

		return data
