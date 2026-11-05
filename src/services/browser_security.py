"""Least-privilege policy for the disposable remote media inspection window."""
from services.security_policy import public_link
import threading

_dns_slots=threading.BoundedSemaphore(64)


def navigation_allowed(uri):
    return uri=='about:blank' or public_link(uri)


def protect_main_window(window):
    """Keep the privileged local UI from navigating to a pasted remote page."""
    from urllib.parse import urlsplit
    from System import Func,Object
    def install():
        if getattr(window,'_vdp_navigation_guard',None):return
        core=window.native.webview.CoreWebView2
        trusted=urlsplit(str(core.Source))
        if trusted.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Untrusted application origin')
        def navigating(sender,args):
            try:
                target=urlsplit(str(args.Uri))
                if (target.scheme,target.netloc)!=(trusted.scheme,trusted.netloc):args.Cancel=True
            except ValueError:args.Cancel=True
        core.NavigationStarting += navigating
        window._vdp_navigation_guard=navigating
    window.native.webview.Invoke(Func[Object](install))


def install_browser_security(core, control):
    # Keep every delegate alive for the lifetime of the owning NativeFrames.
    from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState
    def navigating(sender,args):
        if not navigation_allowed(str(args.Uri)):
            args.Cancel=True
    def permission(sender,args):
        args.State=CoreWebView2PermissionState.Deny
        if hasattr(args,'SavesInProfile'):args.SavesInProfile=False
        if hasattr(args,'Handled'):args.Handled=True
    def download(sender,args):
        args.Cancel=True
        args.Handled=True
    def external(sender,args):args.Cancel=True
    def resource(sender,args):
        uri=str(args.Request.Uri)
        if uri.startswith(('data:','blob:')) or uri=='about:blank':return
        def deny():
            args.Response=core.Environment.CreateWebResourceResponse(None,403,'Blocked by application security','Content-Length: 0\r\n')
        if not public_link(uri):
            deny();return
        # Get a deferral instead of blocking the browser's UI thread on DNS.
        # Check every resource, including redirects, child frames and workers.
        deferral=args.GetDeferral()
        if not _dns_slots.acquire(blocking=False):
            deny();deferral.Complete();return
        def check():
            allowed=False
            try:allowed=public_link(uri,resolve=True)
            finally:
                _dns_slots.release()
                from System import Action
                def finish():
                    try:
                        if not allowed:deny()
                    finally:deferral.Complete()
                try:control.BeginInvoke(Action(finish))
                except Exception:deferral.Complete()
        threading.Thread(target=check,daemon=True).start()
    core.NavigationStarting += navigating
    core.PermissionRequested += permission
    core.DownloadStarting += download
    core.WebResourceRequested += resource
    # Older WebView2 SDKs may omit this event. NavigationStarting still denies
    # custom protocols; no external application is deliberately launched here.
    try:core.LaunchingExternalUriScheme += external
    except AttributeError:pass
    core.Settings.AreHostObjectsAllowed=False
    core.Settings.AreDefaultScriptDialogsEnabled=False
    core.Settings.AreDefaultContextMenusEnabled=False
    core.Settings.AreDevToolsEnabled=False
    core.Settings.AreBrowserAcceleratorKeysEnabled=False
    core.Settings.IsPasswordAutosaveEnabled=False
    core.Settings.IsGeneralAutofillEnabled=False
    return (navigating,permission,download,external,resource)
