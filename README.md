## Setup

- Install python3
- Install Notepad++
- Install NPPexec plugin for notepad++
- Hit F6 to set up the compiler
- Set up the nppexec script with: 
- `"c:\whereveryourpythonis\python.exe" "C:\whereverthisscriptis\bos2cob_py3.py" "$(FULL_CURRENT_PATH)"`
- Save script
- hit CTRL + F6 to compile it

## Known improvements:

- Python3
- Better printing of syntax errors
- Constant folding
- Working when compiling whole directories
- Optional pcpp preprocessor support
- More expletives in comments


## Stuff needing doing

- [X] Convert bos2cob.py to python3
- [X] Supply compiler exectutable for notepad++ running
- [X] Optimize constants
- [ ] Add cmd options to wrapper
- [ ] Validate modulo operator

## License GPL, original author ashdnazg:

https://github.com/ashdnazg/bos2cob

