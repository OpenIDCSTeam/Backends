#define MyAppName "Open IDC Server Backends"
#define MyAppVersion "0.4 Beta"
#define MyAppPublisher "Pikachu Software"
#define MyAppURL "https://github.com/OpenIDCSTeam/Backends"

[Setup]
; 注: AppId的值为单独标识该应用程序。
AppId={{F72299DF-18CD-4F4E-829F-8ADF81373EB1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
SetupIconFile=..\HostConfig\HostManage.ico
; 以下行取消注释，以在非管理安装模式下运行（仅为当前用户安装）。
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
OutputDir=..\BuildCache\
OutputBaseFilename=OpenIDCS-Client-v0.4-winnt-x64-setup
Compression=zip
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=150

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; 通用-安装文件
Source: "..\LICENSE"; DestDir: "{app}\License.rtf"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\BuildCache\cxfreeze\*"; DestDir: "{app}\"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{autodesktop}\OpenIDC 后端管理"; Filename: "http://127.0.0.1:1880"; IconFilename: "{app}\HostConfig\HostManage.ico"; IconIndex: 0
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[run]
Filename: "{app}\HostConfig\setup-nssm.exe";Parameters:"install OpenIDCS-Backends {app}\OpenIDCS-Client.exe";Description:"注册后端服务中...";StatusMsg:"注册后端服务中，请耐心等待......";Flags: waituntilterminated runhidden
Filename: "{app}\HostConfig\setup-nssm.exe";Parameters:"set     OpenIDCS-Backends AppDirectory  {app}\";Description:"注册后端服务中...";StatusMsg:"注册后端服务中，请耐心等待......";Flags: waituntilterminated runhidden
Filename: "{app}\HostConfig\setup-nssm.exe";Parameters:"start   OpenIDCS-Backends";Description:"启动后端服务中...";StatusMsg:"启动后端服务中，请耐心等待......";Flags: waituntilterminated runhidden


[UninstallRun]
Filename: "{app}\HostConfig\setup-nssm.exe";Parameters:"stop    OpenIDCS-Backends";StatusMsg:"停止后端服务中，请耐心等待......";Flags: waituntilterminated runhidden
Filename: "{app}\HostConfig\setup-nssm.exe";Parameters:"remove  OpenIDCS-Backends ";StatusMsg:"删除后端服务中，请耐心等待......";Flags: waituntilterminated runhidden
