#import bos2cob_py3
import cob_file
import struct
import os
import sys

pf = cob_file.PACK_FORMAT
hf = cob_file.COB_HEADER_FIELDS

## Static analysis:
#  stack depth
# call depth?
# instruction pairs


OPCODES = {
	'MOVE'        : 0x10001000,
	'TURN'        : 0x10002000,
	'SCALE'       : 0x100A0000,
	'SPIN'        : 0x10003000,
	'STOP_SPIN'   : 0x10004000,
	'SHOW'        : 0x10005000,
	'HIDE'        : 0x10006000,
	'CACHE'       : 0x10007000,
	'DONT_CACHE'  : 0x10008000,
	'MOVE_NOW'    : 0x1000B000,
	'TURN_NOW'    : 0x1000C000,
	'SCALE_NOW'   : 0x100A1000,
	'SHADE'       : 0x1000D000,
	'DONT_SHADE'  : 0x1000E000,
	'DONT_SHADOW' : 0x1000E000,
	'EMIT_SFX'    : 0x1000F000,

	'WAIT_FOR_TURN'  : 0x10011000,
	'WAIT_FOR_MOVE'  : 0x10012000,
	'WAIT_FOR_SCALE' : 0x100A2000,
	'SLEEP'          : 0x10013000,

	'PUSH_CONSTANT'    : 0x10021001,
	'PUSH_LOCAL_VAR'   : 0x10021002,
	'PUSH_STATIC'      : 0x10021004,
	'CREATE_LOCAL_VAR' : 0x10022000,
	'POP_LOCAL_VAR'    : 0x10023002,
	'POP_STATIC'       : 0x10023004,
	'POP_STACK'        : 0x10024000,

	'ADD'         : 0x10031000,
	'SUB'         : 0x10032000,
	'MUL'         : 0x10033000,
	'DIV'         : 0x10034000,
	'MOD'         : 0x10034001,
	'BITWISE_AND' : 0x10035000,
	'BITWISE_OR'  : 0x10036000,
	'BITWISE_XOR' : 0x10037000,
	'BITWISE_NOT' : 0x10038000,

	'RAND'           : 0x10041000,
	'GET_UNIT_VALUE' : 0x10042000,
	'GET'            : 0x10043000,

	'SET_LESS'             : 0x10051000,
	'SET_LESS_OR_EQUAL'    : 0x10052000,
	'SET_GREATER'          : 0x10053000,
	'SET_GREATER_OR_EQUAL' : 0x10054000,
	'SET_EQUAL'            : 0x10055000,
	'SET_NOT_EQUAL'        : 0x10056000,
	'LOGICAL_AND'          : 0x10057000,
	'LOGICAL_OR'           : 0x10058000,
	'LOGICAL_XOR'          : 0x10059000,
	'LOGICAL_NOT'          : 0x1005A000,

	'START_SCRIPT'    : 0x10061000,
	'CALL_SCRIPT'     : 0x10062000,
	'REAL_CALL'       : 0x10062001,
	'LUA_CALL'        : 0x10062002,
	'JUMP'            : 0x10064000,
	'RETURN'          : 0x10065000,
	'JUMP_NOT_EQUAL'  : 0x10066000,
	'SIGNAL'          : 0x10067000,
	'SET_SIGNAL_MASK' : 0x10068000,

	'EXPLODE'    : 0x10071000,
	'PLAY_SOUND' : 0x10072000,

	'SET'         : 0x10082000,
	'ATTACH_UNIT' : 0x10083000,
	'DROP_UNIT'   : 0x10084000,
}
rop = {}
opargcnt = {} # keyed to opname, value is hist table
for k,v in OPCODES.items():
	rop[v] = k

defines = {}
if os.path.exists('recoil_common_includes.h'):
	for line in open('recoil_common_includes.h','r').readlines():
		if '#define ' in line:
			line = line.partition('#define ')[2].split(None, 1)
			print (line)
			if (len(line) > 1):
				defines[line[0]] = line[1]

