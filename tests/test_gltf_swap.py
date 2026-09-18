import struct

import pytest

from conftest import parse_compile_summary, read_cob, run_compiler

MOVE = (0x10001000).to_bytes(4, "little")
TURN = (0x10002000).to_bytes(4, "little")
SPIN = (0x10003000).to_bytes(4, "little")
STOP_SPIN = (0x10004000).to_bytes(4, "little")
SCALE = (0x100A0000).to_bytes(4, "little")
WAIT_FOR_MOVE = (0x10012000).to_bytes(4, "little")
MUL = (0x10033000).to_bytes(4, "little")


def compile_gltf_bos(tmp_path, filename, statement, flags=(), gltf_define=None):
	# gltf_define: None = no '#define GLTF', "" = bare '#define GLTF', else the spec text
	lines = ["piece arm;"]
	if gltf_define is not None:
		lines.append("#define GLTF %s" % gltf_define if gltf_define else "#define GLTF")
	lines += ["", "Create()", "{", "\t" + statement, "}"]
	bos = tmp_path / filename
	bos.write_text("\n".join(lines) + "\n")
	result = run_compiler(bos, *flags)
	return result, bos


def expect_success(result, bos):
	assert result.returncode == 0, result.stdout + result.stderr
	cob_path = bos.with_suffix(".cob")
	cob = cob_path.read_bytes()
	header, _ = read_cob(cob_path)
	summary = parse_compile_summary(result.stdout)
	assert summary is not None, result.stdout
	assert summary == (header["TotalScriptLen"], header["NumberOfStaticVars"])
	return cob


def statement_args(cob, opcode):
	# each statement opcode is followed by packed args: piece index, then axis index
	args = []
	pos = 0
	while True:
		index = cob.find(opcode, pos)
		if index < 0:
			break
		piece, axis = struct.unpack_from("<LL", cob, index + 4)
		args.append((piece, axis))
		pos = index + 4
	return args


def turn_to(axis):
	return "turn arm to %s-axis <5.000000> speed <300.000000>;" % axis


def move_to(axis):
	return "move arm to %s-axis [1.000000] speed [30.000000];" % axis


def spin_around(axis):
	return "spin arm around %s-axis speed <300.000000>;" % axis


@pytest.mark.parametrize(
	("axis", "expected_axis", "inverted"),
	[("x", 0, False), ("y", 2, True), ("z", 1, False)],
)
def test_gltf_swap_remaps_turn_axes(tmp_path, axis, expected_axis, inverted):
	result, bos = compile_gltf_bos(tmp_path, "turn.bos", turn_to(axis), flags=("--gltf-swap",))
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, expected_axis)]
	assert cob.count(MUL) == (1 if inverted else 0)


@pytest.mark.parametrize(
	("axis", "expected_axis", "inverted"),
	[("x", 0, True), ("y", 2, False), ("z", 1, False)],
)
def test_gltf_swap_s3o_remaps_turn_axes(tmp_path, axis, expected_axis, inverted):
	result, bos = compile_gltf_bos(tmp_path, "turn.bos", turn_to(axis), flags=("--gltf-swap-s3o",))
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, expected_axis)]
	assert cob.count(MUL) == (1 if inverted else 0)


@pytest.mark.parametrize(
	("axis", "expected_axis", "inverted"),
	[("x", 0, False), ("y", 2, True), ("z", 1, False)],
)
def test_gltf_swap_remaps_spin_axes_with_turn_signs(tmp_path, axis, expected_axis, inverted):
	result, bos = compile_gltf_bos(tmp_path, "spin.bos", spin_around(axis), flags=("--gltf-swap",))
	cob = expect_success(result, bos)
	assert statement_args(cob, SPIN) == [(0, expected_axis)]
	assert cob.count(MUL) == (1 if inverted else 0)


def test_no_flag_no_remap(tmp_path):
	result, bos = compile_gltf_bos(tmp_path, "plain.bos", turn_to("y"))
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, 1)]
	assert cob.count(MUL) == 0


