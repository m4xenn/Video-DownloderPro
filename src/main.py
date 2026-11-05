import sys
import os


def _preload_media():
    # Only imports: no source is opened and no HTTP request is made. Preparing
    # this while WebView initializes avoids moving startup work to the first click.
    try:
        import services.site_resolver
    except ImportError:
        pass  # History/settings stay usable; source inspection reports the error.

# app.py'den Flask uygulamamızı içe aktarıyoruz

def start_window():
    # Claim the desktop instance before importing app (which creates queue/store
    # objects) or starting a browser bridge. A duplicate must not touch that state.
    from services.app_lifecycle import SingleInstance, lifecycle_text, native_notice
    instance = SingleInstance()
    if not instance.acquire():
        native_notice(lifecycle_text()['alreadyRunning'])
        return False
    try:
        return _start_window()
    finally:
        instance.close()


def _start_window():
    import webview
    webview.settings['ALLOW_DOWNLOADS']=False
    webview.settings['IGNORE_SSL_ERRORS']=False
    webview.settings['ALLOW_FILE_URLS']=False
    from app import app, download_manager, ensure_download_state
    from services.site_browser import site_browser
    from services.notification_service import notification_icon_path
    from services.extension_bridge import extension_bridge
    from services.app_lifecycle import ShutdownController
    try:
        extension_bridge.start()
    except OSError:
        pass  # Optional companion must not prevent normal application startup.
    site_browser.enabled = True
    ensure_download_state()
    import threading
    threading.Thread(target=_preload_media, daemon=True, name='media-preload').start()
    # Uygulama başlığını ve başlangıç sayfası özelliklerini ayarlıyoruz
    window = webview.create_window(
        'Video Downloader Pro',
        app, 
        width=900, 
        height=750, 
        resizable=True,
        maximized=True,
        min_size=(600, 500),
        background_color='#060914'
    )
    
    def cleanup():
        site_browser.close_all()
        extension_bridge.close()

    shutdown = ShutdownController(window, download_manager, cleanup)
    window.events.closing += shutdown.on_closing
    def protect_ui():
        from services.browser_security import protect_main_window
        try:protect_main_window(window)
        except Exception:
            # Never leave a privileged window open after guard initialization fails.
            window.destroy()
    window.events.loaded += protect_ui

    # Masaüstü penceresi başlatılıyor
    try:
        webview.start(icon=str(notification_icon_path()))
    finally:
        download_manager.close()
        cleanup()

if __name__ == '__main__':
    # freeze support
    import multiprocessing
    multiprocessing.freeze_support()
    
    start_window()
