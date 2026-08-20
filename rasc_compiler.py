# Written by ashdnazg https://github.com/ashdnazg/bos2cob
# Extended by Beherith to https://github.com/beyond-all-reason/BARScriptCompiler
# RASC compiler fork: outputs pre-decoded RASC binary format
# released under the GNU GPL v3 license

import sys
import os.path
from glob import glob
import struct
import argparse
import rasc_file

import warnings
warnings.filterwarnings('ignore', 'write lextab module')

from io import StringIO
import pcpp

version = "1.0-rasc"

parser = argparse.ArgumentParser()
parser.add_argument("--dontfold", action='store_true',
					help="Disable constant folding optimization")
parser.add_argument("--nopcpp", action='store_true',
					help="Fallback to builtin preprocessor instead of pcpp")
parser.add_argument("--dumpast", action='store_true',
					help="Dump the parsed syntax tree into a _initial.ast file")
parser.add_argument("--dumppcpp", action='store_true',
					help="Dump the results of the pcpp preprocessor")
parser.add_argument("--include", type=str,
					help="Additional include directory for pcpp preprocessor")
parser.add_argument("--verbose", action='store_true',
					help="Verbose output during compilation")
parser.add_argument("filename", type=str,
					help="A .ras source file or directory of .ras files",
					default="", nargs='?')

args = parser.parse_args()

LINEAR_SCALE = 65536
ANGULAR_SCALE = 182

# ============================================================================
# Dense byte opcodes (matches RasOpCodes.h RAS_OPCODE_LIST)
# ============================================================================
OPCODES = {
	'MOVE'            : 0x01,
	'TURN'            : 0x02,
	'SPIN'            : 0x03,
	'STOP_SPIN'       : 0x04,
	'SHOW'            : 0x05,
	'HIDE'            : 0x06,
	'CACHE'           : 0x28,
	'DONT_CACHE'      : 0x29,
	'MOVE_NOW'        : 0x0B,
	'TURN_NOW'        : 0x0C,
	'SHADE'           : 0x0D,
	'DONT_SHADE'      : 0x0E,
	'DONT_SHADOW'     : 0x0E,
	'EMIT_SFX'        : 0x0F,
	'SCALE'           : 0x0A,
	'SCALE_NOW'       : 0x10,
	'WAIT_FOR_TURN'   : 0x11,
	'WAIT_FOR_MOVE'   : 0x12,
	'SLEEP'           : 0x13,
	'WAIT_FOR_SCALE'  : 0x14,
	'PUSH_CONSTANT'   : 0x21,
	'PUSH_LOCAL_VAR'  : 0x22,
	'PUSH_STATIC'     : 0x23,
	'CREATE_LOCAL_VAR': 0x24,
	'POP_LOCAL_VAR'   : 0x25,
	'POP_STATIC'      : 0x26,
	'POP_STACK'       : 0x27,
	'PUSH_STATIC_IDX' : 0x2A,
	'POP_STATIC_IDX'  : 0x2B,
	'ADD'             : 0x31,
	'SUB'             : 0x32,
	'MUL'             : 0x33,
	'DIV'             : 0x34,
	'MOD'             : 0x30,
	'BITWISE_AND'     : 0x35,
	'BITWISE_OR'      : 0x36,
	'BITWISE_XOR'     : 0x37,
	'BITWISE_NOT'     : 0x38,
	'ABSOLUTE'        : 0x39,
	'MINIMUM'         : 0x3A,
	'MAXIMUM'         : 0x3B,
	'SIGN'            : 0x3C,
	'CLAMP'           : 0x3D,
	'DELTAHEADING'    : 0x3E,
	'MSINE'           : 0x3F,
	'MCOSINE'         : 0x40,
	'ADDI'            : 0x4B,
	'MULI'            : 0x4C,
	'TURN_REL'        : 0x4D,
	'MOVE_REL'        : 0x4E,
	'EXPLODE_REL'     : 0x4F,
	'SCALE_REL'       : 0x50,
	'RAND'            : 0x41,
	'GET_UNIT_VALUE'  : 0x42,
	'GET'             : 0x43,
	'SET_LESS'        : 0x51,
	'SET_LESS_OR_EQUAL': 0x52,
	'SET_GREATER'     : 0x53,
	'SET_GREATER_OR_EQUAL': 0x54,
	'SET_EQUAL'       : 0x55,
	'SET_NOT_EQUAL'   : 0x56,
	'LOGICAL_AND'     : 0x57,
	'LOGICAL_OR'      : 0x58,
	'LOGICAL_XOR'     : 0x59,
	'LOGICAL_NOT'     : 0x5A,
	'START_SCRIPT'    : 0x61,
	'CALL_SCRIPT'     : 0x62,
	'JUMP'            : 0x64,
	'RETURN'          : 0x65,
	'JUMP_NOT_EQUAL'  : 0x66,
	'SIGNAL'          : 0x67,
	'SET_SIGNAL_MASK' : 0x68,
	'LUA_CALL'        : 0x69,
	'BATCH_LUA'       : 0x6A,
	'LUA_UNSYNCED'    : 0x6B,
	'SIGNATURE_LUA'   : 0x90,
	'EXPLODE'         : 0x71,
	'PLAY_SOUND'      : 0x72,
	'SET'             : 0x82,
	'ATTACH_UNIT'     : 0x83,
	'DROP_UNIT'       : 0x84,
}

# Operand count per opcode (matches RasOpOperandWords in RasOpCodes.h)
OP_OPERANDS = {
	0x01: 2,  # MOVE
	0x02: 2,  # TURN
	0x03: 2,  # SPIN
	0x04: 2,  # STOP_SPIN
	0x05: 1,  # SHOW
	0x06: 1,  # HIDE
	0x28: 1,  # CACHE
	0x29: 1,  # DONT_CACHE
	0x0B: 2,  # MOVE_NOW
	0x0C: 2,  # TURN_NOW
	0x0D: 1,  # SHADE
	0x0E: 1,  # DONT_SHADE
	0x0F: 1,  # EMIT_SFX
	0x0A: 1,  # SCALE
	0x10: 1,  # SCALE_NOW
	0x11: 1,  # WAIT_FOR_TURN
	0x12: 1,  # WAIT_FOR_MOVE
	0x13: 0,  # SLEEP
	0x14: 1,  # WAIT_FOR_SCALE
	0x21: 1,  # PUSH_CONSTANT
	0x22: 1,  # PUSH_LOCAL_VAR
	0x23: 1,  # PUSH_STATIC
	0x24: 0,  # CREATE_LOCAL_VAR
	0x25: 1,  # POP_LOCAL_VAR
	0x26: 1,  # POP_STATIC
	0x27: 0,  # POP_STACK
	0x2A: 1,  # PUSH_STATIC_IDX (a = base slot)
	0x2B: 1,  # POP_STATIC_IDX  (a = base slot)
	0x31: 0,  # ADD
	0x32: 0,  # SUB
	0x33: 0,  # MUL
	0x34: 0,  # DIV
	0x30: 0,  # MOD
	0x35: 0,  # BITWISE_AND
	0x36: 0,  # BITWISE_OR
	0x37: 0,  # BITWISE_XOR
	0x38: 0,  # BITWISE_NOT
	0x39: 0,  # ABSOLUTE
	0x3A: 0,  # MINIMUM
	0x3B: 0,  # MAXIMUM
	0x3C: 0,  # SIGN
	0x3D: 0,  # CLAMP
	0x3E: 0,  # DELTAHEADING
	0x3F: 0,  # MSINE
	0x40: 0,  # MCOSINE
	0x4B: 1,  # ADDI
	0x4C: 1,  # MULI
	0x4D: 0,  # TURN_REL
	0x4E: 0,  # MOVE_REL
	0x4F: 0,  # EXPLODE_REL
	0x50: 0,  # SCALE_REL
	0x41: 0,  # RAND
	0x42: 0,  # GET_UNIT_VALUE
	0x43: 0,  # GET
	0x51: 0,  # SET_LESS
	0x52: 0,  # SET_LESS_OR_EQUAL
	0x53: 0,  # SET_GREATER
	0x54: 0,  # SET_GREATER_OR_EQUAL
	0x55: 0,  # SET_EQUAL
	0x56: 0,  # SET_NOT_EQUAL
	0x57: 0,  # LOGICAL_AND
	0x58: 0,  # LOGICAL_OR
	0x59: 0,  # LOGICAL_XOR
	0x5A: 0,  # LOGICAL_NOT
	0x61: 2,  # START_SCRIPT
	0x62: 2,  # CALL_SCRIPT
	0x64: 1,  # JUMP
	0x65: 0,  # RETURN
	0x66: 1,  # JUMP_NOT_EQUAL
	0x67: 0,  # SIGNAL
	0x68: 1,  # SET_SIGNAL_MASK
	0x69: 2,  # LUA_CALL
	0x6A: 2,  # BATCH_LUA
	0x6B: 2,  # LUA_UNSYNCED
	0x90: 0,  # SIGNATURE_LUA (non-executable; skipped by decode walk)
	0x71: 1,  # EXPLODE
	0x72: 1,  # PLAY_SOUND
	0x82: 0,  # SET
	0x83: 0,  # ATTACH_UNIT
	0x84: 0,  # DROP_UNIT,
}

