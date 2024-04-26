# BARScriptCompiler

This is a compiler for the .bos animation scripting format for the recoil engine. 
It is a fully complete replacement for Scriptor, which is now nearly 25 years old. 

Using the NPPExec plugin will auto save the file before compilation. 

The warning `WARNING: Couldn't write lextab module 'pcpp.lextab'. [Errno 2] No such file or directory` can safely be ignored.

Can compile entire directories of BOS files. 

Note that the pcpp preprocessor allows for very extensive customization and modularization

## Setup for VSCode

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
- Hit `F6` to set up the compiler
- Set up the nppexec script with:

```
npp_save
"C:\BARScriptCompiler\BARScriptCompiler.exe" "$(FULL_CURRENT_PATH)"
```

![image](https://github.com/beyond-all-reason/BARScriptCompiler/assets/109391/cebc1d2e-0405-4106-9879-fb6efee55a5a)


- hit `CTRL + F6` to compile it




## Setup Linux

- Clone this repo
- `pip install pcpp`
- `python bos2cob_py3.py bosfile.bos`


## Command line args:
```
parser.add_argument("--shortopcodes", action='store_true', help = "Use uint8_t opcodes (EXPERIMENTAL with engine branch CobShortOpCodes)")
parser.add_argument("--dontfold", action='store_true', help = "Disable constant folding optimization")
parser.add_argument("--nopcpp", action='store_true', help = "Fallback to builtin preprocessor instead of pcpp")
parser.add_argument("--dumpast", action='store_true', help = "Dump the parsed syntax tree into a _initial.ast file")
parser.add_argument("--dumppcpp", action='store_true', help = "Dump the results of the pcpp preprocessor")
parser.add_argument("--include", type= str, help = "Additional include directory for pcpp preprocessor")
parser.add_argument("filename", type = str, help= "A bos file to compile, or a directory of bos files to work on, such as ../units/myunit.bos")
```

## Future Plans

- [X] Improve the language to use chars as opcodes for better interpreter switch generation
- [ ] First-class ABS, MAX, MIN, SIGN, SINE, DELTAHEADING etc functions for speed.
- [ ] New GET statements for unit_x, unit_z
- [ ] Parametric move and turn commands
- [ ] Scale command
- [ ] Thread safety indicator, to allow MT'ing of ticks
- [ ] Lua-less batched sendtounsynced
- [ ] Array support
- [ ] Constant acceleration


## Known improvements:

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

## License: GPL, original author ashdnazg:

https://github.com/ashdnazg/bos2cob

