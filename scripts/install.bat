@ECHO OFF
echo "Install Home Agent"
set curdir=%cd%

cd "c:\Program Files\"
rmdir /S HomeAgent
mkdir HomeAgent
xcopy "c:\Users\slack\Documents\Git\home-agent" "c:\Program Files\HomeAgent" /s /e

REM nssm.exe remove HomeAgent confirm

REM nssm.exe install HomeAgent
REM nssm.exe set HomeAgentApplication "C:\Program Files\HomeAgent\env\Scripts\python.exe"
REM nssm.exe set HomeAgentAppParameters "C:\Program Files\HomeAgent\service.py"
REM nssm.exe set HomeAgentAppDirectory "C:\Program Files\HomeAgent\"

REM nssm.exe start HomeAgent
REM nssm.exe stopHomeAgent
REM nssm.exe remove HomeAgent confirm

REM sc delete HomeAgent
REM sc create HomeAgent binpath= "C:\Program Files\HomeAgent\env\Scripts\python.exe --C:\Program Files\HomeAgent\service.py" DisplayName= "HomeAgent" start= auto
cd %curdir%
