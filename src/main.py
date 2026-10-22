import sys
import os

# app.py'den Flask uygulamamızı içe aktarıyoruz

def start_window():
    import webview
    from app import app, download_manager, ensure_download_state
    from services.site_browser import site_browser
    from services.notification_service import notification_icon_path
    site_browser.enabled = True
    ensure_download_state()
    # Uygulama başlığını ve başlangıç sayfası özelliklerini ayarlıyoruz
    window = webview.create_window(
        'Video Downloader Pro',
        app, 
        width=900, 
        height=750, 
        resizable=True,
        maximized=True,
        min_size=(600, 500)
    )
    
    window.events.closed += lambda: site_browser.close_all()

    # Masaüstü penceresi başlatılıyor
    try:
        webview.start(icon=str(notification_icon_path()))
    finally:
        site_browser.close_all()
        download_manager.close()

if __name__ == '__main__':
    # freeze support
    import multiprocessing
    multiprocessing.freeze_support()
    
    start_window()
