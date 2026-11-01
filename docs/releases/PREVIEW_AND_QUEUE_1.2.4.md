# Video Downloader Pro 1.2.4

## Önizleme

İndirme tamamlanınca kaynak metadata'sındaki kapak görselleri öncelikli olarak denenir. TikTok/Instagram/YouTube için yt-dlp'nin sunduğu kapak adresleri kullanılır; gerektiğinde kaynak başlıkları ve yt-dlp ağ oturumu korunur. Görsel küçük JPEG olarak yerel önbelleğe kaydedilir; süresi dolan uzak URL'ye sürekli bağımlılık azalır.

Kapak yüklenemez, bozuk veya neredeyse tamamen siyahsa FFmpeg ile videonun %50 noktasından kare alınır. O kare de siyahsa %35 ve %65 noktaları denenir. Kullanılabilir kare yoksa nötr simge gösterilir. Siyah tespiti basit parlaklık kontrolüdür; anlamsal sahne seçimi yapmaz. Çok karanlık sahneler bu nedenle atlanabilir.

Görseller en fazla 400×400 sınırına küçültülür. Uzak görsel 8 MB ve 20 milyon piksel ile sınırlandırılır; ağ ve FFmpeg isteklerinde zaman aşımı vardır. Önizleme hatası başarılı medya indirmesini hatalı saymaz. Ses dosyasında kaynak kapağı denenir, video karesi çıkarılmaz.

Önbellek `%APPDATA%/YoutubePro/previews` içindedir. Bu değişiklik uygulamanın kuyruk önizlemesini düzeltir; videonun içeriğini veya Windows Explorer'ın kendi küçük resim seçimini değiştirmez.

## Kuyruk satırı

- Başlık en fazla iki satırda gösterilir; tamamı başlık üzerine gelince okunabilir.
- Uzun URL yerine platform adı, MP4/MP3 gibi çıktı biçimi ve boyut tek metadata satırındadır. Tam URL kaynak adı üzerinde bekleyince görülebilir.
- İndirme sırasında hız, yüzde ve varsa kalan süre korunur.
- Tamamlanınca yüzde ve ilerleme çubuğu kaldırılır; yeşil “Tamamlandı” durumu gösterilir. İş kalmadığında sıfır hız/eşzamanlılık özeti gizlenir.
- Yeni yerel kapak oluştuğunda mevcut satırın görseli güncellenir. Aynı görsel her ilerleme sorgusunda tekrar yüklenmez.

## Yeniden açılış

Tamamlanan işler aynı oturumda görülebilir. Yeni uygulama oturumunda `finished` ve liste açma sırasında kullanılan `expanded` kayıtlar kuyruğa geri yüklenmez. Geçmiş korunur. Yarım kalan işler duraklatılmış olarak döner; hatalı işler tekrar denenebilir. Video dosyaları silinmez.

## Doğrulama

143 hedefli Python testi ve 51 JavaScript kontrolü geçti. Yeni kontroller kapak önceliği, siyah/bozuk kapak, alternatif kaynak kapağı, siyah orta kareden yakın kareye geçiş, güvenli yerel görsel sunumu, mevcut satır görselinin güncellenmesi ve yeniden açılışta geçmişin korunmasını kapsar.

- FFmpeg ile ilk saniyesi siyah, devamı renkli olan gerçek video üretildi. Orta kare çıkarımı siyah yerine renkli kare döndürdü.
- Bu video gerçek arayüzden indirildi; küçük resim `/previews/<id>.jpg` üzerinden yüklendi ve sade tamamlanmış satır incelendi.
- Aynı SQLite verisini okuyan yeni uygulama sürecinde `/progress` boş kuyruk, `/history` bir tamamlanmış kayıt döndürdü.
- Yerel HTTP sunucusundan gerçek JPEG kapağı yt-dlp ağ katmanıyla alındı. MP4/MP3 indirmeleri, ikinci kopyada dosya adının korunması, HLS, toplam hız sınırı ve duraklat/devam testleri tekrar geçti.
- Canlı TikTok/Instagram hesabı veya çerezleriyle kabul testi bu çalışmada yapılmadı. Kaynağın kapak sunması erişim ve extractor desteğine bağlıdır; alınamadığında yerel kare kullanılır.

Görsel: `tests/queue-preview-fixed.png`.

```powershell
python -m unittest discover -s tests -p test_previews.py -v
node tests/test_queue_preview_ui.cjs
python tests/preview_library.py --empty --black-start
```

Kurulum: `releases/v1.2.4/VideoDownloaderPro_Setup.exe`. Önce mevcut uygulamayı kapat. Windows/WebView2 üzerinde son kurulum kabul kontrolü ayrıca yapılmalıdır; GitHub'a yayın yapılmadı.
