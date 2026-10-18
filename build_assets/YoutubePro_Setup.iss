; Version and project root are supplied by scripts/build_release.py.
#ifndef MyAppVersion
  #error Run scripts/build_release.py to supply the version from version.json
#endif
#ifndef ProjectRoot
  #error ProjectRoot is required
#endif

[Setup]
; Preserve the identity of the original Studio Downloader installer.
AppId=Studio Downloader
AppName=Video Downloader Pro
AppVersion={#MyAppVersion}
AppPublisher=Salih
DefaultDirName={autopf}\Studio Downloader
DefaultGroupName=Video Downloader Pro
OutputDir={#ProjectRoot}\releases\v{#MyAppVersion}
OutputBaseFilename=VideoDownloaderPro_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile={#ProjectRoot}\build_assets\icon.ico
UninstallDisplayIcon={app}\YoutubePro.exe
CloseApplications=yes
RestartApplications=no
SetupMutex=VideoDownloaderProSetup
PrivilegesRequired=admin
WizardStyle=modern

[Files]
Source: "{#ProjectRoot}\dist\YoutubePro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Video Downloader Pro"; Filename: "{app}\YoutubePro.exe"
Name: "{group}\Video Downloader Pro Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Video Downloader Pro"; Filename: "{app}\YoutubePro.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek Kısayollar:"

[Run]
Filename: "{app}\YoutubePro.exe"; Description: "Video Downloader Pro'yu başlat"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
procedure CheckInstalledVersion(RootKey: Integer; const AppKey: String;
  var HighestVersion: Int64; var HighestVersionText: String);
var
  VersionText: String;
  ParsedVersion: Int64;
begin
  if RegQueryStringValue(RootKey,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + AppKey + '_is1',
    'DisplayVersion', VersionText) then
  begin
    if StrToVersion(VersionText, ParsedVersion) then
    begin
      if (HighestVersionText = '') or
        (ComparePackedVersion(ParsedVersion, HighestVersion) > 0) then
      begin
        HighestVersion := ParsedVersion;
        HighestVersionText := VersionText;
      end;
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  InstalledVersion, SetupVersion: Int64;
  InstalledVersionText: String;
  Comparison: Integer;
begin
  Result := False;
  InstalledVersion := 0;
  InstalledVersionText := '';
  { Check the original installer identity in both Windows registry views. }
  CheckInstalledVersion(HKLM32, 'Studio Downloader', InstalledVersion, InstalledVersionText);
  CheckInstalledVersion(HKCU32, 'Studio Downloader', InstalledVersion, InstalledVersionText);
  if IsWin64 then
  begin
    CheckInstalledVersion(HKLM64, 'Studio Downloader', InstalledVersion, InstalledVersionText);
    CheckInstalledVersion(HKCU64, 'Studio Downloader', InstalledVersion, InstalledVersionText);
  end;

  if InstalledVersionText <> '' then
  begin
    if not StrToVersion('{#MyAppVersion}', SetupVersion) then
      RaiseException('Kurulum sürüm bilgisi okunamadı.');
    Comparison := ComparePackedVersion(InstalledVersion, SetupVersion);
    if Comparison = 0 then
    begin
      SuppressibleMsgBox('Video Downloader Pro zaten yüklü.' + #13#10 +
        'Yüklü sürüm: ' + InstalledVersionText + #13#10 +
        'Aynı sürümü tekrar kurmanıza gerek yok.', mbInformation, MB_OK, IDOK);
      Exit;
    end;
    if Comparison > 0 then
    begin
      SuppressibleMsgBox('Video Downloader Pro uygulamasının daha yeni bir sürümü zaten yüklü.' + #13#10 +
        'Yüklü sürüm: ' + InstalledVersionText + #13#10 +
        'Bu eski kurulum paketiyle devam edilemez.', mbInformation, MB_OK, IDOK);
      Exit;
    end;
  end;
  { No installation, or an older installed version: allow setup/update. }
  Result := True;
end;
