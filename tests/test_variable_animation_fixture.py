from pathlib import Path
import re
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "variable_animation"
MODULE = ROOT.parent / "Beyond-All-Reason" / "scripts" / "variable_animation.h"
sys.path.insert(0, str(ROOT.parent / "Skeletor_S3O"))
from bos_animation import render_bos_animation


FRAMES = {
	0: {"pelvis": {"location1": 1.0}, "thigh": {"rot0": 0.0}},
	3: {"pelvis": {"location1": 2.0}, "thigh": {"rot0": 10.0}},
	5: {"pelvis": {"location1": 1.0}, "thigh": {"rot0": -5.0}},
}


def test_two_animation_includes_compile_and_keep_mod(tmp_path):
	for source in FIXTURE.iterdir():
		shutil.copy2(source, tmp_path / source.name)
	shutil.copy2(MODULE, tmp_path / "variable_animation.h")
	(tmp_path / "Walk.h").write_text(render_bos_animation(FRAMES, "Walk", variable_amplitude=False))
	(tmp_path / "Run.h").write_text(render_bos_animation(FRAMES, "Run", variable_amplitude=True))
	result = subprocess.run(
		[sys.executable, str(ROOT / "bos2cob_py3.py"), "--dumppcpp", str(tmp_path / "main.bos")],
		cwd=ROOT,
		text=True,
		capture_output=True,
	)
	assert result.returncode == 0, result.stdout + result.stderr
	assert (tmp_path / "main.cob").is_file()
	preprocessed = (tmp_path / "main.bos.pcpp").read_text()
	assert len(re.findall(r"^StartWalk\(\)\s*$", preprocessed, re.MULTILINE)) == 1
	assert len(re.findall(r"^StartRun\(\)\s*$", preprocessed, re.MULTILINE)) == 1
	assert "%" in preprocessed
	# Dynamic modulo must survive constant folding and be emitted as the full opcode.
	assert (0x10034001).to_bytes(4, "little") in (tmp_path / "main.cob").read_bytes()