# Stack delta per opcode (matches stackDelta in RasFile.cpp)
STACK_DELTA = {
	0x21: +1,   # PUSH_CONSTANT
	0x22: +1,   # PUSH_LOCAL_VAR
	0x23: +1,   # PUSH_STATIC
	0x2A: 0,    # PUSH_STATIC_IDX
	0x2B: -2,   # POP_STATIC_IDX
	0x25: -1,   # POP_LOCAL_VAR
	0x26: -1,   # POP_STATIC
	0x27: -1,   # POP_STACK
	0x64: -1,   # JUMP
	0x66: -1,   # JUMP_NOT_EQUAL
	0x06: -1,   # HIDE
	0x0D: -1,   # SHADE
	0x0E: -1,   # DONT_SHADE
	0x28: -1,   # CACHE
	0x29: -1,   # DONT_CACHE
	0x71: -1,   # EXPLODE
	0x72: -1,   # PLAY_SOUND
	0x0F: -1,   # EMIT_SFX
	0x38: -1,   # BITWISE_NOT
	0x5A: -1,   # LOGICAL_NOT
	0x68: -1,   # SET_SIGNAL_MASK
	0x67: -1,   # SIGNAL
	0x84: -1,   # DROP_UNIT
	0x31: -1,   # ADD
	0x32: -1,   # SUB
	0x33: -1,   # MUL
	0x34: -1,   # DIV
	0x30: -1,   # MOD
	0x35: -1,   # BITWISE_AND
	0x36: -1,   # BITWISE_OR
	0x37: -1,   # BITWISE_XOR
	0x51: -1,   # SET_LESS
	0x52: -1,   # SET_LESS_OR_EQUAL
	0x53: -1,   # SET_GREATER
	0x54: -1,   # SET_GREATER_OR_EQUAL
	0x55: -1,   # SET_EQUAL
	0x56: -1,   # SET_NOT_EQUAL
	0x57: -1,   # LOGICAL_AND
	0x58: -1,   # LOGICAL_OR
	0x59: -1,   # LOGICAL_XOR
	0x3A: -1,   # MINIMUM
	0x3B: -1,   # MAXIMUM
	0x41: -1,   # RAND
	0x3D: -2,   # CLAMP
	0x43: -4,   # GET
	0x42: 0,    # GET_UNIT_VALUE
	0x39: 0,    # ABSOLUTE
	0x3C: 0,    # SIGN
	0x3E: -1,   # DELTAHEADING (reserved: pop2 push1)
	0x3F: 0,    # MSINE        (reserved: pop1 push1)
	0x40: 0,    # MCOSINE      (reserved: pop1 push1)
	0x4B: 0,    # ADDI
	0x4C: 0,    # MULI
	0x61: -2,   # START_SCRIPT
	0x83: -3,   # ATTACH_UNIT
	0x82: -2,   # SET
	0x01: -2,   # MOVE
	0x02: -2,   # TURN
	0x0B: -1,   # MOVE_NOW
	0x0C: -1,   # TURN_NOW
	0x0A: -2,   # SCALE
	0x10: -1,   # SCALE_NOW
	0x4F: -1,   # EXPLODE_REL
	0x4D: -2,   # TURN_REL
	0x4E: -2,   # MOVE_REL
	0x50: -2,   # SCALE_REL
	0x03: -2,   # SPIN
	0x04: -2,   # STOP_SPIN
	0x05: -1,   # SHOW
	0x13: 0,    # SLEEP
	0x11: 0,    # WAIT_FOR_TURN
	0x12: 0,    # WAIT_FOR_MOVE
	0x14: 0,    # WAIT_FOR_SCALE
	0x24: 0,    # CREATE_LOCAL_VAR
	0x65: 0,    # RETURN
	0x69: 0,    # LUA_CALL
	0x6A: 0,    # BATCH_LUA
	0x6B: 0,    # LUA_UNSYNCED
	0x62: 0,    # CALL_SCRIPT
	0x90: 0,    # SIGNATURE_LUA
}

# Unsafe opcodes (touch global/shared state)
# Must mirror RasOpIsThreadSafe() in RasOpCodes.h
UNSAFE_OPCODES = {
	0x69,   # LUA_CALL (synced Lua)
	0x90,   # SIGNATURE_LUA
	0x71,   # EXPLODE (uses global gsRNG)
	0x4F,   # EXPLODE_REL
	0x0F,   # EMIT_SFX
	0x83,   # ATTACH_UNIT
	0x84,   # DROP_UNIT
	0x82,   # SET (may target cross-unit value-ids)
}

# Operator mapping
OPS = {
	'+' : OPCODES['ADD'],
	'-' : OPCODES['SUB'],
	'*' : OPCODES['MUL'],
	'/' : OPCODES['DIV'],
	'%' : OPCODES['MOD'],
	'&' : OPCODES['BITWISE_AND'],
	'|' : OPCODES['BITWISE_OR'],
	'^' : OPCODES['BITWISE_XOR'],
	'<' : OPCODES['SET_LESS'],
	'>' : OPCODES['SET_GREATER'],
	'==' : OPCODES['SET_EQUAL'],
	'<=' : OPCODES['SET_LESS_OR_EQUAL'],
	'>=' : OPCODES['SET_GREATER_OR_EQUAL'],
	'!=' : OPCODES['SET_NOT_EQUAL'],
	'&&' : OPCODES['LOGICAL_AND'],
	'||' : OPCODES['LOGICAL_OR'],
	'^^' : OPCODES['LOGICAL_XOR'],
	'AND' : OPCODES['LOGICAL_AND'],
	'and' : OPCODES['LOGICAL_AND'],
	'OR' : OPCODES['LOGICAL_OR'],
	'or' : OPCODES['LOGICAL_OR'],
	'XOR' : OPCODES['LOGICAL_XOR'],
	'xor' : OPCODES['LOGICAL_XOR'],
}

OPS_PYEVAL = {
	"+" : "+",
	"-" : "-",
	"*" : "*",
	"/" : "/",
	"&" : "&&",
	"|" : "||",
	"^" : "^^",
	"%" : "%",
}

OPS_PYEVAL_PRECEDENCE = ["%", "*", "/", "+", "-", "|", "&", "^"]

