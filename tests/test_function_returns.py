import struct

import pytest

from conftest import parse_compile_summary, read_cob, run_compiler


def _compile(tmp_path, source, flags):
	bos = tmp_path / "returns.bos"
	bos.write_text(source)
	result = run_compiler(bos, *flags)
	assert result.returncode == 0, result.stdout + result.stderr
	header, data = read_cob(bos.with_suffix(".cob"))
	assert parse_compile_summary(result.stdout) == (
		header["TotalScriptLen"], header["NumberOfStaticVars"]
	)
	code = struct.unpack_from("<%dL" % header["TotalScriptLen"], data, header["OffsetToScriptCode"])
	offsets = struct.unpack_from(
		"<%dL" % header["NumberOfScripts"], data, header["OffsetToScriptCodeIndexArray"]
	)
	ends = offsets[1:] + (len(code),)
	functions = dict(zip(header["functions"], zip(offsets, ends)))
	return code, functions


def _execute(code, bounds, stunned, other, short):
	# Execute only the instructions used by these fixtures. Check the function
	# boundary on every fetch, even when another function follows in the file.
	push_constant, push_static, pop_static, jump, jump_if_zero, ret = (
		(0x21, 0x23, 0x26, 0x64, 0x66, 0x65) if short else
		(0x10021001, 0x10021004, 0x10023004, 0x10064000, 0x10066000, 0x10065000)
	)
	start, end = bounds
	pc = start
	stack = []
	static_vars = [stunned, other]

	def fetch():
		nonlocal pc
		assert start <= pc < end, "execution escaped the function at word %d" % pc
		word = code[pc]
		pc += 1
		return word

	for _ in range(100):
		opcode = fetch()
		if opcode == push_constant:
			stack.append(fetch())
		elif opcode == push_static:
			stack.append(static_vars[fetch()])
		elif opcode == pop_static:
			static_vars[fetch()] = stack.pop()
		elif opcode == jump:
			pc = fetch()
		elif opcode == jump_if_zero:
			target = fetch()
			if stack.pop() == 0:
				pc = target
		elif opcode == ret:
			value = stack.pop()
			assert not stack
			return value
		else:
			pytest.fail("unexpected opcode %#x" % opcode)
	pytest.fail("function did not return")


@pytest.mark.parametrize("flags", [(), ("--dontfold",), ("--shortopcodes",), ("--shortopcodes", "--dontfold")])
@pytest.mark.parametrize("followed_by_function", [False, True], ids=["last-function", "next-function"])
@pytest.mark.parametrize(
	("body", "expected"),
	[
		("if (Stunned) { return (1); }", (0, 0, 1, 1)),
		("if (Stunned) return (1);", (0, 0, 1, 1)),
		("if (Stunned) { Other = 7; } else { return (2); }", (2, 2, 0, 0)),
		("if (Stunned) { return (1); } else { Other = 7; }", (0, 0, 1, 1)),
		("if (Stunned) { if (Other) { return (1); } }", (0, 0, 0, 1)),
		("if (Stunned) { return (1); } else if (Other) { return (2); }", (0, 2, 1, 1)),
		("while (Stunned) { return (1); }", (0, 0, 1, 1)),
		("if (Stunned) { while (Other) { return (1); } }", (0, 0, 0, 1)),
		("if (Stunned) { return (1); } return (2);", (2, 2, 1, 1)),
		("if (Stunned) { return (1); } else { return (2); }", (2, 2, 1, 1)),
		("return;", (0, 0, 0, 0)),
		("", (0, 0, 0, 0)),
	],
	ids=["if", "unbraced-if", "else-returns", "then-returns", "nested-if", "else-if",
		"while", "nested-while", "final-return", "both-return", "bare-return", "empty"],
)
def test_function_returns_without_leaving_its_body(tmp_path, flags, followed_by_function, body, expected):
	source = "static-var Stunned, Other;\nPadding() { return (13); }\n"
	source += "ExecuteRestoreAfterDelay() { %s }\n" % body
	if followed_by_function:
		source += "FunctionThatDoesSomethingUnrelated() {}\n"
	code, functions = _compile(tmp_path, source, flags)
	for (stunned, other), value in zip(((0, 0), (0, 1), (1, 0), (1, 1)), expected):
		assert _execute(code, functions["ExecuteRestoreAfterDelay"], stunned, other,
			"--shortopcodes" in flags) == value


def test_jump_operand_matching_return_opcode_still_gets_implicit_return(tmp_path):
	# 98 local declarations and a three-word return put the loop at word 0x65,
	# also the short RETURN opcode. Its final word is a jump operand, not RETURN.
	padding = ", ".join("pad%d" % i for i in range(98))
	source = "static-var Stunned, Other;\nPadding() { var %s; return (0); }\n" % padding
	source += "ExecuteRestoreAfterDelay() { while (Stunned) { return (1); } }\n"
	code, functions = _compile(tmp_path, source, ("--shortopcodes",))
	assert functions["ExecuteRestoreAfterDelay"][0] == 0x65
	assert _execute(code, functions["ExecuteRestoreAfterDelay"], 0, 0, True) == 0
	assert _execute(code, functions["ExecuteRestoreAfterDelay"], 1, 0, True) == 1


@pytest.mark.parametrize("flags", [(), ("--shortopcodes",)])
def test_consecutive_conditional_functions_have_valid_jump_targets(tmp_path, flags):
	code, functions = _compile(tmp_path,
		"static-var Stunned, Other;\n"
		"First() { if (Stunned) { return (1); } }\n"
		"Second() { if (Other) { return (2); } }\n", flags)
	short = "--shortopcodes" in flags
	for stunned, other in ((0, 0), (0, 1), (1, 0), (1, 1)):
		assert _execute(code, functions["First"], stunned, other, short) == stunned
		assert _execute(code, functions["Second"], stunned, other, short) == 2 * other


@pytest.mark.parametrize("flags", [(), ("--shortopcodes",)])
def test_final_unconditional_return_needs_no_extra_epilogue(tmp_path, flags):
	code, functions = _compile(tmp_path, "ExplicitReturn() { return (42); }\n", flags)
	push, ret = (0x21, 0x65) if flags else (0x10021001, 0x10065000)
	assert functions["ExplicitReturn"] == (0, 3)
	assert code == (push, 42, ret)
