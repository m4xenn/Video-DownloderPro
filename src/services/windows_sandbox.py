"""Windows write confinement and resource limits for media subprocesses.

Low integrity does NOT prevent reading the current user's files; this is not
a full AppContainer. No ACLs outside a job's workspace are modified.
"""
import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import threading

_job_lock = threading.Lock()
_global_job = None


def shared_media_job():
    """Bound all concurrent media parsers, not just one hostile process."""
    global _global_job
    import win32job as job, psutil
    with _job_lock:
        if _global_job is None:
            handle = job.CreateJobObject(None, '')
            try:
                limits = job.QueryInformationJobObject(handle, job.JobObjectExtendedLimitInformation)
                limits['BasicLimitInformation']['LimitFlags'] = 0x2000 | 0x8 | 0x400 | 0x200
                limits['BasicLimitInformation']['ActiveProcessLimit'] = 64
                limits['JobMemoryLimit'] = max(2 * 1024**3, min(8 * 1024**3, psutil.virtual_memory().total // 2))
                job.SetInformationJobObject(handle, job.JobObjectExtendedLimitInformation, limits)
            except BaseException:
                handle.Close()
                raise
            _global_job = handle
        return _global_job


class SandboxUnavailable(OSError):
    code = 'security_unavailable'
    def __init__(self):
        super().__init__('[security_unavailable] Media process protection could not be initialized.')


def protect_workspace(path):
    import win32api, win32con, win32security as security
    token = security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        user = security.ConvertSidToStringSid(security.GetTokenInformation(token, security.TokenUser)[0])
    finally:
        token.Close()
    descriptor = security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        f'D:P(A;OICI;FA;;;{user})(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)S:(ML;OICI;NW;;;LW)', 1)
    security.SetFileSecurity(str(path), security.DACL_SECURITY_INFORMATION | 0x10, descriptor)


class StartupInfo(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR), ('lpTitle', w.LPWSTR),
                ('dwX', w.DWORD), ('dwY', w.DWORD), ('dwXSize', w.DWORD), ('dwYSize', w.DWORD),
                ('dwXCountChars', w.DWORD), ('dwYCountChars', w.DWORD), ('dwFillAttribute', w.DWORD),
                ('dwFlags', w.DWORD), ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                ('lpReserved2', ctypes.c_void_p), ('hStdInput', w.HANDLE), ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]


def restore_file_integrity(path):
    """A completed file must not retain its worker's low-integrity write label."""
    import win32api, win32con, win32security as security
    token = security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        sid = security.ConvertSidToStringSid(security.GetTokenInformation(token, security.TokenIntegrityLevel)[0])
    finally:
        token.Close()
    descriptor = security.ConvertStringSecurityDescriptorToSecurityDescriptor(f'S:(ML;;NW;;;{sid})', 1)
    security.SetFileSecurity(str(path), 0x10, descriptor)


class StartupInfoEx(ctypes.Structure):
    _fields_ = [('startup', StartupInfo), ('attributes', ctypes.c_void_p)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]


def create_media_process(arguments, handles, environment=None):
    """Create suspended; attach limits before executing any application code."""
    import win32api, win32con as con, win32security as security, win32job as job, win32process
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.c_size_t)]
    kernel.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, w.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
    kernel.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    advapi.CreateProcessAsUserW.argtypes = [w.HANDLE, w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL,
                                          w.DWORD, ctypes.c_void_p, w.LPCWSTR, ctypes.POINTER(StartupInfoEx), ctypes.POINTER(ProcessInfo)]
    original = security.OpenProcessToken(win32api.GetCurrentProcess(), con.TOKEN_DUPLICATE | con.TOKEN_ASSIGN_PRIMARY | con.TOKEN_QUERY | con.TOKEN_ADJUST_DEFAULT)
    restricted = None
    limits_handle = None
    info = ProcessInfo()
    attributes = None
    startup = StartupInfoEx()
    try:
        disabled = [(sid, 0) for sid, _ in security.GetTokenInformation(original, security.TokenGroups)
                    if security.ConvertSidToStringSid(sid) in ('S-1-5-32-544', 'S-1-5-32-547')]
        restricted = security.CreateRestrictedToken(original, 1, disabled, [], [])
        security.SetTokenInformation(restricted, security.TokenIntegrityLevel,
                                     (security.ConvertStringSidToSid('S-1-16-4096'), 0x20))
        limits_handle = job.CreateJobObject(None, '')
        limits = job.QueryInformationJobObject(limits_handle, job.JobObjectExtendedLimitInformation)
        limits['BasicLimitInformation']['LimitFlags'] = 0x2000 | 0x8 | 0x400 | 0x200
        limits['BasicLimitInformation']['ActiveProcessLimit'] = 6
        import psutil
        limits['JobMemoryLimit'] = max(2 * 1024**3, min(8 * 1024**3, psutil.virtual_memory().total // 2))
        job.SetInformationJobObject(limits_handle, job.JobObjectExtendedLimitInformation, limits)
        startup.startup.cb = ctypes.sizeof(startup)
        startup.startup.dwFlags = 1
        inherited = [int(value) for value in handles] if -1 not in handles else []
        flags = 0x4 | 0x80000 | 0x400 | 0x08000000
        if inherited:
            startup.startup.dwFlags |= 0x100
            startup.startup.hStdInput, startup.startup.hStdOutput, startup.startup.hStdError = inherited
            size = ctypes.c_size_t()
            kernel.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
            attributes = ctypes.create_string_buffer(size.value)
            if not kernel.InitializeProcThreadAttributeList(attributes, 1, 0, ctypes.byref(size)):
                raise ctypes.WinError(ctypes.get_last_error())
            startup.attributes = ctypes.cast(attributes, ctypes.c_void_p)
            handle_array = (w.HANDLE * len(set(inherited)))(*sorted(set(inherited)))
            if not kernel.UpdateProcThreadAttribute(startup.attributes, 0, 0x20002, handle_array, ctypes.sizeof(handle_array), None, None):
                raise ctypes.WinError(ctypes.get_last_error())
        executable = str(Path(arguments[0]).absolute())
        if not Path(executable).suffix and Path(executable + '.exe').is_file():
            executable += '.exe'
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline([executable, *(str(a) for a in arguments[1:])]))
        env = dict(os.environ if environment is None else environment)
        for key in list(env):
            if key.upper().startswith(('PYTHON', 'QT_', 'LD_', 'DYLD_')):
                env.pop(key)
        env_block = ctypes.create_unicode_buffer('\0'.join(f'{k}={v}' for k, v in sorted(env.items(), key=lambda item: item[0].upper())) + '\0\0')
        if not advapi.CreateProcessAsUserW(int(restricted), executable, command, None, None, bool(inherited), flags,
                                          env_block, str(Path(executable).parent), ctypes.byref(startup), ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        job.AssignProcessToJobObject(shared_media_job(), int(info.process))
        job.AssignProcessToJobObject(limits_handle, int(info.process))
        win32process.ResumeThread(int(info.thread))
        result = int(info.process), info.pid, limits_handle
        info.process = None
        limits_handle = None
        return result
    except Exception as error:
        if info.process:
            win32process.TerminateProcess(int(info.process), 1)
        raise SandboxUnavailable() from error
    finally:
        if attributes and startup.attributes:
            kernel.DeleteProcThreadAttributeList(startup.attributes)
        if info.thread:
            kernel.CloseHandle(info.thread)
        if info.process:
            kernel.CloseHandle(info.process)
        if limits_handle:
            limits_handle.Close()
        if restricted:
            restricted.Close()
        original.Close()