OPS_PRECEDENCE = {
	'*' : 1,
	'/' : 1,
	'%' : 1,
	'+' : 2,
	'-' : 2,
	'<' : 3,
	'>' : 3,
	'<=' : 3,
	'>=' : 3,
	'==' : 4,
	'!=' : 4,
	'&' : 5,
	'^' : 6,
	'|' : 7,
	'&&' : 8,
	'AND' : 8,
	'and' : 8,
	'||' : 9,
	'OR' : 9,
	'or' : 9,
	'^^' : 10,
	'XOR' : 10,
	'xor' : 10,
}

UNARY_OPS = {
	'NOT' : OPCODES['LOGICAL_NOT'],
	'!' : OPCODES['LOGICAL_NOT'],
}

RAS_EXT = 'ras'        # Source files
RAS_EXT = 'ras'
RASC_EXT = 'rasc'      # Compiled binary files

PRINTED_NODES = {'keyword', 'symbol', 'integerConstant', 'floatConstant', 'identifier',
				 'argumentList', 'staticVarDec', 'pieceDec', 'localVarDec',
				 'funcDec', 'funcBody', 'ifStatement', 'whileStatement', 'forStatement',
				 'callStatement',
				 'startStatement',
				 'spinStatement',
				 'stopSpinStatement',
				 'turnStatement',
				 'moveStatement',
				 'scaleStatement',
				 'waitForTurnStatement',
				 'waitForMoveStatement',
				 'waitForScaleStatement',
				 'emitSfxStatement',
				 'sleepStatement',
				 'hideStatement',
				 'showStatement',
				 'explodeStatement',
				 'signalStatement',
				 'setSignalMaskStatement',
				 'setStatement',
				 'getStatement',
				 'attachUnitStatement',
				 'dropUnitStatement',
				 'returnStatement',
				 'expression', 'term',
				 'expressionList'}

def escape(s):
	return s.replace('&','&amp;').replace('>','&gt;').replace('<','&lt;').replace('\"','&quot;')


class Node(object):
	def __init__(self, node_type, text=None):
		self._type = node_type
		self._text = text
		self._children = []
		self._note = ""

	def add_child(self, child):
		self._children.append(child)

	def clear(self):
		self._children = []

	def print_node(self, indent=0, out_file=sys.stdout, verbose=False):
		if verbose or self._type in PRINTED_NODES:
			indentation = '  ' * indent
			if self._text is not None:
				out_file.write("%s<%s> %s </%s> %s\n" %
							   (indentation, self._type, escape(self._text),
								self._type, self._note))
			else:
				out_file.write("%s<%s>\n %s" % (indentation, self._type, self._note))
				for child in self._children:
					child.print_node(indent + 1, out_file=out_file, verbose=verbose)
				out_file.write("%s</%s>\n%s" % (indentation, self._type, self._note))
		else:
			for child in self._children:
				child.print_node(indent, out_file=out_file, verbose=verbose)

	def term_is_a_signedFloatConstant(self):
		if self._type == "term" and len(self._children) == 1:
			child = self._children[0]
			if child._type == "constant" and len(child._children) == 1:
				child = child._children[0]
				if child._type == "signedFloatConstant" and len(child._children) == 1:
					child = child._children[0]
					if child._type == "floatConstant" and len(child._children) == 0:
						return child
		return None

	def fold_node(self, depth=0):
		foldcount = 0
		for child in self._children:
			foldcount += child.fold_node(depth + 1)

		foldedone = True
		while (foldedone):
			foldedone = False

			if self._type == "signedFloatConstant" and len(self._children) == 2 \
					and self._children[0]._text == '-':
				self._children.pop(0)
				self._children[0]._text = '-' + self._children[0]._text

			if self._type == "constant" and len(self._children) == 3:
				sym1 = self._children[0]._text
				sym2 = self._children[2]._text
				if sym1 == '[' and sym2 == ']':
					self._children.pop(2)
					self._children.pop(0)
					self._children[0]._children[0]._text = str(
						float(self._children[0]._children[0]._text) * LINEAR_SCALE)
				if sym1 == '<' and sym2 == '>':
					self._children.pop(2)
					self._children.pop(0)
					self._children[0]._children[0]._text = str(
						float(self._children[0]._children[0]._text) * ANGULAR_SCALE)

			if self._type == 'expression' and len(self._children) >= 2:
				for pyop in OPS_PYEVAL_PRECEDENCE:
					i = 0
					while (i < len(self._children) - 1):
						if (i + 1) >= len(self._children):
							break
						term1 = self._children[i].term_is_a_signedFloatConstant()
						if not term1 and self._children[i]._type == 'opterm' \
								and self._children[i]._children[1].term_is_a_signedFloatConstant():
							term1 = self._children[i]._children[1].term_is_a_signedFloatConstant()
						if term1 is None:
							i += 1
							continue

						opterm = self._children[i + 1]
						if opterm._children[0]._type != "op" or len(opterm._children) < 2:
							i += 1
							continue

						term2 = opterm._children[1].term_is_a_signedFloatConstant()
						if term2 is None:
							i += 1
							continue

						op = opterm._children[0]._children[0]._text
						if op != pyop:
							i += 1
							continue

						try:
							expr = term1._text + ' ' + op + ' ' + term2._text
							result = eval(expr)
							if op == '/' and abs(float(result)) < 1 and float(term1._text) != 0:
								print("Warning: A division folding resulted in < 1 result", expr)
								raise
							term1._text = str(result)
							self._children.pop(i + 1)
							foldcount += 1
							foldedone = True
						except:
							i += 1
							print("Warning: Cant evaluate expression", expr)

			if self._type == "term" and len(self._children) == 3:
				symbolstart = self._children[0]
				symbolend = self._children[2]
				expression = self._children[1]
				if symbolstart._type == "symbol" and symbolend._type == "symbol" \
						and len(expression._children) == 1:
					newterm = expression._children[0].term_is_a_signedFloatConstant()
					if newterm is not None:
						self._children = [expression._children[0]._children[0]]
						foldcount += 1
						foldedone = True

			return foldcount

	def __getitem__(self, i):
		return self._children[i]

	def __len__(self):
		return len(self._children)

	def get_children(self):
		return self._children

	def get_type(self):
		return self._type

	def get_text(self):
		if self._text is None:
			return "".join(c.get_text() for c in self._children)
		return self._text

	def count_descendants(self):
		d = 1
		for child in self._children:
			d += child.count_descendants()
		return d

	def __repr__(self):
		return f'{self._type}:{self.count_descendants()}/{len(self._children)}:{self._text}'


def parse_string(pump, node):
	token = pump.next()
	if type(token) == tuple:
		token = token[0]
	if len(token) == 0:
		return False
	if token.startswith("\""):
		node.add_child(Node('stringConstant', token.strip('\"')))
		return True
	return False


def parse_int(pump, node):
	token = pump.next()
	if type(token) == tuple:
		token = token[0]
	if len(token) == 0:
		return False
	if token.startswith("0x"):
		try:
			token = str(int(token, 16))
			node.add_child(Node('integerConstant', token))
			return True
		except:
			return False
	if token.isdigit():
		node.add_child(Node('integerConstant', token))
		return True
	return False


def parse_identifier(pump, node):
	token = pump.next()
	if type(token) == tuple:
		token = token[0]
	if len(token) == 0:
		return False
	if token[0].isalpha() or token[0] == '_':
		node.add_child(Node('identifier', token))
		return True
	return False


def parse_float(pump, node):
	token = pump.next()
	if type(token) == tuple:
		token = token[0]
	if len(token) == 0:
		return False
	if token.count(".") > 1:
		return False
	if token.replace(".", "").isdigit():
		node.add_child(Node('floatConstant', token))
		return True
	return False


