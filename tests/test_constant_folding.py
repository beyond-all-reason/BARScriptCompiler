import struct
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

PUSH_CONSTANT = (0x10021001).to_bytes(4, "little")
EMIT_SFX = (0x1000F000).to_bytes(4, "little")
ADD = (0x10031000).to_bytes(4, "little")
SUB = (0x10032000).to_bytes(4, "little")
MUL = (0x10033000).to_bytes(4, "little")
DIV = (0x10034000).to_bytes(4, "little")
MOD = (0x10034001).to_bytes(4, "little")
BITWISE_AND = (0x10035000).to_bytes(4, "little")
BITWISE_OR = (0x10036000).to_bytes(4, "little")
SET_LESS = (0x10051000).to_bytes(4, "little")


def compile_bos(tmp_path, filename, expression, static_var=False):
	header = "piece arm;\n"
	if static_var:
		header += "static-var x;\n"
	bos = tmp_path / filename
	bos.write_text(header + "\nCreate()\n{\n\tmove arm to x-axis %s now;\n}\n" % expression)
	result = subprocess.run(
		[sys.executable, str(ROOT / "bos2cob_py3.py"), str(bos)],
		cwd=ROOT,
		text=True,
		capture_output=True,
	)
	assert result.returncode == 0, result.stdout + result.stderr
	return (tmp_path / (Path(filename).stem + ".cob")).read_bytes(), result.stdout


def pushed_value(value):
	if value < 0:
		return PUSH_CONSTANT + struct.pack("<l", value)
	return PUSH_CONSTANT + struct.pack("<L", value)


def test_division_uses_truncating_integer_division(tmp_path):
	cob, _ = compile_bos(tmp_path, "div.bos", "7 / 2")
	assert pushed_value(3) in cob
	assert DIV not in cob


def test_negative_division_truncates_toward_zero(tmp_path):
	cob, _ = compile_bos(tmp_path, "negdiv.bos", "-7 / 2")
	assert pushed_value(-3) in cob
	assert DIV not in cob


def test_modulo_uses_c_sign(tmp_path):
	cob, _ = compile_bos(tmp_path, "mod.bos", "-7 % 3")
	assert pushed_value(-1) in cob
	assert MOD not in cob


def test_bitwise_precedence_and_binds_tighter_than_or(tmp_path):
	cob, _ = compile_bos(tmp_path, "bitwise.bos", "4 & 2 | 1")
	assert pushed_value(1) in cob
	assert BITWISE_AND not in cob
	assert BITWISE_OR not in cob


def test_scaled_constant_folded_matches_unfolded(tmp_path):
	solo, _ = compile_bos(tmp_path, "solo.bos", "[0.1]")
	folded, _ = compile_bos(tmp_path, "folded.bos", "1 + [0.1]")
	assert pushed_value(6553) in solo
	assert pushed_value(6554) in folded
	assert ADD not in folded


def test_hex_constant_folds(tmp_path):
	cob, _ = compile_bos(tmp_path, "hex.bos", "0x10 + 5")
	assert pushed_value(21) in cob
	assert ADD not in cob


def test_division_by_zero_is_not_folded(tmp_path):
	cob, stdout = compile_bos(tmp_path, "div0.bos", "5 / 0")
	assert DIV in cob
	assert "not folding" in stdout


def test_overflow_is_not_folded_and_warns(tmp_path):
	cob, stdout = compile_bos(tmp_path, "big.bos", "[1000] * 50")
	assert MUL in cob
	assert "not folding" in stdout


def test_island_after_variable_folds(tmp_path):
	cob, _ = compile_bos(tmp_path, "mid.bos", "x + 2 + 3", static_var=True)
	assert ADD in cob
	assert pushed_value(5) in cob
	assert pushed_value(2) not in cob
	assert pushed_value(3) not in cob


def test_left_boundary_operand_not_stolen(tmp_path):
	cob, _ = compile_bos(tmp_path, "left.bos", "x * 3 + 2", static_var=True)
	assert MUL in cob
	assert ADD in cob
	assert pushed_value(3) in cob
	assert pushed_value(2) in cob
	assert pushed_value(5) not in cob


def test_right_boundary_operand_not_stolen(tmp_path):
	cob, _ = compile_bos(tmp_path, "right.bos", "4 | 2 < 3")
	assert BITWISE_OR in cob
	assert SET_LESS in cob
	assert pushed_value(6) not in cob


def compile_emit_sfx_bos(tmp_path, filename, from_expr, *flags):
	bos = tmp_path / filename
	bos.write_text(
		"piece base, fire1, fire2;\n\nCreate()\n{\n\temit-sfx 1024 from %s;\n}\n" % from_expr
	)
	result = subprocess.run(
		[sys.executable, str(ROOT / "bos2cob_py3.py"), *flags, str(bos)],
		cwd=ROOT,
		text=True,
		capture_output=True,
	)
	return result


def test_emit_sfx_piece_expression_folds(tmp_path):
	result = compile_emit_sfx_bos(tmp_path, "sfx.bos", "base + 1")
	assert result.returncode == 0, result.stdout + result.stderr
	cob = (tmp_path / "sfx.cob").read_bytes()
	assert PUSH_CONSTANT + struct.pack("<L", 1024) in cob
	assert EMIT_SFX + struct.pack("<L", 1) in cob
	assert ADD not in cob


def test_emit_sfx_piece_subtract_folds(tmp_path):
	result = compile_emit_sfx_bos(tmp_path, "sfxsub.bos", "fire2 - base")
	assert result.returncode == 0, result.stdout + result.stderr
	cob = (tmp_path / "sfxsub.cob").read_bytes()
	assert EMIT_SFX + struct.pack("<L", 2) in cob
	assert SUB not in cob


def test_emit_sfx_bare_piece_name_still_works(tmp_path):
	for filename, flags in (("sfxplain.bos", ()), ("sfxplain2.bos", ("--dontfold",))):
		result = compile_emit_sfx_bos(tmp_path, filename, "base", *flags)
		assert result.returncode == 0, result.stdout + result.stderr
		cob = (tmp_path / (Path(filename).stem + ".cob")).read_bytes()
		assert EMIT_SFX + struct.pack("<L", 0) in cob


@pytest.mark.parametrize(
	("filename", "from_expr", "flags", "expected"),
	[
		("sfxnf.bos", "base + 1", ("--dontfold",), "compile-time constant"),
		("sfxrange.bos", "base + 99", (), "out of range"),
		("sfxunknown.bos", "nose", (), "Piece not found"),
		("sfxruntime.bos", "base + x", (), "compile-time constant"),
	],
)
def test_emit_sfx_bad_piece_expression_fails(tmp_path, filename, from_expr, flags, expected):
	result = compile_emit_sfx_bos(tmp_path, filename, from_expr, *flags)
	assert result.returncode != 0
	assert expected in result.stdout + result.stderr
	assert not (tmp_path / (Path(filename).stem + ".cob")).exists()
