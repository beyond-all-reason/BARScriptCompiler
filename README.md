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
  - Install nppexec plugin for notepad++
  - Hit F6 to set up the compiler
  - as per: https://www.trishtech.com/2021/07/run-commands-from-notepad-with-nppexec-plugin/
  - `c:\whereveryourpythonis\python.exe "C:\whereverthisscriptis\bos2cob_py3.py" "$(FULL_CURRENT_PATH)"`
  - Set up the nppexec script:
  - ![image](https://github.com/beyond-all-reason/BARScriptCompiler/assets/109391/8c0204b5-01f6-498b-942c-966f713ae459)
  - Hit Ctrl + F6 to run compiler
      
- [X] Optimize constants
- [ ] Add cmd options to wrapper
- [ ] Validate modulo operator

## License GPL, original author ashdnazg:

https://github.com/ashdnazg/bos2cob