ELEMENTS_DICT = {
	'keyword': ('piece', 'static', 'var', 'while', 'for', 'if', 'else', 'return',
				'call', 'start', 'script', 'spin', 'stop', 'turn', 'move', 'scale', 'wait',
				'from', 'to', 'along', 'around', 'x', 'y', 'z', 'axis', 'speed', 'now',
				'accelerate', 'decelerate',
				'hide', 'show', 'set', 'get', 'explode', 'signal', 'mask', 'emit', 'sfx',
				'type', 'sleep',
				'attach', 'drop', 'unit', 'rand', 'unknown_unit_value',
				'dont', 'cache', 'shade', 'shadow', 'play', 'sound'),
	'symbol': ('{', '}', '(', ')', '[', ']', ',', ';', '+', '-', '*', '/', '%', '&', '|', '^',
			   '<', '>', '=', '!', 'xor', 'or', 'and', 'not'),
}

ATOMS_DICT = {
	'_integerConstant': parse_int,
	'_floatConstant': parse_float,
	'_stringConstant': parse_string,
	'_identifier': parse_identifier,
}

PARSER_DICT = {
	'_file': (('_declaration~',),),
	'_declaration': (('_pieceDec',), ('_staticVarDec',), ('_funcDec',),),
	'_pieceDec': (('piece', '_pieceName', '_commaPiece~', ';',),),
	'_commaPiece': ((',', '_pieceName',),),
	'_pieceName': (('_identifier',),),
	'_staticVarDec': (('static', '-', 'var', '_varName', '_commaVar~', ';',),),
	'_commaVar': ((',', '_varName',),),
	'_varName': (('_identifier',),),
	'_funcDec': (('_funcName', '(', '_argumentList', ')', '_statementBlock',),),
	'_funcName': (('_identifier',),),
	'_argumentList': (('_arguments?',),),
	'_arguments': (('_varName', '_commaVar~',),),

	'_statement': (('_keywordStatement', ';',), ('_varStatement', ';',),
				   ('_ifStatement',), ('_whileStatement',), ('_forStatement',),
				   ('_assignStatement', ';',), (';',),),
	'_assignStatement': (('_varName', '=', '_expression',), ('_incStatement',), ('_decStatement',),),
	'_incStatement': (('+', '+', '_varName',),),
	'_decStatement': (('-', '-', '_varName',),),
	'_ifStatement': (('if', '(', '_expression', ')', '_statementBlock', '_elseBlock?',),),
	'_elseBlock': (('else', '_statementBlock',),),
	'_whileStatement': (('while', '(', '_expression', ')', '_statementBlock',),),
	'_forStatement': (('for', '(', '_expression', ';', '_expression', ';', '_expression',
					   ';?', ')', '_statementBlock',),),
	'_statementBlock': (('{', '_statement~', '}',), ('_statement',),),

	'_keywordStatement': (
		('_callStatement',),
		('_startStatement',),
		('_spinStatement',),
		('_stopSpinStatement',),
		('_turnStatement',),
		('_moveStatement',),
		('_scaleStatement',),
		('_waitForTurnStatement',),
		('_waitForMoveStatement',),
		('_waitForScaleStatement',),
		('_emitSfxStatement',),
		('_sleepStatement',),
		('_hideStatement',),
		('_showStatement',),
		('_explodeStatement',),
		('_signalStatement',),
		('_setSignalMaskStatement',),
		('_setStatement',),
		('_getStatement',),
		('_attachUnitStatement',),
		('_dropUnitStatement',),
		('_returnStatement',),
		('_playSoundStatement',),
		('_cacheStatement',),
		('_dontCacheStatement',),
		('_dontShadowStatement',),
		('_dontShadeStatement',),
	),

	'_varStatement': (('var', '_arguments',),),
	'_callStatement': (('call', '-', 'script', '_funcName', '(', '_expressionList', ')',),),
	'_startStatement': (('start', '-', 'script', '_funcName', '(', '_expressionList', ')',),),
	'_spinStatement': (('spin', '_pieceName', 'around', '_axis', 'speed', '_expression',
						'_optionalAcceleration'),),
	'_optionalAcceleration': (('_acceleration?',),),
	'_acceleration': (('accelerate', '_expression',),),
	'_stopSpinStatement': (('stop', '-', 'spin', '_pieceName', 'around', '_axis',
							'_optionalDeceleration'),),
	'_optionalDeceleration': (('_deceleration?',),),
	'_deceleration': (('decelerate', '_expression',),),
	'_turnStatement': (('turn', '_pieceName', 'to', '_axis', '_expression', '_speedNow'),),
	'_moveStatement': (('move', '_pieceName', 'to', '_axis', '_expression', '_speedNow'),),
	'_scaleStatement': (('scale', '_pieceName', 'to', '_axis', '_expression', '_speedNow'),),
	'_speedNow': (('now',), ('speed', '_expression',),),

	'_waitForTurnStatement': (('wait', '-', 'for', '-', 'turn', '_pieceName', 'around',
								'_axis'),),
	'_waitForMoveStatement': (('wait', '-', 'for', '-', 'move', '_pieceName', 'along',
							   '_axis'),),
	'_waitForScaleStatement': (('wait', '-', 'for', '-', 'scale', '_pieceName', 'along',
								'_axis'),),

	'_emitSfxStatement': (('emit', '-', 'sfx', '_expression', 'from', '_pieceName'),),
	'_sleepStatement': (('sleep', '_expression'),),
	'_hideStatement': (('hide', '_pieceName'),),
	'_showStatement': (('show', '_pieceName'),),
	'_explodeStatement': (('explode', '_pieceName', 'type', '_expression'),),
	'_signalStatement': (('signal', '_expression'),),
	'_setSignalMaskStatement': (('set', '-', 'signal', '-', 'mask', '_expression'),),
	'_setStatement': (('set', '_expression', 'to', '_expression'),),
	'_getStatement': (('_get',),),
	'_attachUnitStatement': (('attach', '-', 'unit', '_expression', 'to', '_expression'),),
	'_dropUnitStatement': (('drop', '-', 'unit', '_expression'),),
	'_returnStatement': (('return', '_optionalExpression'),),

	'_cacheStatement': (('cache', '_pieceName'),),
	'_dontCacheStatement': (('dont', '-', 'cache', '_pieceName'),),
	'_dontShadowStatement': (('dont', '-', 'shadow', '_pieceName'),),
	'_dontShadeStatement': (('dont', '-', 'shade', '_pieceName'),),

	'_playSoundStatement': (('play', '-', 'sound', '(', '_stringConstant', '_commaExpression',
							 ')'),),

	'_axis': (('_axisLetter', '-', 'axis'),),
	'_axisLetter': (('x',), ('y',), ('z',),),
	'_expressionList': (('_expressions?',),),
	'_expressions': (('_expression', '_commaExpression~'),),
	'_commaExpression': ((',', '_expression'),),
	'_optionalCommaExpression': (('_commaExpression?',),),
	'_expression': (('_term', '_opterm~'),),
	'_optionalExpression': (('_expression?',),),
	'_term': (('_get',), ('_rand',), ('(', '_expression', ')',), ('_unaryOp', '_term',),
			  ('_varName',), ('_constant',),),
	'_get': (('get', '_term', '(', '_expression', '_optionalCommaExpression',
			  '_optionalCommaExpression', '_optionalCommaExpression', ')',),
			 ('get', '_term',),),
	'_rand': (('rand', '(', '_expression', ',', '_expression', ')',),),
	'_opterm': (('_op', '_term',),),
	'_unaryOp': (('!',), ('NOT',),),
	'_op': (('=', '=',), ('<', '=',), ('>', '=',), ('!', '=',), ('^', '^',), ('|', '|',),
			('&', '&',), ('+',), ('-',), ('*',), ('/',), ('%',), ('&',), ('|',), ('^',),
			('<',), ('>',), ('XOR',), ('OR',), ('AND',),),
	'_constant': (('<', '_signedFloatConstant', '>',),
				  ('[', '_signedFloatConstant', ']',),
				  ('_signedFloatConstant',), ('_signedIntegerConstant',),),
	'_signedFloatConstant': (('-', '_floatConstant',), ('_floatConstant',),),
	'_signedIntegerConstant': (('-', '_integerConstant',), ('_integerConstant',),),
}