def get_name(cob, pos):
	start = pos
	res = b''
	while cob[pos]!= 0:
		#print(cob[pos])
		#res += int.to_bytes(cob[pos])
		pos +=1
	return cob[start:pos]

def get_uint(cob, pos):
	return struct.unpack(pf%1, cob[pos:pos+4])[0]

def decompile(fname):
	cobf = open(fname,'rb').read()
	offset = 0
	header = struct.unpack(cob_file.PACK_FORMAT%(len(cob_file.COB_HEADER_FIELDS)), cobf[0:4*len(hf)])
	print (header)
	hd = {}
	for i in zip(hf, header):
		print (i)
		hd[i[0]] = i[1]

	NumberOfPieces = hd["NumberOfPieces"]
	OffsetToPieceNameOffsetArray = hd['OffsetToPieceNameOffsetArray']
	pieces = []
	for i in range(NumberOfPieces):
		offset = get_uint(cobf, OffsetToPieceNameOffsetArray + 4*i)
		pieces.append(get_name(cobf,offset))
	print (pieces)
	scripts = [get_name(cobf, get_uint(cobf, hd['OffsetToScriptNameOffsetArray'] + 4*i)) for i in range (hd["NumberOfScripts"])]
	print (scripts)
	scriptcode = [get_uint(cobf, 4*len(hf) + 4*i) for i in range(hd["TotalScriptLen"])]
	scriptoffsets = [get_uint(cobf, hd["OffsetToScriptCodeIndexArray"] + 4*i) for i in range(hd["NumberOfScripts"])]
	print(scriptoffsets)


	cmd = []
	opcnt = 0
	opname = ""

	decomp = []
	for i, scriptname in enumerate(scripts):
		decomp.append(str(scriptname))
		startpos = scriptoffsets[i]
		endpos = hd["TotalScriptLen"]
		if i+1 < len(scriptoffsets):
			endpos = scriptoffsets[i+1] 
		for offset in range(startpos, endpos ):
			op = scriptcode[offset]
			
			#for j, op in enumerate(scriptcode[0:hd["TotalScriptLen"]]):
			if op in rop:
				
				if opname not in opargcnt:
					opargcnt[opname] = {}
				if opcnt not in opargcnt[opname]:
					opargcnt[opname][opcnt] = 0
				opargcnt[opname][opcnt] += 1

				opname = rop[op]
				#print(cmd)
				decomp.append(cmd)
				cmd = ['\\* 0x%06x *\\'% offset, opname]
				opcnt = 0
				
			else:
				opcnt+=1
				cmd += str(op)
	#print(decomp)
	return decomp


def get_path():
	if len(sys.argv) > 1:
		path = sys.argv[1]
	else:
		path = os.getcwd()
	return path

def get_filenames(path):
	if os.path.isdir(path):
		filenames = os.listdir(path)
	else:
		filenames = [path]
	return filenames

if __name__ == "__main__":
	path = get_path()
	filenames = get_filenames(path)
	ipairs = {}
	for filename in filenames:
		if filename.lower().endswith(".cob"):	
			print (path+filename)
			res = decompile(os.path.join(path ,filename))	
			for i in range(0,len(res)-1):
				op1 = res[i]
				op2 = res[i+1]
				if len(op1) >= 2 and len(op2)>=2:
					order = f'{op1[1]}->{op2[1]}'
					if order not in ipairs:
						ipairs[order] = 0
					ipairs[order] += 1
			print ('\n'.join([str(r) for r in res]))
	for op, cnts in opargcnt.items():
		print(op, cnts)
	for op, _ in OPCODES.items():
		if op not in opargcnt:
			print(f"{op} was never seen")
			continue
		cnts = opargcnt[op]
		if len(cnts) == 1:
			print(f"{op} count is {list(cnts.keys())[0]}")
		else:
			print(f"{op} has more than one call kind:")
	print("Pairs:")
	for i in sorted( list(ipairs.items()), key = lambda x:x[1], reverse=True):
		print (i)