import getpass
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config):
	# On some machines the default pytest temp root (AppData\Local\Temp\pytest-of-<user>)
	# exists but is locked down by its ACL, which breaks every tmp_path test with
	# PermissionError. Point pytest at a fresh temp root in that case; otherwise
	# leave the default behaviour untouched.
	temproot = Path(tempfile.gettempdir())
	default_root = temproot / ("pytest-of-" + (getpass.getuser() or "unknown"))
	try:
		default_root.mkdir(mode=0o700, exist_ok=True)
		probe = default_root / ".write-probe"
		probe.write_bytes(b"")
		probe.unlink()
	except OSError:
		os.environ["PYTEST_DEBUG_TEMPROOT"] = tempfile.mkdtemp(
			prefix="pytest-temproot-", dir=temproot
		)


COMPILER = ROOT / "bos2cob_py3.py"
CORPUS = Path(__file__).parent / "fixtures" / "corpus"

COB_HEADER_FIELDS = (
	"VersionSignature",
	"NumberOfScripts",
	"NumberOfPieces",
	"TotalScriptLen",
	"NumberOfStaticVars",
	"Unknown_2",
	"OffsetToScriptCodeIndexArray",
	"OffsetToScriptNameOffsetArray",
	"OffsetToPieceNameOffsetArray",
	"OffsetToScriptCode",
	"OffsetToNamesArray",
)


def run_compiler(bos_path, *flags):
	return subprocess.run(
		[sys.executable, str(COMPILER), *flags, str(bos_path)],
		cwd=ROOT,
		text=True,
		capture_output=True,
	)


def copy_tree_to_tmp(source_dir, tmp_path):
	for source in sorted(Path(source_dir).rglob("*")):
		if source.is_file():
			destination = Path(tmp_path) / source.relative_to(source_dir)
			destination.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy2(source, destination)


def read_cob(cob_path):
	data = Path(cob_path).read_bytes()
	values = struct.unpack_from("<%dL" % len(COB_HEADER_FIELDS), data, 0)
	header = dict(zip(COB_HEADER_FIELDS, values))
	header["functions"] = _read_names(data, header, "NumberOfScripts", "OffsetToScriptNameOffsetArray")
	header["pieces"] = _read_names(data, header, "NumberOfPieces", "OffsetToPieceNameOffsetArray")
	return header, data


def _read_names(data, header, count_field, offset_field):
	count = header[count_field]
	offsets = struct.unpack_from("<%dL" % count, data, header[offset_field])
	names = []
	for offset in offsets:
		end = data.index(b"\0", offset)
		names.append(data[offset:end].decode("utf-8"))
	return names


def parse_compile_summary(stdout):
	match = re.search(r"Compile successful: (\d+) Commands, (\d+) Static-vars", stdout)
	if match is None:
		return None
	return int(match.group(1)), int(match.group(2))
