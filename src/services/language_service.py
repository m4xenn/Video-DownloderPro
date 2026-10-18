"""Resolve supported UI languages without changing the process locale."""
import locale
import sys

SUPPORTED_LANGUAGES = frozenset(('tr', 'en', 'es', 'fr', 'de', 'ru', 'pt', 'zh', 'ja', 'hi'))


def supported_language(value):
    if not isinstance(value, str):
        return None
    language = value.strip().replace('_', '-').split('-')[0].lower()
    return language if language in SUPPORTED_LANGUAGES else None


def system_language():
    if sys.platform == 'win32':
        try:
            import ctypes
            language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            language = supported_language(locale.windows_locale.get(language_id))
            return language or 'en'
        except (AttributeError, OSError, ValueError):
            pass
    try:
        return supported_language(locale.getlocale()[0]) or 'en'
    except (ValueError, TypeError):
        return 'en'
