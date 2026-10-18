# ============================================================
#  src/utils/i18n.py
#  Python tarafı çeviri sistemi
#
#  app.py'den taşındı (FAZ 1):
#    - py_i18n sözlüğü (orijinal L85-110)
#    - get_i18n() fonksiyonu (orijinal L112-114)
#
#  Değişiklik: get_i18n() artık `lang` parametresi alıyor.
#  Çağıran taraf: get_i18n("key", current_lang)
# ============================================================

# Desteklenen diller ve çeviriler
py_i18n = {
    "tr": {
        "success": "İndirme işlemi başarıyla tamamlandı!",
        "err_link": "Link hatalı, kilitli veya yayın şu anda çevrimdışı.",
        "err_folder": "Klasör Seçilmedi!",
        "err_empty": "Liste boş!",
        "unknown_vid": "Bilinmeyen Video/Liste",
        "unknown_link": "Bilinmeyen Bağlantı (İndirilebilir)"
    },
    "en": {
        "success": "Download completed successfully!",
        "err_link": "Invalid link, locked, or stream offline.",
        "err_folder": "No folder selected!",
        "err_empty": "Queue is empty!",
        "unknown_vid": "Unknown Video/Playlist",
        "unknown_link": "Unknown Link (Downloadable)"
    },
    "es": { "success": "¡Descarga completada con éxito!", "err_link": "Enlace inválido, bloqueado o transmisión fuera de línea.", "err_folder": "¡No se seleccionó ninguna carpeta!", "err_empty": "¡La cola está vacía!", "unknown_vid": "Video/Lista Desconocida", "unknown_link": "Enlace Desconocido" },
    "fr": { "success": "Téléchargement terminé avec succès !", "err_link": "Lien invalide, verrouillé ou flux hors ligne.", "err_folder": "Aucun dossier sélectionné !", "err_empty": "La file d'attente est vide !", "unknown_vid": "Vidéo/Playlist inconnue", "unknown_link": "Lien Inconnu" },
    "de": { "success": "Download erfolgreich abgeschlossen!", "err_link": "Ungültiger Link, gesperrt oder Stream offline.", "err_folder": "Kein Ordner ausgewählt!", "err_empty": "Warteschlange ist leer!", "unknown_vid": "Unbekanntes Video/Playlist", "unknown_link": "Unbekannter Link" },
    "ru": { "success": "Скачивание успешно завершено!", "err_link": "Неверная ссылка, заблокирована или трансляция оффлайн.", "err_folder": "Папка не выбрана!", "err_empty": "Очередь пуста!", "unknown_vid": "Неизвестное видео/плейлист", "unknown_link": "Неизвестная ссылка" },
    "pt": { "success": "Download concluído com sucesso!", "err_link": "Link inválido, bloqueado ou stream offline.", "err_folder": "Nenhuma pasta selecionada!", "err_empty": "A fila está vazia!", "unknown_vid": "Vídeo/Playlist Desconhecido", "unknown_link": "Link Desconhecido" },
    "zh": { "success": "下载成功完成！", "err_link": "链接无效、被锁定或直播离线。", "err_folder": "未选择文件夹！", "err_empty": "队列为空！", "unknown_vid": "未知的视频/播放列表", "unknown_link": "未知的链接" },
    "ja": { "success": "ダウンロードが正常に完了しました！", "err_link": "無効なリンク、ロックされている、またはストリームがオフラインです。", "err_folder": "フォルダが選択されていません！", "err_empty": "キューが空です！", "unknown_vid": "不明なビデオ/プレイリスト", "unknown_link": "不明なリンク" },
    "hi": { "success": "डाउनलोड सफलतापूर्वक पूरा हुआ!", "err_link": "अवैध लिंक, लॉक किया गया, या स्ट्रीम ऑफ़लाइन।", "err_folder": "कोई फ़ोल्डर नहीं चुना गया!", "err_empty": "कतार खाली है!", "unknown_vid": "अज्ञात वीडियो/प्लेलिस्ट", "unknown_link": "अज्ञात लिंक" }
}


def get_i18n(key, lang="en"):
    """
    Verilen anahtar için aktif dile göre çeviri döndürür.

    Args:
        key  (str): Çeviri anahtarı (örn: "success", "err_folder")
        lang (str): Dil kodu (örn: "tr", "en"). Bilinmiyorsa "en" kullanılır.

    Returns:
        str: Çevrilmiş metin. Anahtar bulunamazsa İngilizce fallback, o da yoksa key'in kendisi döner.
    """
    active_lang = lang if lang in py_i18n else "en"
    return py_i18n[active_lang].get(key, py_i18n["en"].get(key, key))
