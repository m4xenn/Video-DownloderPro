"""Isolated current-user install/upgrade fixture using actual old/new payloads.
The production installer requires admin; this fixture changes identity, privilege,
shortcuts and destination only. It is not a fresh-Windows or UAC test.
"""
import hashlib,json,os,subprocess,sys,time,urllib.request,winreg
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
VERSION=json.loads((ROOT/'version.json').read_text(encoding='utf-8'))['version']
BASE=ROOT/('build/installer-acceptance-'+VERSION)
IDENTITY='VideoDownloaderProAcceptance-'+VERSION.replace('.','-')
KEY=r'Software\Microsoft\Windows\CurrentVersion\Uninstall' + chr(92) + IDENTITY + '_is1'
ISCC=Path(os.environ['ProgramFiles(x86)'])/'Inno Setup 6/ISCC.exe'
OLD=Path(os.environ['ProgramFiles(x86)'])/'Studio Downloader'
NEW=ROOT/'dist/YoutubePro'
INSTALL=BASE/'installed'
DATA=BASE/'profile'
REPORT={'scope':'isolated current-user installer fixture; production identity/admin/shortcuts overridden','checks':[],'status':'running'}
def record(message):
    REPORT['checks'].append(message);print(message,flush=True)
    (BASE/'result.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
def registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY) as key:
            return winreg.QueryValueEx(key,'DisplayVersion')[0]
    except FileNotFoundError:return None

def fixture_uninstaller():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY) as key:
        path=Path(winreg.QueryValueEx(key,'UninstallString')[0].strip('"')).resolve()
    assert path.parent==INSTALL.resolve() and path.name.startswith('unins'),str(path)
    return path
def run_setup(exe,label,expected=0):
    log=BASE/(label+'.log')
    proc=subprocess.run([str(exe),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/NOICONS','/TASKS=',f'/DIR={INSTALL}',f'/LOG={log}'],capture_output=True,text=True,timeout=120)
    if expected==0:assert proc.returncode==0,(label,proc.returncode)
    else:assert proc.returncode!=0,(label,proc.returncode)
    return proc.returncode
def build_fixture(version,source):
    text=(ROOT/'build_assets/YoutubePro_Setup.iss').read_text(encoding='utf-8')
    text=text.replace('AppId=Studio Downloader','AppId='+IDENTITY)
    text=text.replace("'Studio Downloader'","'"+IDENTITY+"'")
    text=text.replace('PrivilegesRequired=admin','PrivilegesRequired=lowest')
    text=text.replace('DefaultDirName={autopf}\\Studio Downloader','DefaultDirName='+str(INSTALL))
    text=text.replace('DefaultGroupName=Video Downloader Pro','DefaultGroupName='+IDENTITY)
    text=text.replace('OutputDir={#ProjectRoot}\\releases\\v{#MyAppVersion}','OutputDir='+str(BASE/'packages'/version))
    text=text.replace('SetupMutex=VideoDownloaderProSetup','SetupMutex='+IDENTITY)
    text=text.replace('Source: "{#ProjectRoot}\\dist\\YoutubePro\\*"','Source: "'+str(source/'*')+'"')
    text=text.replace('Flags: ignoreversion recursesubdirs createallsubdirs', 'Excludes: "unins*.exe,unins*.dat"; Flags: ignoreversion recursesubdirs createallsubdirs')
    # The fixture must never create production shortcuts or launch after install.
    begin=text.index('[Icons]');end=text.index('[Code]')
    text=text[:begin]+text[end:]
    script=BASE/('fixture-'+version+'.iss');script.write_text(text,encoding='utf-8')
    with (BASE/('compile-'+version+'.log')).open('w',encoding='utf-8') as log:
        command=[str(ISCC),'/DMyAppVersion='+version,'/DProjectRoot='+str(ROOT),str(script)]
        for attempt in range(3):
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            log.flush()
            if result.returncode==0:break
            error=(BASE/('compile-'+version+'.log')).read_text(encoding='utf-8',errors='replace')
            if attempt==2 or 'EndUpdateResource failed' not in error:
                result.check_returncode()
            time.sleep(.5)
    return BASE/'packages'/version/'VideoDownloaderPro_Setup.exe'
def seed():
    sys.path.insert(0,str(ROOT/'src'))
    from services.download_store import DownloadStore
    DATA.mkdir(parents=True,exist_ok=True)
    profile=DATA/'YoutubePro';profile.mkdir(exist_ok=True)
    settings={'language':'tr','concurrency_mode':'manual','concurrent_downloads':2,'speed_limit_mbps':'5','auto_compress':False}
    (profile/'settings.json').write_text(json.dumps(settings),encoding='utf-8')
    media=BASE/'Acceptance sample.mp4'
    ffmpeg=Path(os.environ['APPDATA'])/'YoutubePro/bin/ffmpeg.exe'
    subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=s=640x360:r=24','-f','lavfi','-i','sine=frequency=440','-t','2','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(media)],check=True,timeout=30)
    store=DownloadStore(profile/'downloads.sqlite3')
    record={'id':'acceptance-history','media_key':'fixture:acceptance','url':'https://example.com/acceptance.mp4','title':'Kurulum testi videosu','thumbnail':'','format':'video','quality':'max','embed_subs':False,'path':str(media),'size':media.stat().st_size,'completed_at':'2026-10-18T12:00:00+00:00'}
    job={'url':'https://example.com/paused.mp4','options':{'format':'video','quality':'max','embed_subs':False},'path':str(BASE),'bin_dir':'','id':'acceptance-paused','title':'Korunan yar\u0131m indirme','status':'paused','percent':42,'total_bytes':1000000,'downloaded_bytes':420000}
    store.commit_queue([job],[record]);store.save_drafts([{'url':'https://example.com/draft.mp4','title':'Korunan kuyruk kayd\u0131','thumbnail':''}])
    return profile,settings

