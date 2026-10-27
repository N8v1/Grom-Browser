#define AppName "Grom Browser"
#define AppVersion "1.1.1"
#define AppPublisher "Ilyin Nikita Nikolaevich N8"

[Setup]
AppId={{E8048F8C-51C7-44D2-9AE6-4D69EBDEBF91}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\Grom
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=Grom-Setup-{#AppVersion}
SetupIconFile=browser_icon.ico
UninstallDisplayIcon={app}\Grom.exe
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные параметры:"

[Files]
Source: "dist\Grom\*"; DestDir: "{app}"; Excludes: "browser_data\*"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Grom.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Grom.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Grom.exe"; Description: "Запустить {#AppName}"; Flags: postinstall nowait skipifsilent
