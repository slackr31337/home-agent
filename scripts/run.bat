@ECHO OFF
set curdir=%cd%
cd "c:\Program Files\HomeAgent"
call env\Scripts\activate.bat
call env\Scripts\python.exe run.py -s -c secrets.yaml
call env\Scripts\deactivate.bat
cd %curdir%
