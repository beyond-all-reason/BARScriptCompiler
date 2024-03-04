## Setup

- Install python3
- Install Notepad++
- Install NPPexec plugin for notepad++
- Hit F6 to set up the compiler
- Set up the nppexec script with:

```
npp_save
"c:\whereveryourpythonis\python.exe" "C:\whereverthisscriptis\bos2cob_py3.py" "$(FULL_CURRENT_PATH)"
```

- Or use the prebuilt binary of BARScriptCompiler.exe
- Save script
- hit CTRL + F6 to compile it

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
- [ ] Validate modulo operator

## License: GPL, original author ashdnazg:

https://github.com/ashdnazg/bos2cob

