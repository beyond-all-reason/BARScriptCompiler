import pytest

from conftest import CORPUS, copy_tree_to_tmp, parse_compile_summary, read_cob, run_compiler


CASES = [
	{
		"name": "freefusion",
		"bos": "freefusion.bos",
		"pieces": 7,
		"piece_names": {"base", "column1", "fusionsphere", "emit"},
		"static_vars": 0,
		"functions": {"Create", "Activate", "SmokeUnit", "Killed", "SweetSpot"},
	},
	{
		"name": "mission_command_tower",
		"bos": "mission_command_tower.bos",
		"pieces": 15,
		"piece_names": {"base", "column4", "fusionsphere", "coolera1", "coolerb4"},
		"static_vars": 0,
		"functions": {"Create", "Activate", "SmokeUnit", "Killed", "SweetSpot"},
	},
	{
		"name": "freefusion_clean",
		"bos": "freefusion_clean.bos",
		"pieces": 7,
		"piece_names": {"base", "column1", "fusionsphere", "emit"},
		"static_vars": 1,
		"functions": {"Create", "Activate", "Killed", "HitByWeapon", "DamagedSmoke"},
	},
	{
		"name": "raptord1",
		"bos": "Raptors/raptord1.bos",
		"pieces": 2,
		"piece_names": {"body", "firepoint"},
		"static_vars": 0,
		"functions": {
			"Create", "Killed", "AimWeapon1", "AimFromWeapon1",
			"QueryWeapon1", "HitByWeaponId", "StopBuilding", "QueryNanoPiece",
		},
	},
	{
		"name": "armpt",
		"bos": "Units/armpt.bos",
		"pieces": 10,
		"piece_names": {"base", "ground", "turretaa", "flareaa", "blink"},
		"static_vars": 11,  # 4 from armpt.bos + 7 declared in bar_ships_common.h
		"functions": {
			"Create", "Killed", "Activate", "Deactivate", "Lights",
			"AimWeapon1", "QueryWeapon1", "FireWeapon1", "AimWeapon2",
			"StartMoving", "StopMoving", "SetStunned",
		},
	},
	{
		"name": "armscavengerbossv2",
		"bos": "Units/scavboss/armscavengerbossv2.bos",
		"pieces": 41,
		"piece_names": {"head", "torso", "pelvis", "biggun", "Ref_Point"},
		"static_vars": 15,
		"functions": {
			"Create", "Killed", "StartMoving", "StopMoving", "StopBuilding",
			"QueryNanoPiece", "SweetSpot",
			"QueryWeapon4", "AimWeapon4", "AimFromWeapon4", "FireWeapon4",
		},
	},
]


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_corpus_script_compiles(tmp_path, case):
	copy_tree_to_tmp(CORPUS, tmp_path)
	bos = tmp_path / case["bos"]
	result = run_compiler(bos)
	assert result.returncode == 0, result.stdout + result.stderr

	cob = bos.with_suffix(".cob")
	assert cob.is_file()

	header, _ = read_cob(cob)
	assert header["VersionSignature"] == 4
	assert header["NumberOfPieces"] == case["pieces"]
	assert case["piece_names"] <= set(header["pieces"])
	assert header["NumberOfStaticVars"] == case["static_vars"]
	assert case["functions"] <= set(header["functions"])

	summary = parse_compile_summary(result.stdout)
	assert summary is not None, result.stdout
	assert summary == (header["TotalScriptLen"], header["NumberOfStaticVars"])
