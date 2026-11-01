# Video Downloader Pro 1.1.5

Bu sürümde onaylanan altı özellik eklendi. Video kesiti indirme eklenmedi.

## Kullanım ve kabul testi

1. **Kalıcı kuyruk:** Bağlantıları ekle, indirmeyi başlatmadan uygulamayı kapatıp aç. Bağlantılar geri gelmeli. Ardından bir indirmeyi başlat, yarıda kapatıp aç. Yarım kalan işler duraklatılmış dönmeli; “Tümüne devam et” veya satırdaki devam düğmesiyle başlatılmalı. Format, kalite, altyazı, hedef klasör ve dosya adı korunur. Kaynağın desteğine göre `.part` dosyasından devam edilir; bazı kaynaklarda baştan indirmek gerekir.
2. **Otomatik yeniden deneme:** Geçici bağlantı, zaman aşımı, HTTP 429/5xx hatalarında uygulama en fazla iki kez daha dener: 5 ve 10 saniye bekler. Satırda geri sayım görünür; beklerken duraklatılabilir veya kaldırılabilir. yt-dlp'nin kendi sınırlı ağ/parça denemeleri de vardır. Gizli/silinmiş içerik, desteklenmeyen format, izin ve disk hataları otomatik döngüye alınmaz. Son hatada kullanıcı tekrar deneyebilir.
3. **Boyut ve kalan süre:** İndirme sırasında boyut ve kaynağın sağladığı ETA gösterilir. Tahmini boyut “≈” ile ayrılır. Bilinmeyen değerler açıkça belirtilir. Ayrı ses/video akışlarında gösterilen ağ ilerlemesi ve ETA o an indirilen akışa aittir; FFmpeg işleme süresini kapsamaz. Tamamlanınca gerçek çıktı boyutu gösterilir. Önizleme boyutu seçilecek nihai kaliteyi garanti etmez.
4. **Playlist seçimi:** Liste bağlantısını ekle, “Oynatma Listesi Olarak İndir” seçeneğini aç ve başlat. Önce seçim penceresi açılmalı; seçim onayından önce medya indirmesi başlamamalı. Arama, sonuçları seç, tüm seçimi temizle ve “Seçilenleri indir” düğmelerini dene. Gizli/silinmiş öğeler seçilemez. İlk 2000 öğe taranır; büyük listelerde bu sınır belirtilir. Ekran 100 satırlık gruplar halinde açılır. En fazla 20 kaynak liste tek taramada kabul edilir. Farklı listelerin videoları kendi liste klasörlerine ayrılır.
5. **İndirme geçmişi:** Üst araç çubuğundaki saat simgesini aç. Başarılı yeni indirmeler başlık, format, kalite, zaman, boyut ve yoluyla görünür. Ara, dosyayı aç, klasörde göster ve tekrar indir seçeneklerini dene. Dosyayı taşıdıysan/sildiysen kayıt korunur; açma düğmeleri kapanır, tekrar indirme kullanılabilir. Önceki sürümlerdeki eski dosyalar otomatik olarak geçmişe aktarılmaz.
6. **Tekrarlanan indirme uyarısı:** Başarılı indirdiğin videoyu aynı format, kalite ve altyazı seçimiyle yeniden başlat. Dosya hâlâ mevcutsa uyarı çıkmalı. “Mevcutları atla” listede yalnız yeni videoları başlatır; hepsi mevcutsa indirme yapmaz. “Yeniden indir” eski dosyayı koruyup yeni ada `(1)`, `(2)` ekler. İptal indirme başlatmaz. Farklı format/kalite/altyazı seçimi ayrı çıktı sayılır. YouTube kısa, normal ve shorts bağlantıları aynı video kimliğiyle eşleştirilir; diğer kaynaklarda medya kimliği veya normalleştirilmiş bağlantı kullanılır. Bu bir tüm disk taraması değildir.

Yeni pencereler mevcut koyu/açık tema renklerini ve buton sistemini kullanır. Eski sürüm kapalıyken `releases/v1.1.5/VideoDownloaderPro_Setup.exe` ile yükselt. Test için kısa ve indirmeye yetkili olduğun içerikleri kullan.

## Yerel kayıt

Kuyruk ve geçmiş `%APPDATA%/YoutubePro/downloads.sqlite3` içinde tutulur. Medyanın kendisi seçilen klasörde kalır. Kuyruk/geçmiş sunucuya gönderilmez. Kuyruk geçişlerinde ve aktif indirme sırasında yaklaşık iki saniyede bir kayıt alınır; ani güç kesilmesinde son ilerleme sayacı geriden gelebilir. `.part` dosyası yine kaynak desteğine göre kullanılır. Bozuk kayıt okunduğunda üzerine boş kuyruk yazmak yerine hata gösterilir. Aynı veri klasörüyle eşzamanlı birden fazla uygulama açmak desteklenen test senaryosu değildir.

## Geliştirici doğrulaması

Hedefli testler (eski dış ağ/çerez kullanan betikler genel keşfe dahil edilmez):

```powershell
python -m unittest discover -s tests -p test_library_features.py -v
python -m unittest discover -s tests -p test_scheduler.py -v
python -m unittest discover -s tests -p test_audit.py -v
python -m unittest discover -s tests -p test_app_updates.py -v
python -m unittest discover -s tests -p test_components.py -v
python -m unittest discover -s tests -p test_local_download.py -v
python -m unittest discover -s tests -p test_bandwidth_local.py -v
node tests/test_library_ui.cjs
node tests/test_download_ui.cjs
node tests/test_update_ui.cjs
node tests/test_component_ui.cjs
```

Sonuçlar: 25 yeni kalıcılık/yeniden deneme/playlist/geçmiş kontrolü; 30 scheduler, 15 audit, 26 uygulama güncelleme ve 20 bileşen kontrolü geçti. Node akış kontrolleri geçti. Gerçek localhost MP4 ve MP3 iki kez indirildi, mevcut çıktı korunup `(1)` oluşturuldu, SQLite geçmişi ve yeniden açılışta tamamlanan kayıtlar doğrulandı; çıktılar FFprobe ile kontrol edildi. Üç gerçek HTTP/HLS/hız sınırı ve duraklat/devam testi geçti. Bunlar dış platformların tümünde indirme veya aynı hız garantisi vermez.

Görsel test için `python tests/preview_library.py` yalnız localhost:5056 üzerinde geçici örnek veriyle çalışır; kişisel kuyruk/geçmişe dokunmaz. Gerçek medya indirme testleri localhost erişimi ve `%APPDATA%/YoutubePro/bin` altında FFmpeg/FFprobe gerektirir.
