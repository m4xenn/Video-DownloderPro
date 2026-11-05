"""Application-owned user messages, shared by Python and the web interface."""
from functools import lru_cache
import json
from pathlib import Path
import sys


@lru_cache(maxsize=1)
def catalog():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    return json.loads((root / 'static/message-locales.json').read_text(encoding='utf-8'))


def current_language():
    from services.language_service import supported_language, system_language
    from state.app_state import state
    from utils.file_helpers import load_settings
    if state.get('ui_language_selected'):
        return supported_language(state.get('current_lang')) or 'en'
    return supported_language(load_settings().get('language')) or system_language()


def message(key, language=None, **values):
    copies = catalog()
    language = language or current_language()
    text = copies.get(language, copies['en']).get(key, copies['en'].get(key, copies['en']['generic']))
    for name, value in values.items():
        text = text.replace('{' + name + '}', str(value))
    return text


RAW_KEYS = {
    'Invalid video container.':'error.invalid_container',
    'Invalid recovery folder.':'error.invalid_recovery_folder',
    'Invalid recovery action.':'error.recording_action',
    'Invalid recording recovery action.':'error.recording_action',
    'Recording recovery is still running.':'error.recording_busy',
    'Unsafe link or network destination.':'error.unsafe_link',
    'Geçersiz ayarlar.':'invalid_settings', 'Ayarlar bir nesne olmalı.':'invalid_settings',
    'İndirme yönetimi otomatik veya manuel olmalı.':'invalid_settings',
    'Invalid transfer mode.':'invalid_settings', 'Invalid notification mode.':'invalid_settings',
    'Manuel indirme sayısı 1–10 arasında olmalı.':'invalid_settings',
    'Toplam hız sınırı 0–100000 Mbps arasında olmalı.':'invalid_settings',
    'Pozitif hız sınırı en az 0,001 Mbps olmalı.':'invalid_settings',
    'Geçersiz toplam hız sınırı.':'invalid_settings', 'Geçersiz sıkıştırma ayarı.':'invalid_settings',
    'Ayarlar kaydedilemedi.':'settings_failed','Ayarlar yüklenemedi.':'settings_load_failed',
    'Güncellemenin bitmesini bekleyin.':'wait_update','Güncelleme bitene kadar bekleyin.':'wait_update',
    'Önce aktif indirme veya kurulum işleminin bitmesini bekleyin.':'wait_downloads',
    'Önce aktif video indirmelerinin tamamlanmasını bekleyin.':'wait_downloads',
    'Kurulum için masaüstü uygulamasını kullanın.':'desktop_required',
    'Geçerli bir video bağlantısı girin.':'invalid_link',
    'Yalnız geçerli http/https bağlantıları desteklenir.':'invalid_link',
    'Klasör Seçilmedi!':'folder_missing','No folder selected!':'folder_missing',
    'Recording duration must be 1–1440 minutes.':'live_duration',
    'Recording stop time must be within the next 24 hours.':'live_duration',
    'Live recording requires one inspected live video and MP4 output.':'live_source',
    'Source is no longer live; inspect it again to download the replay.':'live_source',
    'Inspect one live source and choose a recording duration before starting.':'live_source',
    'Live recording currently requires MP4 video output.':'live_source',
    'Aynı format ve kalitede indirilmiş dosyalar bulundu.':'duplicates',
    'Tüm seçilen dosyalar zaten mevcut.':'skipped',
    'Bağlantıların incelenmesini bekleyin.':'inspection_wait',
    'Hata ayrıntıları kopyalandı.':'diagnostic_copied','Error details copied.':'diagnostic_copied',
    'Rapor kopyalandı.':'diagnostic_copied','Report copied.':'diagnostic_copied',
    'Seçili raporu Ctrl+C ile kopyalayabilirsin.':'copy_manually',
    'Press Ctrl+C to copy the selected report.':'copy_manually',
    'Hata ayrıntıları okunamadı.':'diagnostic_failed','Could not read error details.':'diagnostic_failed',
    'Kayıtlar okunamadı.':'records_failed','Could not read records.':'records_failed',
    'Kayıt dosyasına erişilemiyor; rapor eksik olabilir.':'records_unavailable',
    'Records unavailable; the report may be incomplete.':'records_unavailable',
    'Geçmiş okunamadı.':'history_failed','Bekleyen bağlantılar okunamadı.':'drafts_failed',
    'Liste taranamadı.':'playlist_failed',
    'Video bilgileri okunuyor…':'phase.validating_source',
    'Kaynağın kalite seçenekleri inceleniyor...':'phase.validating_source',
    'Kalite bilgisi alınamadı. Yenile düğmesiyle tekrar deneyebilirsin.':'media_info',
    'Video bilgisi alınamadı. Hata raporunu Ayarlar → Sorun giderme kayıtları bölümünden kopyalayabilirsin.':'media_info',
    'Could not read media information. Copy the report from Settings → Troubleshooting records.':'media_info',
    'Tarayıcı açılamadı.':'error.interaction_required',
    'Güncelleme kontrol edilemedi.':'component.failed','Güncelleme durumu alınamadı.':'component.failed',
    'İşlem tamamlanamadı.':'generic',
    'İndirme tamamlanamadı. Ayrıntılar kuyruk satırında korunuyor.':'generic',
    'Download failed. Details are kept in the queue.':'generic',
    'Language preference could not be saved.':'settings_failed',
    'Could not save welcome preference.':'settings_failed',
}


@lru_cache(maxsize=1)
def aliases():
    result = dict(RAW_KEYS)
    for copy in catalog().values():
        for key, text in copy.items():
            if '{' not in text:
                result.setdefault(text, key)
    return result


def identify(text, code=None, path='', status='error', **data):
    if text in aliases():
        return aliases()[text], {}
    if status == 'interaction_required':
        return 'error.interaction_required', {}
    if path.startswith(('/components/', '/app-update/')):
        if status == 'downloading':
            return 'update.downloading', {'percent': data.get('percent', 0)}
        if status == 'checking':
            return 'component.checking', {}
        if status in ('up_to_date', 'finished'):
            return ('component.pending' if data.get('restart_required') else 'component.current'), {}
        if status == 'ready':
            return 'update.ready', {}
        if status == 'installing':
            return 'update.installing', {}
        if status in ('available', 'update_available'):
            return 'component.available', {}
        if status == 'error':
            return 'component.failed', {}
    if str(text).startswith(('Geçmiş okunamadı:',)):
        return 'history_failed', {}
    if str(text).startswith(('Bağlantı kuyruğu kaydedilemedi:',)):
        return 'drafts_failed', {}
    if str(text).startswith('Geçersiz') or text in ('Unsupported language.', 'Invalid onboarding request.'):
        return 'invalid_request', {}
    from services.diagnostics import error_code
    code = code or error_code(text)
    key = 'error.' + str(code)
    if key in catalog()['en']:
        return key, {}
    return ('invalid_settings' if path == '/save-settings' else 'generic'), {}
