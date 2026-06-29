/* This file is part of the Spring engine (GPL v2 or later), see LICENSE.html */

#ifndef RASC_FORMAT_H
#define RASC_FORMAT_H

#include <cstdint>

// RASC binary format constants (matches RasFile.cpp::loadRascFormat()).

static constexpr uint32_t RASC_MAGIC = 0x43534152; // "RASC"
static constexpr uint32_t RASC_VERSION = 1;

// RASC binary header (48 bytes, all fields little-endian int32).
// Offsets match RasFile.cpp:414-427 exactly.
struct RascBinaryHeader {
	uint32_t magic;              // +0  0x43534152 "RASC"
	uint32_t version;            // +4  1
	uint32_t numScripts;         // +8
	uint32_t numPieces;          // +12
	uint32_t numStaticVars;      // +16
	uint32_t numSounds;          // +20
	uint32_t numInstructions;    // +24
	uint32_t offsetScriptNames;  // +28
	uint32_t offsetPieceNames;   // +32
	uint32_t offsetScriptInfo;   // +36
	uint32_t offsetDecoded;      // +40
	uint32_t offsetSoundNames;   // +44  0 if none
};
static_assert(sizeof(RascBinaryHeader) == 48, "RascBinaryHeader must be 48 bytes");

// Per-script metadata (16 bytes each).
// Matches RasFile.cpp:431-438 exactly.
struct RascScriptInfo {
	int32_t  decodedOffset;  // +0  first instruction index in decoded stream
	int32_t  maxStackDepth;  // +4
	uint8_t  threadSafe;     // +8  0 or 1
	uint8_t  isLuaScript;    // +9
	uint8_t  padding[6];     // +10
};
static_assert(sizeof(RascScriptInfo) == 16, "RascScriptInfo must be 16 bytes");

// Decoded instruction (10 bytes packed on disk).
// Parsed field-by-field on load; this struct is documentation only. Avoid
// non-portable __attribute__((packed)) so the header compiles under MSVC.
static constexpr int RASC_DISK_INSTR_SIZE = 10;
struct RascInstr {
	uint8_t  op;     // +0  RasOp byte value
	uint8_t  flags;  // +1  RAS_INSTR_* bitmask
	int32_t  a;      // +2  first operand / jump target / funcId (LE)
	int32_t  b;      // +6  second operand / argCount / immediate (LE)
};

#endif // RASC_FORMAT_H