AXES = ('x', 'y', 'z')
IGNORED_SYMBOLS = (';', '(', ')', '{', '}', ',')
IGNORED_KEYWORDS = ('accelerate', 'decelerate')


# ============================================================================
# RASC Compiler: emits RasInstr structs directly (pre-decoded format)
# ============================================================================
class RascCompiler(object):
	def __init__(self, tree):
		self._static_vars = []
		self._local_vars = []
		self._pieces = []
		self._functions = []
		self._instructions = []  # list of (op, flags, a, b) tuples
		self._functions_instrs = {}  # func_name -> list of (op, flags, a, b)
		self._func_start_offset = {}  # func_name -> instruction index in global stream
		self._func_max_stack = {}  # func_name -> max stack depth
		self._func_is_lua = {}  # func_name -> bool
		self._compile_funcs = {
			'file': self.parse_file,
			'staticVarDec': self.parse_staticVarDec,
			'pieceDec': self.parse_pieceDec,
			'funcDec': self.parse_funcDec,
			'arguments': self.parse_arguments,
			'assignStatement': self.parse_assignStatement,
			'incStatement': self.parse_incStatement,
			'decStatement': self.parse_decStatement,
			'keywordStatement': self.parse_keywordStatement,
			'varStatement': self.parse_varStatement,
			'rand': self.parse_rand,
			'get': self.parse_get,
			'ifStatement': self.parse_ifStatement,
			'whileStatement': self.parse_whileStatement,
			'term': self.parse_term,
			'unaryOp': self.parse_unaryOp,
			'constant': self.parse_constant,
			'expression': self.parse_expression,
			'symbol': self.parse_symbol,
			'keyword': self.parse_keyword,
		}
		self._vars_to_push = (
			(self._local_vars, OPCODES["PUSH_LOCAL_VAR"]),
			(self._static_vars, OPCODES["PUSH_STATIC"]),
			(self._pieces, OPCODES["PUSH_CONSTANT"]),
		)
		self._vars_to_pop = (
			(self._local_vars, OPCODES["POP_LOCAL_VAR"]),
			(self._static_vars, OPCODES["POP_STATIC"]),
		)
		# Jump fixup list: (instr_index_in_current_func, target_func_name_or_None)
		self._jump_fixups = []
		self._call_fixups = []  # (instr_index, func_name) for CALL resolution

		self.parse(tree)
		self._resolve_fixups()

	def _emit(self, op, a=0, b=0):
		self._instructions.append((op, 0, a, b))

	def _current_instr_idx(self):
		return len(self._instructions)

	def _get_operand_count(self, op):
		return OP_OPERANDS.get(op, 0)

	def _stack_delta(self, op):
		return STACK_DELTA.get(op, 0)

	def _is_unsafe(self, op):
		return op in UNSAFE_OPCODES

	def parse(self, node):
		node_type = node.get_type()
		if node_type in self._compile_funcs:
			self._compile_funcs[node_type](node)
		else:
			self.parse_children(node)

	def parse_children(self, node):
		if len(node.get_children()) == 0:
			raise Exception("node not handled %s: %s" % (node.get_type(), node.get_text()))
		for child in node.get_children():
			self.parse(child)

	def parse_file(self, node):
		for child_node in node.get_children():
			if child_node[0].get_type() == 'funcDec':
				function_name = child_node[0][0].get_text()
				if function_name in self._functions:
					raise Exception("Function %s already defined." % function_name)
				self._functions.append(function_name)
		self.parse_children(node)

	def parse_staticVarDec(self, node):
		static_var_name = node[3].get_text()
		if static_var_name in self._static_vars:
			raise Exception("Static-var %s already exists." % static_var_name)
		self._static_vars.append(static_var_name)
		for comma_var in node.get_children()[4:]:
			if comma_var.get_type() == 'commaVar':
				static_var_name = comma_var[1].get_text()
				if static_var_name in self._static_vars:
					raise Exception("Static-var %s already exists." % static_var_name)
				self._static_vars.append(static_var_name)

	def parse_pieceDec(self, node):
		piece_name = node[1].get_text()
		if piece_name in self._pieces:
			raise Exception("Piece name %s already exists." % piece_name)
		self._pieces.append(piece_name)
		for comma_piece in node.get_children()[2:]:
			if comma_piece.get_type() == 'commaPiece':
				piece_name = comma_piece[1].get_text()
				if piece_name in self._pieces:
					raise Exception("Piece name %s already exists." % piece_name)
				self._pieces.append(piece_name)

	def parse_funcDec(self, node):
		del self._local_vars[0:]
		func_instrs_start = len(self._instructions)
		func_name = node[0].get_text()

		# Check if this is a Lua signature function
		is_lua = (func_name.startswith("lua_synced_")
		           or func_name.startswith("lua_unsynced_")
		           or func_name.startswith("SignatureLua"))
		self._func_is_lua[func_name] = is_lua

		if len(node[2].get_children()) > 0:
			self.parse(node[2])

		if not is_lua:
			self.parse(node[4])
			# Insert implicit return if necessary
			if not self._instructions or self._instructions[-1][0] != OPCODES['RETURN']:
				self._emit(OPCODES['PUSH_CONSTANT'], 0)
				self._emit(OPCODES['RETURN'])
		else:
			# Reserve the slot the loader expects for a Lua signature function
			# so absolute jump targets in later functions stay correct.
			self._emit(OPCODES['SIGNATURE_LUA'])

		func_instrs = self._instructions[func_instrs_start:]
		self._func_start_offset[func_name] = func_instrs_start
		self._functions_instrs[func_name] = func_instrs

		# Compute max stack depth for this function
		stack = 0
		max_depth = 0
		for (op, flags, a, b) in func_instrs:
			stack += self._stack_delta(op)
			if stack < 0:
				stack = 0
			if stack > max_depth:
				max_depth = stack
		self._func_max_stack[func_name] = max_depth

	def parse_varStatement(self, node):
		self.parse(node[1])

	def parse_arguments(self, node):
		if len(node.get_children()) == 0:
			return
		local_var_name = node[0].get_text()
		if local_var_name in self._static_vars:
			raise Exception('Static-var named "%s" already exists.' % local_var_name)
		if local_var_name in self._local_vars:
			raise Exception('Local-var named "%s" already exists.' % local_var_name)
		self._local_vars.append(node[0].get_text())
		self._emit(OPCODES['CREATE_LOCAL_VAR'])
		for comma_var in node.get_children()[1:]:
			if comma_var.get_type() == 'commaVar':
				local_var_name = comma_var[1].get_text()
				if local_var_name in self._static_vars:
					raise Exception('Static-var named "%s" already exists.' % local_var_name)
				if local_var_name in self._local_vars:
					raise Exception('Local-var named "%s" already exists.' % local_var_name)
				self._local_vars.append(comma_var[1].get_text())
				self._emit(OPCODES['CREATE_LOCAL_VAR'])

	def parse_assignStatement(self, node):
		if len(node.get_children()) < 3:
			self.parse_children(node)
			return
		self.parse(node[2])
		self._emit_var(node[0].get_text(), False)

	def parse_incStatement(self, node):
		self._emit_var(node[2].get_text(), True)
		self._emit(OPCODES['PUSH_CONSTANT'], 1)
		self._emit(OPCODES['ADD'])
		self._emit_var(node[2].get_text(), False)

	def parse_decStatement(self, node):
		self._emit_var(node[2].get_text(), True)
		self._emit(OPCODES['PUSH_CONSTANT'], 1)
		self._emit(OPCODES['SUB'])
		self._emit_var(node[2].get_text(), False)

	def parse_keywordStatement(self, node):
		node = node[0]

		if len(node[0].get_children()) > 0 and node[0][0].get_text() == 'get':
			self.parse(node)
			self._emit(OPCODES['POP_STACK'])
			return

		keyword = node[0].get_text()
		i = 0
		while node[i + 1].get_text() == '-':
			keyword += '-%s' % (node[i + 2].get_text())
			i += 2

		if keyword == 'set' or keyword == 'attach-unit':
			children = node.get_children()
		else:
			children = node.get_children()[::-1]

		arguments = []
		for child_node in children:
			if child_node.get_type() == 'pieceName':
				piece_name = child_node.get_text()
				piece_index = self._case_insensitive_index(self._pieces, piece_name)
				if piece_index < 0:
					raise Exception('Piece not found: %s' % piece_name)
				arguments.append(piece_index)
			elif child_node.get_type() == 'funcName':
				func_name = child_node.get_text()
				func_index = self._case_insensitive_index(self._functions, func_name)
				if func_index < 0:
					raise Exception("Function not found: %s" % func_name)
				arguments.append(func_index)
			elif child_node.get_type() == 'axis':
				arguments.append(AXES.index(child_node[0].get_text()))
			elif child_node.get_type() == 'expression':
				self.parse(child_node)
			elif child_node.get_type() == 'expressionList':
				if len(child_node.get_children()) > 0:
					self.parse(child_node[0])
					arguments.append(len(child_node[0].get_children()))
				else:
					arguments.append(0)
			elif child_node.get_type() == 'speedNow':
				if child_node[0].get_text() == 'now':
					keyword += "-now"
				else:
					self.parse(child_node[1])
			elif child_node.get_type().startswith('optional'):
				if len(child_node.get_children()) == 0:
					self._emit(OPCODES['PUSH_CONSTANT'], 0)
				else:
					self.parse_children(child_node)
			elif child_node.get_type() == 'stringConstant':
				# For play-sound: string goes into operand
				pass

		if keyword == 'attach-unit':
			self._emit(OPCODES['PUSH_CONSTANT'], 0)

		opcode_name = keyword.upper().replace("-", "_")
		if opcode_name not in OPCODES:
			raise Exception('Unhandled keyword %s %s' % (keyword, opcode_name))

		op = OPCODES[opcode_name]

		# Build operand values from collected arguments
		operands = arguments[::-1]
		a = operands[0] if len(operands) > 0 else 0
		b = operands[1] if len(operands) > 1 else 0

		# For CALL_SCRIPT, record for later resolution
		if opcode_name == 'CALL_SCRIPT':
			self._emit(op, a, b)
		else:
			self._emit(op, a, b)

	def parse_get(self, node):
		num_expressions = 0
		for child_node in node.get_children()[1:]:
			if child_node.get_type() == 'expression' or child_node.get_type() == 'term':
				self.parse(child_node)
				num_expressions += 1
			elif child_node.get_type().startswith('optional'):
				num_expressions += 1
				if len(child_node.get_children()) == 0:
					self._emit(OPCODES['PUSH_CONSTANT'], 0)
				else:
					self.parse_children(child_node)

		if num_expressions == 1:
			self._emit(OPCODES['GET_UNIT_VALUE'])
		else:
			self._emit(OPCODES['GET'])

	def parse_rand(self, node):
		self.parse(node[2])
		self.parse(node[4])
		self._emit(OPCODES['RAND'])

	def parse_ifStatement(self, node):
		has_else = len(node.get_children()) > 5
		self.parse(node[2])
		self._emit(OPCODES['JUMP_NOT_EQUAL'], 0)  # placeholder
		jne_idx = self._current_instr_idx() - 1

		self.parse(node[4])

		else_target = self._current_instr_idx()
		if has_else:
			self._emit(OPCODES['JUMP'], 0)  # placeholder
			jump_idx = self._current_instr_idx() - 1
			self.parse(node[5][1])

			# Fix up else jump target
			self._fixup_instr(jump_idx, self._current_instr_idx())
		# Fix up JNE target
		self._fixup_instr(jne_idx, else_target)

	def parse_expression(self, node):
		self.parse(node[0])
		if len(node.get_children()) == 1:
			return
		op_stack = []
		for op_term in node.get_children()[1:]:
			op = op_term[0].get_text()
			while len(op_stack) > 0 and OPS_PRECEDENCE[op_stack[-1]] <= OPS_PRECEDENCE[op]:
				self._emit(OPS[op_stack.pop()])
			self.parse(op_term[1])
			op_stack.append(op)
		while len(op_stack) > 0:
			self._emit(OPS[op_stack.pop()])

	def parse_whileStatement(self, node):
		start = self._current_instr_idx()
		self.parse(node[2])
		self._emit(OPCODES['JUMP_NOT_EQUAL'], 0)
		jne_idx = self._current_instr_idx() - 1
		self.parse(node[4])
		self._emit(OPCODES['JUMP'], start)
		self._fixup_instr(jne_idx, self._current_instr_idx())

	def parse_term(self, node):
		if node[0].get_type() == 'unaryOp':
			self.parse(node[1])
			self.parse(node[0])
		elif node[0].get_type() == 'varName':
			self._emit_var(node[0].get_text(), True)
		else:
			self.parse_children(node)

	def parse_constant(self, node):
		self._emit(OPCODES['PUSH_CONSTANT'])
		if len(node.get_children()) == 1:
			value = round(float(node.get_text()))
			self._instructions[-1] = (OPCODES['PUSH_CONSTANT'], 0, int(value), 0)
		else:
			if node[0].get_text() == '[':
				value = int(LINEAR_SCALE * float(node[1].get_text()))
			elif node[0].get_text() == '<':
				value = int(ANGULAR_SCALE * float(node[1].get_text()))
			else:
				raise Exception("Unhandled fancy number: %s" % node.get_text())
			self._instructions[-1] = (OPCODES['PUSH_CONSTANT'], 0, int(value), 0)

	def parse_unaryOp(self, node):
		self._emit(UNARY_OPS[node.get_text()])

	def parse_symbol(self, node):
		symbol = node.get_text()
		if symbol not in IGNORED_SYMBOLS:
			raise Exception("Unhandled symbol %s" % symbol)

	def parse_keyword(self, node):
		keyword = node.get_text()
		if keyword not in IGNORED_KEYWORDS:
			raise Exception("Unhandled keyword %s" % keyword)

	def _emit_var(self, var_name, push):
		if push:
			opcodes = self._vars_to_push
		else:
			opcodes = self._vars_to_pop
		for vars_list, opcode in opcodes:
			i = self._case_insensitive_index(vars_list, var_name)
			if i < 0:
				continue
			self._emit(opcode, i)
			return
		raise Exception("Var not found: %s" % var_name)

	def _case_insensitive_index(self, iterable, s):
		l = s.lower()
		for i, v in enumerate(iterable):
			if v.lower() == l:
				return i
		return -1

	def _fixup_instr(self, idx, target):
		if idx < 0 or idx >= len(self._instructions):
			return
		op, flags, a, b = self._instructions[idx]
		self._instructions[idx] = (op, flags, target, b)

	def _resolve_fixups(self):
		# CALL_SCRIPT resolution handled in get_rasc_data()
		pass

	def _analyze_thread_safety(self):
		"""Recursion-safe thread-safety analysis (Part V of RASC_PLANS.md).

		Start every function SAFE, then propagate UNSAFE for any function with
		an unsafe op or a call to an unsafe/lua function. Pure recursive cycles
		stay safe (growing safety from False would deadlock cycles as unsafe)."""
		num_funcs = len(self._functions)
		safe = [not self._func_is_lua.get(self._functions[fi], False) for fi in range(num_funcs)]

		changed = True
		while changed:
			changed = False
			for fi in range(num_funcs):
				if not safe[fi]:
					continue
				instrs = self._functions_instrs.get(self._functions[fi], [])
				unsafe = False
				for (op, flags, a, b) in instrs:
					if self._is_unsafe(op):
						unsafe = True
						break
					if op == OPCODES['CALL_SCRIPT']:
						if not (0 <= a < num_funcs) or not safe[a]:
							unsafe = True
							break
				if unsafe:
					safe[fi] = False
					changed = True

		return safe

	def get_rasc_data(self):
		# Resolve CALL_SCRIPT based on target function name prefix:
		#   lua_synced_*   -> LUA_CALL
		#   lua_unsynced_* -> LUA_UNSYNCED
		#   default        -> CALL_SCRIPT (regular function call)
		for fi, fname in enumerate(self._functions):
			resolved = []
			for (op, flags, a, b) in self._functions_instrs.get(fname, []):
				if op == OPCODES['CALL_SCRIPT']:
					target_name = self._functions[a] if 0 <= a < len(self._functions) else ""
					if target_name.startswith("lua_synced_"):
						op = OPCODES['LUA_CALL']
					elif target_name.startswith("lua_unsynced_"):
						op = OPCODES['LUA_UNSYNCED']
					# else: stays as CALL_SCRIPT
				resolved.append((op, flags, a, b))
			self._functions_instrs[fname] = resolved

		# Rebuild global instruction stream
		all_instrs = []
		func_infos = []
		for fname in self._functions:
			is_lua = self._func_is_lua.get(fname, False)
			instrs = self._functions_instrs.get(fname, [])
			decoded_offset = len(all_instrs)
			max_stack = self._func_max_stack.get(fname, 0)

			if is_lua:
				# SIGNATURE_LUA already reserved at compile time
				all_instrs.extend(instrs)
				func_infos.append((decoded_offset, 0, 0, 1))
			else:
				all_instrs.extend(instrs)
				func_infos.append((decoded_offset, max_stack, 0, 0))

		# Thread-safety analysis
		ts_flags = self._analyze_thread_safety()
		for i in range(len(func_infos)):
			dec_off, max_st, ts, is_lua = func_infos[i]
			func_infos[i] = (dec_off, max_st, 1 if ts_flags[i] else 0, is_lua)

		# Print thread-safety results
		for i, fname in enumerate(self._functions):
			flag = "SAFE" if ts_flags[i] else "UNSAFE"
			print("  Thread-safety: %s -> %s" % (fname, flag))

		# Build RASC binary
		rasc = rasc_file.RascFile(
			script_names=self._functions,
			piece_names=self._pieces,
			static_vars=self._static_vars,
			sound_names=[],
			instructions=all_instrs,
			script_infos=func_infos,
		)
		return rasc.get_content(), {
			"numScripts": len(self._functions),
			"numPieces": len(self._pieces),
			"numStaticVars": len(self._static_vars),
			"numInstructions": len(all_instrs),
		}


