# AGENTS.md — BARScriptCompiler

Python 3 compiler that converts `.bos` animation source files for Beyond All Reason / RecoilEngine into `.cob` bytecode. Full replacement for the legacy Scriptor tool.

## Layout

| Path | What |
|---|---|
| `bos2cob_py3.py` | The compiler. CLI entry point (`python bos2cob_py3.py <file.bos\|dir>`). |
| `cob_file.py` | COB binary format read/write helpers. |
| `cob_decompiler.py` | Debugging tool: disassembles `.cob` back to readable commands. |
| `BARScriptCompiler.spec`, `BARScriptCompiler.exe` | PyInstaller spec and prebuilt Windows exe (for Notepad++/VSCode setups). The exe is rebuilt by `.github/workflows/build_windows_exe.yml`, not by tests. |
| `tests/` | pytest suite. `tests/conftest.py` provides `run_compiler`, `read_cob`, `parse_compile_summary` helpers. |
| `tests/fixtures/` | Self-contained `.bos` corpus + headers (no sibling game checkout needed). See `tests/fixtures/corpus/README.md`. |
| `pytest.ini` | Sets `testpaths = tests`. |
| `requirements.txt` | Full environment freeze (dev + build tools). Runtime dep is just `pcpp`; tests need `pcpp` + `pytest`. |

## Build / Test

```
pip install pcpp pytest
python -m pytest                 # from repo root
python bos2cob_py3.py <file.bos> # compile one file or a directory
python cob_decompiler.py <f.cob> # disassemble a .cob file
```

CI (`.github/workflows/test.yml`) runs `python -m pytest` on Python 3.12.

## Conventions

- Python 3, tab indentation, CRLF line endings (match existing files).
- Tests run the compiler as a **subprocess** (`[sys.executable, "bos2cob_py3.py", ...]`) and assert on the emitted `.cob` bytes and the `Compile successful: N Commands, M Static-vars` stdout line. Do not import the compiler in-process from tests.
- The compiler writes `.cob` **next to the `.bos` source**. Never compile fixtures in place — copy to a temp dir first (see `copy_tree_to_tmp` in `tests/conftest.py`).
- The `WARNING: Couldn't write lextab module 'pcpp.lextab'` message is normal; `tests` and the compiler already filter it.
- CLI flags live at the top of `bos2cob_py3.py`; keep the README "Command line args" section in sync when changing them. `--gltf-swap`/`--gltf-swap-s3o` (and per-file `#define GLTF`) enable GLTF axis remapping, see `GLTF_AXIS_SWAP.md`.
- Always bump the `version` string at the top of `bos2cob_py3.py` (e.g. `1.2` → `1.3`) on any change to the compiler.
- COB header layout is defined in `COB_HEADER_FIELDS` in `tests/conftest.py` and mirrored by `cob_file.py`.

## Policies

- **AI usage must be disclosed in PRs** and AI-assisted code must be human-verified — see `AI_POLICY.md`.
- License: GPL, derived from https://github.com/ashdnazg/bos2cob.
