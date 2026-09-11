; ==============================================================================
;  LUMENIA ART STUDIO — INNO SETUP SCRIPT
;  Gera o instalador oficial Lumenia_Setup_v0.2.0_Alpha.exe
; ==============================================================================

#define MyAppName "Lumenia"
#define MyAppFullName "Lumenia — Digital Art & Paint Studio"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Lumenia Team"
#define MyAppURL "https://lumeniateam.itch.io/lumenia"
#define MyAppExeName "Lumenia.exe"
#ifndef SourceDir
  #define SourceDir AddBackslash(SourcePath) + "..\build\portable\Lumenia.dist"
#endif
#ifndef OutputDir
  #define OutputDir AddBackslash(SourcePath) + "..\build\installer"
#endif
#define IconPath AddBackslash(SourcePath) + "..\assets\images\icon_lumenia.ico"
#define LicensePath AddBackslash(SourcePath) + "..\TERMS_AND_LICENSE.txt"

[Setup]
AppId={{D37E8492-4C10-4A9B-B41E-9C8022E5F701}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppFullName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile={#LicensePath}
OutputDir={#OutputDir}
OutputBaseFilename=Lumenia_Setup_v{#MyAppVersion}
SetupIconFile={#IconPath}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Todos os arquivos da pasta compilada
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppFullName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppFullName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