def launch():
    env=dict(os.environ,APPDATA=str(DATA),VIDEO_DOWNLOADER_DATA_DIR=str(DATA/'YoutubePro'))
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    proc=subprocess.Popen([str(INSTALL/'YoutubePro.exe')],env=env,startupinfo=startup)
    try:
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            if proc.poll() is not None:raise RuntimeError('Installed app exited: '+str(proc.returncode))
            for conn in psutil.Process(proc.pid).net_connections(kind='tcp'):
                if conn.status==psutil.CONN_LISTEN and conn.laddr.ip=='127.0.0.1':
                    url='http://127.0.0.1:'+str(conn.laddr.port)
                    try:
                        with urllib.request.urlopen(url+'/',timeout=2) as response:html=response.read().decode()
                        if 'Video Downloader Pro' in html:return proc,url,html
                    except OSError:pass
            time.sleep(.25)
        raise RuntimeError('Installed application did not serve UI')
    except BaseException:
        stop(proc);raise

def stop(proc):
    if proc.poll() is not None:return
    children=psutil.Process(proc.pid).children(recursive=True)
    for child in reversed(children):
        try:child.terminate()
        except psutil.NoSuchProcess:pass
    proc.terminate();proc.wait(timeout=10);psutil.wait_procs(children,timeout=5)
def get(url,path):
    with urllib.request.urlopen(url+path,timeout=5) as response:return json.load(response)
def verify_payload(source):
    paths=[p for p in source.rglob('*') if p.is_file()]
    for path in paths:
        target=INSTALL/path.relative_to(source)
        assert target.is_file(),str(target)
        assert hashlib.sha256(path.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest(),str(target)
    return len(paths)

def main():
    BASE.mkdir(parents=True,exist_ok=True)
    assert registered() is None,'A previous test fixture is still installed; inspect before retrying'
    oldversion=json.loads((OLD/'_internal/version.json').read_text())['version'];assert tuple(map(int,oldversion.split('.')))<tuple(map(int,VERSION.split('.'))),oldversion
    old=build_fixture(oldversion,OLD);new=build_fixture(VERSION,NEW)
    record('Compiled isolated fixtures from installed and current packaged payloads')
    profile,settings=seed()
    run_setup(old,'old-clean-install');assert registered()==oldversion
    record('Previous-version clean install succeeded in isolated current-user fixture')
    proc,url,html=launch()
    try:
        assert oldversion in html
        assert get(url,'/get-settings')['speed_limit_mbps']=='5'
        assert get(url,'/history')['total']==1
        assert len(get(url,'/queue/drafts')['items'])==1
    finally:stop(proc)
    record('Previous-version app launched and read synthetic settings/history/draft queue')
    run_setup(new,'upgrade');assert registered()==VERSION
    count=verify_payload(NEW);record('Installed -> current upgrade succeeded; '+str(count)+' installed payload files match distributable SHA-256')
    proc,url,html=launch()
    try:
        assert VERSION in html
        actual=get(url,'/get-settings');assert all(actual[k]==v for k,v in settings.items()),actual
        assert get(url,'/history')['total']==1
        assert len(get(url,'/queue/drafts')['items'])==1
        assert get(url,'/progress')['items'][0]['status']=='paused'
    finally:stop(proc)
    record('Upgraded app launched with settings, language, history, draft and paused job preserved')
    run_setup(new,'same-version-blocked',expected=1);assert registered()==VERSION;verify_payload(NEW)
    record('Same-version reinstall rejected without changing application files')
    run_setup(old,'downgrade-blocked',expected=1);assert registered()==VERSION;verify_payload(NEW)
    record('Downgrade to previous version rejected without changing application files')
    uninstaller=fixture_uninstaller()
    proc=subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(BASE/'uninstall.log')],timeout=60)
    assert proc.returncode==0
    deadline=time.monotonic()+15
    while time.monotonic()<deadline and (INSTALL/'YoutubePro.exe').exists():time.sleep(.2)
    assert not (INSTALL/'YoutubePro.exe').exists() and registered() is None
    assert (profile/'settings.json').exists() and (profile/'downloads.sqlite3').exists()
    record('Uninstall removed isolated application/registry while preserving profile data')
    run_setup(new,'new-clean-install');assert registered()==VERSION;verify_payload(NEW)
    record('Current-version clean application install succeeded in isolated fixture')
    REPORT['status']='passed';record('Fixture left installed for visual UI acceptance; production installation untouched')
    print(json.dumps(REPORT,indent=2),flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as exc:
        REPORT['status']='failed';REPORT['error']=str(exc)
        BASE.mkdir(parents=True,exist_ok=True);(BASE/'result.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
        raise
