from decimal import Decimal, InvalidOperation

DEFAULTS = {'concurrency_mode': 'auto', 'concurrent_downloads': 3,
            'speed_limit_mbps': '0', 'auto_compress': False}


def normalize_settings(data, strict=True):
    if not isinstance(data, dict):
        raise ValueError('Ayarlar bir nesne olmalı.')
    result = dict(DEFAULTS, **data)
    if result['concurrency_mode'] not in ('auto', 'manual'):
        raise ValueError('İndirme yönetimi otomatik veya manuel olmalı.')
    value = result['concurrent_downloads']
    if isinstance(value, bool) or str(value) not in [str(n) for n in range(1, 11)]:
        raise ValueError('Manuel indirme sayısı 1–10 arasında olmalı.')
    result['concurrent_downloads'] = int(value)
    try:
        if 'speed_limit_mbps' not in data and data.get('speed_limit'):
            rate = Decimal(str(data['speed_limit'])) / 1000  # legacy Kbps
        else:
            rate = Decimal(str(result['speed_limit_mbps'] or '0'))
        if not rate.is_finite() or rate < 0 or rate > 100000:
            raise ValueError('Toplam hız sınırı 0–100000 Mbps arasında olmalı.')
        if 0 < rate < Decimal('0.001'):
            raise ValueError('Pozitif hız sınırı en az 0,001 Mbps olmalı.')
    except (InvalidOperation, TypeError):
        raise ValueError('Geçersiz toplam hız sınırı.')
    result['speed_limit_mbps'] = format(rate, 'f')
    if not isinstance(result['auto_compress'], bool):
        raise ValueError('Geçersiz sıkıştırma ayarı.')
    result.pop('speed_limit', None)
    return result


def bytes_per_second(settings):
    return int(Decimal(settings['speed_limit_mbps']) * 125000)