# ============================================================================
# Lexer / Parser (same as bos2cob)
# ============================================================================
class Pump(object):
	def __init__(self, generator):
		leftovers = []
		for token, idx in generator:
			while (type(token) == tuple):
				token = token[0]
			leftovers.append((token, idx))
		self._leftovers = leftovers
		self._index = 0
		self._max_index = 0

	def next(self):
		if self._index < len(self._leftovers):
			token, idx = self._leftovers[self._index]
			self._index += 1
			self._max_index = max(self._max_index, self._index)
			return token
		else:
			return ""

	def update(self, result, index=0):
		if not result:
			self._index = index

	def get_index(self):
		return self._index


def parse(pump, node, block_type):
	if block_type in ATOMS_DICT:
		return ATOMS_DICT[block_type](pump, node)
	for element_type in ELEMENTS_DICT:
		if block_type.lower() in ELEMENTS_DICT[element_type]:
			next = pump.next()
			if type(next) == type((1, 1)):
				next = next[0]
			if next.lower() == block_type.lower():
				node.add_child(Node(element_type, next))
				return True
			return False
	current_node = Node(block_type.strip('?%_'))
	for alternative in PARSER_DICT[block_type]:
		alternative_correct = True
		index = pump.get_index()
		for child_type in alternative:
			maybe = False
			multiple = False
			if child_type.endswith('~'):
				maybe = True
				multiple = True
			elif child_type.endswith('?'):
				maybe = True
			first = True
			while first or multiple:
				first = False
				result = try_parse(pump, current_node, child_type.strip('?~'))
				if not result:
					break
			if not (result or maybe):
				alternative_correct = False
				break
		if alternative_correct:
			node.add_child(current_node)
			return True
		pump.update(False, index)
		current_node.clear()
	return False


