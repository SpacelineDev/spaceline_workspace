#define MyAppName "Spaceline"
#ifndef AppVersion
  #define AppVersion "0.9.6"
#endif

[Setup]
AppId={{9A7E58E8-2B65-4E20-8A0E-9F6A0C2D1B96}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher=Spaceline
DefaultDirName={localappdata}\Programs\Spaceline
DefaultGroupName=Spaceline
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=Spaceline-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Spaceline.exe
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64
Uninstallable=yes

[Files]
Source: "..\dist\Spaceline.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\FIREBASE_SETUP.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Spaceline"; Filename: "{app}\Spaceline.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Spaceline"; Filename: "{app}\Spaceline.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\Spaceline.exe"; Description: "Launch Spaceline"; Flags: postinstall nowait skipifsilent