def test_gltf_swap_inverts_move_position_but_not_speed(tmp_path):
	result, bos = compile_gltf_bos(tmp_path, "move.bos", move_to("y"), flags=("--gltf-swap",))
	cob = expect_success(result, bos)
	assert statement_args(cob, MOVE) == [(0, 2)]
	# exactly one negation: the on-axis position, not the speed magnitude
	assert cob.count(MUL) == 1


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_gltf_swap_remaps_stop_spin_without_inversion(tmp_path, axis):
	result, bos = compile_gltf_bos(
		tmp_path, "stopspin.bos", "stop-spin arm around %s-axis;" % axis, flags=("--gltf-swap",)
	)
	cob = expect_success(result, bos)
	assert statement_args(cob, STOP_SPIN) == [(0, {"x": 0, "y": 2, "z": 1}[axis])]
	assert cob.count(MUL) == 0


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_gltf_swap_remaps_wait_for_move_without_inversion(tmp_path, axis):
	result, bos = compile_gltf_bos(
		tmp_path, "wait.bos", "wait-for-move arm along %s-axis;" % axis, flags=("--gltf-swap",)
	)
	cob = expect_success(result, bos)
	assert statement_args(cob, WAIT_FOR_MOVE) == [(0, {"x": 0, "y": 2, "z": 1}[axis])]
	assert cob.count(MUL) == 0


def test_gltf_swap_remaps_scale_without_inversion(tmp_path):
	result, bos = compile_gltf_bos(
		tmp_path, "scale.bos", "scale arm to y-axis [2.000000] speed [10.000000];", flags=("--gltf-swap",)
	)
	cob = expect_success(result, bos)
	assert statement_args(cob, SCALE) == [(0, 2)]
	assert cob.count(MUL) == 0


def test_bare_define_equals_default_map(tmp_path):
	result, bos = compile_gltf_bos(tmp_path, "bare.bos", turn_to("y"), gltf_define="")
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, 2)]
	assert cob.count(MUL) == 1


def test_define_overrides_flag(tmp_path):
	result, bos = compile_gltf_bos(
		tmp_path, "override.bos", turn_to("x"), flags=("--gltf-swap-s3o",), gltf_define=""
	)
	cob = expect_success(result, bos)
	# bare define selects the default map (x not inverted), not the s3o map
	assert statement_args(cob, TURN) == [(0, 0)]
	assert cob.count(MUL) == 0
	assert "'#define GLTF' in file overrides --gltf-swap/--gltf-swap-s3o" in result.stdout


def test_define_three_field_spec(tmp_path):
	result, bos = compile_gltf_bos(tmp_path, "three.bos", turn_to("y"), gltf_define="x;z;y")
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, 2)]
	assert cob.count(MUL) == 0


def test_define_six_field_spec_shares_signs(tmp_path):
	result, bos = compile_gltf_bos(tmp_path, "sixx.bos", turn_to("x"), gltf_define="x;z;y;-;+;+")
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, 0)]
	assert cob.count(MUL) == 1

	result, bos = compile_gltf_bos(tmp_path, "sixy.bos", turn_to("y"), gltf_define="x;z;y;-;+;+")
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, 2)]
	assert cob.count(MUL) == 0


def test_define_nine_field_spec_separates_turn_and_move_signs(tmp_path):
	# x: turn inverted, move not; y: neither; z: move inverted
	spec = "x;z;y;-;-;+;+;+;-"
	result, bos = compile_gltf_bos(tmp_path, "turnx.bos", turn_to("x"), gltf_define=spec)
	cob = expect_success(result, bos)
	assert statement_args(cob, TURN) == [(0, 0)]
	assert cob.count(MUL) == 1

	result, bos = compile_gltf_bos(tmp_path, "movex.bos", move_to("x"), gltf_define=spec)
	cob = expect_success(result, bos)
	assert statement_args(cob, MOVE) == [(0, 0)]
	assert cob.count(MUL) == 0

	result, bos = compile_gltf_bos(tmp_path, "movez.bos", move_to("z"), gltf_define=spec)
	cob = expect_success(result, bos)
	assert statement_args(cob, MOVE) == [(0, 1)]
	assert cob.count(MUL) == 1


@pytest.mark.parametrize(
	"spec",
	["x;q;y", "x;z", "x;z;y;q;+;+", "x;z;y;-;+;+;+", "x;z;y;-;+;+;+;-;q"],
)
def test_invalid_define_fails(tmp_path, spec):
	result, bos = compile_gltf_bos(tmp_path, "bad.bos", turn_to("x"), gltf_define=spec)
	assert result.returncode == 1
	assert "Invalid #define GLTF" in result.stdout
	assert not bos.with_suffix(".cob").exists()


def test_gltf_swap_flags_are_mutually_exclusive(tmp_path):
	result, bos = compile_gltf_bos(
		tmp_path, "both.bos", turn_to("x"), flags=("--gltf-swap", "--gltf-swap-s3o")
	)
	assert result.returncode == 2
	assert "not allowed with argument" in result.stderr
	assert not bos.with_suffix(".cob").exists()
