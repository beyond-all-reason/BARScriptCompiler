from conftest import CORPUS, copy_tree_to_tmp, parse_compile_summary, read_cob, run_compiler


def _compile(tmp_path, bos_rel, *flags):
	bos = tmp_path / bos_rel
	result = run_compiler(bos, *flags)
	assert result.returncode == 0, result.stdout + result.stderr
	header, _ = read_cob(bos.with_suffix(".cob"))
	summary = parse_compile_summary(result.stdout)
	assert summary is not None, result.stdout
	assert summary == (header["TotalScriptLen"], header["NumberOfStaticVars"])
	return header


def test_dontfold_keeps_more_commands_than_folded(tmp_path):
	copy_tree_to_tmp(CORPUS, tmp_path)
	folded = _compile(tmp_path, "Raptors/raptord1.bos")
	dontfold = _compile(tmp_path, "Raptors/raptord1.bos", "--dontfold")
	assert dontfold["TotalScriptLen"] > folded["TotalScriptLen"]


def test_dontfold_compiles_stress_case(tmp_path):
	copy_tree_to_tmp(CORPUS, tmp_path)
	header = _compile(tmp_path, "Units/scavboss/armscavengerbossv2.bos", "--dontfold")
	assert header["TotalScriptLen"] > 0
	assert header["NumberOfStaticVars"] == 15


def test_shortopcodes_emits_version_8_with_same_command_count(tmp_path):
	copy_tree_to_tmp(CORPUS, tmp_path)
	folded = _compile(tmp_path, "Raptors/raptord1.bos")
	short = _compile(tmp_path, "Raptors/raptord1.bos", "--shortopcodes")
	assert short["VersionSignature"] == 8
	assert short["TotalScriptLen"] == folded["TotalScriptLen"]
