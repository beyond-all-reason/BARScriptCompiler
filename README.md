# BARScriptCompiler

This is a compiler for the .bos animation scripting format for the recoil engine.
It is a fully complete replacement for Scriptor, which is now nearly 25 years old.

## What it does

- Compiles `.bos` animation scripts to `.cob` bytecode for the RecoilEngine
- Compiles a single `.bos` file or an entire directory of them
- Runs scripts through the pcpp preprocessor first, which allows for very extensive customization and modularization
- Constant folding and other bytecode optimizations
- Optional `uint8_t` short opcodes (experimental)
- `cob_decompiler.py` disassembles `.cob` files back to readable form for debugging

## Running from source

- Install Python 3 (CI tests against 3.12) and the runtime dependency: `pip install pcpp`
- Compile a file or directory:

```
python bos2cob_py3.py path/to/file.bos
```

The `.cob` output is written next to the `.bos` source.

## Command line args

```
--shortopcodes     Use uint8_t opcodes (EXPERIMENTAL with engine branch CobShortOpCodes)
--dontfold         Disable constant folding optimization
--dumpast          Dump the parsed syntax tree into a _initial.ast file
--dumppcpp         Dump the results of the pcpp preprocessor
--include <dir>    Additional include directory for pcpp preprocessor
--gltf-swap        Rewrite script axes from GLTF Z-up model space to engine Spring space (see GLTF_AXIS_SWAP.md)
--gltf-swap-s3o    Same as --gltf-swap, but for models with s3ocompat=true in their .lua metafile
<filename>         A bos file to compile, or a directory of bos files to work on, such as ../units/myunit.bos
```

The `WARNING: Couldn't write lextab module 'pcpp.lextab'. [Errno 2] No such file or directory` warning can safely be ignored.

`--gltf-swap` rewrites the axis of every `turn`/`move`/`spin` (and `stop-spin`/`scale`/`wait-*`)
statement from the GLTF authoring frame (Z-up) to the engine's Spring frame, inserting a runtime
`* -1` on signed on-axis values where the swap negates the axis. Alternatively, put a
`#define GLTF` (optionally with a custom axis spec) in the `.bos` file itself; per-file defines
override the flags. See [GLTF_AXIS_SWAP.md](GLTF_AXIS_SWAP.md).

## Disassembling COB files

```
python cob_decompiler.py path/to/file.cob
```

## Development

- Tests are a pytest suite in `tests/`; run from the repo root:

```
pip install pcpp pytest
python -m pytest
```

- Tests invoke the compiler as a subprocess (`python bos2cob_py3.py ...`) and
  validate the resulting `.cob` binaries; they do not import the compiler in-process.
- Test fixtures are self-contained under `tests/fixtures/` (see
  `tests/fixtures/corpus/README.md`). Do not compile fixtures in place; the
  compiler writes `.cob` files next to the `.bos` source, and the tests copy the
  corpus to a temp directory first.

## Setup for VSCode

- Install the Bos language support VSCode Extension by Chesiren from: https://github.com/chesiren/bos-language-support
- Select the menu 'Terminal->Configure Tasks...'
- Scroll to the bottom, select `Create tasks.json file from template`
- Select `Others`
- Paste the snippet below into the tasks.json file
- Edit the path to `BARScriptCompiler.exe`
- Hit `ctrl-shift-B` to compile any .bos file

```
{
    // See https://go.microsoft.com/fwlink/?LinkId=733558
    // for the documentation about the tasks.json format
    "version": "2.0.0",
    "tasks": [
        {
            "label": "BARScriptCompiler",
            "type": "shell",
            "command": "N:/BARScriptCompiler/BARScriptCompiler.exe",
            "args": [{
                "value":"${file}",
                "quoting": "strong"
            }],
            "problemMatcher": [],
            "group": {
                "kind": "build",
                "isDefault": true
            }
        }
    ]
}
```

## Setup Windows Notepad++
- Download this repo as zip
- Install Notepad++
- Install the NPPexec plugin for Notepad++ from the Plugins->Plugins Admin menu
- Using the NPPExec plugin will auto save the file before compilation.
- Hit `F6` to set up the compiler
- Set up the nppexec script with (NOTE: only change the path to the exe, dont change the `"$(FULL_CURRENT_PATH)"` part, as that is needed so np++ knows the path to the file) :

```
npp_save
"C:\BARScriptCompiler\BARScriptCompiler.exe" "$(FULL_CURRENT_PATH)"
```

![image](https://github.com/beyond-all-reason/BARScriptCompiler/assets/109391/cebc1d2e-0405-4106-9879-fb6efee55a5a)


- hit `CTRL + F6` to compile it

## Quickly reload COB Scripts for units in Beyond All Reason

**Enable the CobReload widget from F11 menu**
**Hit CTRL + R to reload cob scripts for all selected units**

## Future Plans

- [X] Improve the language to use chars as opcodes for better interpreter switch generation
- [ ] First-class ABS, MAX, MIN, SIGN, SINE, DELTAHEADING etc functions for speed.
    - E.g. see https://github.com/beyond-all-reason/spring/commit/acc3a294b0d9db28a16fea75858c80110ede4d6b#diff-302c5df9876df8e098af4798263206e886f90b827ccab2e56f3f2da690eaf256R705
- [ ] New GET statements for unit_x, unit_z
    - Because the current packedXZ format packs the units position into two 16 bit integers, this precision is absolulyte not enough!
- [ ] Parametric move and turn commands, use variables from the stack instead of constants in the COB script
    - Because sometimes, you want to be able to turn a piece based on a a variable and dont want to write a huge if statement. E.g.:
    - we would want: `move (barrel0 + VARIABLE) along x-axis [1] speed [1];`
    - instead of :
	```c
		if (X == 0 ) move barrel0 along x-axis [1] speed [1];
		if (X == 1 ) move barrel1 along x-axis [1] speed [1];
		if (X == 2 ) move barrel2 along x-axis [1] speed [1];
	```
- [ ] Scale command
    - Due to the new skeletal and mesh animations, move and turn are no longer enough to describe animations
    - e.g. `scale torso along x-axis [2.0] speed [2.0];`

- [ ] Thread safety indicator, to allow MT'ing of ticks
    - Engine random isnt MT safe, use and see Linear Feedback Shift register in random.h
    - Doing things like getting the unitID's of _other_ units is not thread safe
    - But the compiler can know ahead of time of all of the
- [ ] Lua-less batched sendtounsynced
- [ ] Array support
- [ ] Constant acceleration
- [ ] Multithreaded execution of COB scripts on engine, see the wonderful diagram here:

![image](https://github.com/user-attachments/assets/0998e2f9-f7f8-4068-902c-3a3a0f3f0ae4)

## Known improvements over the original bos2cob

- Python3
- Better printing of syntax errors
- Constant folding
- Working when compiling whole directories
- Mandatory pcpp preprocessor support
- More expletives in comments
- Support for uint8_t bos opcodes

## Stuff needing doing

- [X] Convert bos2cob.py to python3
- [X] Supply compiler exectutable for notepad++ running
- [X] Optimize constants
- [X] Add cmd options to wrapper
- [X] Validate modulo operator

## Contributing

See [AI_POLICY.md](AI_POLICY.md): AI-assisted code must be disclosed in the
pull request and fully verified by a human contributor.

## License: GPL, original author ashdnazg:

https://github.com/ashdnazg/bos2cob
