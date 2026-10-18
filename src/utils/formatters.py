# ============================================================
#  src/utils/formatters.py
#  Saf formatlama ve temizleme fonksiyonları
#
#  app.py'den taşındı (FAZ 1):
#    - clean_ansi() — progress_hook içindeki inline regex (orijinal L213-214)
# ============================================================

import re


def clean_ansi(text):
    """
    Bir metinden ANSI renk/biçimlendirme kaçış kodlarını temizler.

    Örnek: '\x1b[32m150 KiB/s\x1b[0m' → '150 KiB/s'

    Args:
        text (str): Temizlenecek metin.

    Returns:
        str: ANSI kodları kaldırılmış, başı/sonu boşluksuz metin.
    """
    if not text:
        return text
    return re.sub(r'\x1b\[[0-9;]*m', '', text).strip()
