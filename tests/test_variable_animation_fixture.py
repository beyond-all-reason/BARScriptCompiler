import re

from conftest import copy_tree_to_tmp, run_compiler
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "variable_animation"


def test_two_animation_includes_compile_and_keep_mod(tmp_path):
	copy_tree_to_tmp(FIXTURE, tmp_path)
	result = run_compiler(tmp_path / "main.bos", "--dumppcpp")
	assert result.returncode == 0, result.stdout + result.stderr
	assert (tmp_path / "main.cob").is_file()
	preprocessed = (tmp_path / "main.bos.pcpp").read_text()
	assert len(re.findall(r"^StartWalk\(\)\s*$", preprocessed, re.MULTILINE)) == 1
	assert len(re.findall(r"^StartRun\(\)\s*$", preprocessed, re.MULTILINE)) == 1
	assert "%" in preprocessed
	# Dynamic modulo must survive constant folding and be emitted as the full opcode.
	assert (0x10034001).to_bytes(4, "little") in (tmp_path / "main.cob").read_bytes()