def try_parse(pump, node, block_type):
	index = pump.get_index()
	result = parse(pump, node, block_type)
	pump.update(result, index)
	return result


def token_generator(code):
	symbol_delimiters = ['{', '}', '[', ']', '(', ')', ' ', '&', '|', '^', '+', '-', '*', '/',
						 '%', ',', ';', '<', '>', '=', '!', '#', '\t', '\r', '\n', '\\']
	is_line_comment = False
	is_multi_line_comment = False
	is_in_quotation = False
	is_preprocessor = False
	skip = False

	idx = 0
	prev_idx = 0

	while (idx < len(code)):
		if not is_line_comment and not is_multi_line_comment and not is_in_quotation \
				and code[idx] == '"':
			is_in_quotation = True
			prev_idx = idx
			idx += 1
			continue

		if not is_line_comment and not is_multi_line_comment and is_in_quotation \
				and code[idx] == '"':
			is_in_quotation = False
			idx += 1
			yield code[prev_idx:idx], idx
			prev_idx = idx
			continue

		if not is_line_comment and not is_multi_line_comment and not is_in_quotation \
				and code[idx:idx + 2] == "//":
			is_line_comment = True
			s = code[prev_idx:idx].strip()
			if len(s) > 0:
				yield s, idx
			if is_preprocessor:
				is_preprocessor = False
				yield '$', idx
			idx += 2
			prev_idx = idx
			continue

		if not is_line_comment and not is_multi_line_comment and not is_in_quotation \
				and code[idx:idx + 2] == "/*":
			is_multi_line_comment = True
			s = code[prev_idx:idx].strip()
			if len(s) > 0:
				yield s, idx
			idx += 2
			prev_idx = idx
			continue

		if not is_line_comment and not is_multi_line_comment and not is_in_quotation \
				and not is_preprocessor and code[idx] == "#":
			is_preprocessor = True
			s = code[prev_idx:idx].strip()
			if len(s) > 0:
				yield s, idx
			yield '#', idx
			idx += 1
			prev_idx = idx
			continue

		if not is_line_comment and not is_multi_line_comment and not is_in_quotation \
				and is_preprocessor and code[idx] == "\n" and code[idx - 1:idx] != '\\' \
				and code[idx - 2:idx] != '\\\r':
			is_preprocessor = False
			s = code[prev_idx:idx].strip()
			if len(s) > 0:
				yield s, idx
			yield '$', idx
			idx += 1
			prev_idx = idx
			continue

		if is_line_comment and code[idx:idx + 1] == '\n':
			is_line_comment = False
			idx += 1
			prev_idx = idx
			continue

		if is_multi_line_comment and code[idx:idx + 2] == "*/":
			is_multi_line_comment = False
			idx += 2
			prev_idx = idx
			continue

		skip = is_multi_line_comment or is_line_comment or is_in_quotation
		if not skip and (code[idx] in symbol_delimiters):
			token = code[prev_idx:idx].strip().strip('\\')
			if len(token) > 0:
				yield token, idx
			symbol_token = code[idx:idx + 1].strip().strip('\\')
			if len(symbol_token) > 0:
				yield symbol_token, idx
			idx += 1
			prev_idx = idx
			continue

		idx += 1

	if not skip and idx == len(code):
		token = code[prev_idx:idx].strip()
		prev_idx = idx
		if len(token) > 0:
			yield token, idx
	return


def preprocess(code, include_path, defs={"TRUE": "1", "FALSE": "0",
										 "UNKNOWN_UNIT_VALUE": ""}, recursion=0):
	if recursion > 10:
		print("Error: recursion limit reached")
		sys.exit(1)

	gen = token_generator(code)
	is_preprocessor_directive = False
	skip = 0
	ifs = 0
	while True:
		try:
			token, idx = gen.__next__()
		except Exception:
			if ifs > 0:
				print("Error: Missing #endif at %d" % idx)
				sys.exit(1)
			if is_preprocessor_directive:
				print("Preprocessor error at %d" % idx)
				sys.exit(1)
			break

		if token == '#':
			is_preprocessor_directive = True
			continue
		if token == '$':
			continue
		if not is_preprocessor_directive:
			if skip > 0:
				continue
			if token not in defs:
				yield token, idx
				continue
			for prep_tokens in preprocess(defs[token], include_path, defs, recursion + 1):
				yield prep_tokens, idx
			continue

		is_preprocessor_directive = False

		if token.lower() == 'include':
			if skip > 0:
				continue
			included, idx = gen.__next__()
			included = included.strip('"')
			try:
				if not os.path.exists(included):
					alt_path = os.path.join(include_path, included)
					if not os.path.exists(alt_path):
						print('Error: can\'t find %s at %d' % (included, idx))
						sys.exit(1)
					included = alt_path
				content = open(included, 'r').read()
				for prep_tokens in preprocess(content, include_path, defs, recursion + 1):
					yield prep_tokens, idx
			except:
				print('Error: Couldn\'t include %s at %d' % (included, idx))
				sys.exit(1)
			continue

		if token.lower() == 'define':
			if skip > 0:
				continue
			current_definition, idx = gen.__next__()
			defs[current_definition] = ""
			while True:
				token, idx = gen.__next__()
				if token == '$':
					break
				defs[current_definition] += " " + token
			continue

		if token.lower() == 'undef':
			if skip > 0:
				continue
			current_definition, idx = gen.__next__()
			del defs[current_definition]
			continue

		if token.lower() == 'ifdef':
			ifs += 1
			if skip > 0:
				skip += 1
				continue
			current_definition, idx = gen.__next__()
			if current_definition not in defs:
				skip += 1
			continue

		if token.lower() == 'ifndef':
			ifs += 1
			if skip > 0:
				skip += 1
				continue
			current_definition, idx = gen.__next__()
			if current_definition in defs:
				skip += 1
			continue

		if token.lower() == 'if':
			ifs += 1
			if skip > 0:
				skip += 1
				continue
			query = ""
			while True:
				token, idx = gen.__next__()
				if token == '$':
					break
				else:
					query += token
			query = "".join(preprocess(query, include_path, defs, recursion + 1))
			result = eval(query.strip())
			if not result or result == 0:
				skip += 1
			continue

		if token.lower() == 'else':
			if skip == 1:
				skip = 0
			elif skip == 0:
				skip = 1
			continue

		if token.lower() == 'endif':
			if ifs == 0:
				print("Error: extraneous #endif at %d" % idx)
				sys.exit(1)
			ifs -= 1
			if skip > 0:
				skip -= 1
			continue

		print("Error: unhandled token %s at %d" % (token, idx))
		sys.exit(1)


# pcpp preprocessor (same as bos2cob)
if not args.nopcpp:
	class MyPreprocessor(pcpp.Preprocessor):
		def __init__(self, input_string):
			from pcpp import lextab
			from pcpp.ply.ply import lex
			self.lexer = lex.lex(object=pcpp.parser, lextab=lextab, optimize=True)
			super(MyPreprocessor, self).__init__()
			self.line_directive = None
			self.input = input_string
			self.output = StringIO()

		def preprocess(self):
			self.define("TRUE 1")
			self.define("FALSE 0")
			self.define("UNKNOWN_UNIT_VALUE")
			self.parse(self.input)
			self.write(self.output)
			return self.output.getvalue()

		def on_error(self, file, line, msg):
			print(f"Preprocessor error in file: {file} at line: {line} Error: {msg}")
			sys.exit(1)
			return super().on_error(file, line, msg)()


def main(path, output_path=None):
	if path[-1] == '/':
		input_path = path[:-1]
	else:
		input_path = path
	if not os.path.exists(input_path):
		print("File %s doesn't exist" % input_path)
		sys.exit()
	if os.path.isdir(input_path):
		files = glob(os.path.join(input_path, "*.%s" % RAS_EXT))
	else:
		files = [input_path]
		input_path = os.path.split(input_path)[0]
		if output_path is None:
			output_path = "%s.%s" % (os.path.splitext(input_path)[0], RASC_EXT)

	for rasc_file_path in files:
		print("RASC Compiler v%s - Compiling %s" % (version, rasc_file_path))
		root = Node('root')
		content = open(rasc_file_path, 'r').read()

		if not args.nopcpp:
			pcpp_preproc = MyPreprocessor(content)
			pcpp_preproc.add_path(os.path.dirname(os.path.abspath(rasc_file_path)))
			if args.include:
				pcpp_preproc.add_path(args.include)
			content = pcpp_preproc.preprocess()
			if args.dumppcpp:
				dump_path = rasc_file_path + '.pcpp'
				with open(dump_path, 'w') as f:
					f.write(content)
				print("Wrote preprocessed output to " + dump_path)

		pump = Pump(preprocess(content, input_path, defs={
			"TRUE": "1", "FALSE": "0", "UNKNOWN_UNIT_VALUE": ""}))

		print("Parsing %s" % rasc_file_path)
		result = try_parse(pump, root, '_file')

		if len(pump.next()) != 0:
			print("Leftovers while parsing:")
			print(pump._leftovers[pump._index - 1:pump._max_index],
				  pump._index, pump._max_index)
			print("At: " + ''.join(
				[t[0] for t in pump._leftovers[pump._index - 1:pump._max_index]]))
			print("Syntax Error!")
			lines = content.splitlines()
			for j in range(pump._max_index - 4, pump._max_index):
				word, offset = pump._leftovers[j]
				searchpos = 0
				for i, line in enumerate(lines):
					searchpos += len(line) + 1
					if searchpos > offset:
						print("%d: At line %d (offset = %d) with token %s" %
							  (j, i + 1, offset, word))
						break
			sys.exit(1)

		output_path = "%s.rasc" % os.path.splitext(rasc_file_path)[0]

		if args.dumpast:
			root.print_node(verbose=False, out_file=open(output_path + "_initial.ast", 'w'))

		if not args.dontfold:
			folds = root.fold_node()
			totalfolds = folds
			passes = 0
			while (folds > 0):
				folds = root.fold_node()
				totalfolds += folds
				passes += 1
			if args.dumpast:
				root.print_node(verbose=False,
								out_file=open(output_path + "_folded.ast", 'w'))
			print("Folded %d constants in %d passes" % (totalfolds, passes))

		print("Generating RASC binary for %s" % rasc_file_path)
		comp = RascCompiler(root)
		data, stats = comp.get_rasc_data()

		print("Compile successful: %d instructions, %d scripts, %d pieces, "
			  "%d static-vars" % (
				  stats['numInstructions'],
				  stats['numScripts'],
				  stats['numPieces'],
				  stats['numStaticVars']))
		print("Writing: %s (%d bytes)" % (output_path, len(data)))

		with open(output_path, "wb") as f:
			f.write(data)


if __name__ == '__main__':
	if len(args.filename) > 1:
		main(args.filename)
	else:
		parser.print_help()
		print("Specify a path to a .%s file, or a directory of .%s files" % (RAS_EXT, RAS_EXT))
