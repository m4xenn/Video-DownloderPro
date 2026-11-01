# Video Downloader Pro — İlk inceleme ve test kılavuzu

Tarih: 16 Ekim 2026

v1.1.4 sonrası not: aşağıdaki ilk taramanın 15 audit kontrolünün tamamı artık geçiyor. Yeni kuyruk, hız bütçesi ve doğrulamalar AUTOMATIC_DOWNLOADS.md; güncelleyici ve yayın adımları RELEASE_PUBLISHING.md içinde açıklanıyor. Aşağıdaki bulgular ilk taramanın tarihsel kaydıdır.

## Sonuç

Uygulama Python + Flask + pywebview kullanıyor. Medya motoru Python `yt_dlp` modülü, dönüştürücü FFmpeg. Bu incelemede uygulama davranışı değiştirilmedi; tekrarlanabilir testler ve bu kılavuz eklendi.

- `tests/test_audit.py`: 15 kontrol; **10 geçti, 5 başarısız**. Başarısız kontroller mevcut kusurları gösteriyor.
- `tests/test_local_download.py`: 1 test içinde gerçek MP4 indirme ve MP3 dönüşümü; **ikisi de geçti**. FFmpeg ile üretilen iki saniyelik örnek localhost üzerinden indirildi. FFprobe ile süre ve ses/görüntü akışları doğrulandı. Test dosyaları işlem sonunda temizlendi.
- Ana sayfa Flask test istemcisiyle 200 döndü. Klasör/kuyruk eksikliği kontrolleri, ilerleme yüzdesi, duraklatma kancası, format seçenekleri ve izole ayar kaydı geçti.
- `python -m pip check`: kurulu paket bağımlılıklarında sorun bildirmedi.
- Mevcut ortam: Python 3.12.6, Flask 3.1.2, yt-dlp 2026.8.19, pywebview 6.2.1. Bunlar requirements.txt içindeki sabit sürümlerden farklı; temiz kurulum sonucu ayrıca test edilmeli.

Gerçek dış platform indirmeleri, oynatma listesi, ayrı ses/video birleştirme, kapak, altyazı, masaüstü pencere etkileşimleri, bildirimler ve paketlenmiş EXE/kurulum bu turda uçtan uca doğrulanmadı. Yerel MP4 testi kalite seçimini veya platform erişimini doğrulamaz.

## Öncelikli bulgular

| Öncelik | Bulgu | Kanıt / etkisi |
|---|---|---|
| Yüksek | İndirme başarısız olsa da toplu başarı durumu veriliyor. | queue_manager.py, işçi False döndüğünde ve exception attığında iki ayrı testte `finished_all` üretti. Future sonuçları okunmuyor; başarı bildirimi koşulsuz. Arayüz 3 saniye sonra kuyruğu temizleyebilir. |
| Yüksek | Duraklat/devam et tüm kuyruk durumunu bozabilir. | Kod incelemesi: resumeItem yalnız tek URL ile yeniden /download çağırıyor; run_download global items listesini yeniden oluşturuyor. Devam isteğinde hız, altyazı ve playlist seçenekleri korunmuyor; polling yeniden başlatılmıyor. Kullanıcı arayüzünde ayrıca test edilmeli. |
| Yüksek | Güncelleme indirilen Python motorunu değiştirmiyor. | updater_service.py yt-dlp.exe indiriyor; gerçek indirme `from yt_dlp import YoutubeDL` kullanıyor. app.py EXE'nin klasörünü sys.path'e ekliyor; EXE bir Python modülü güncellemesi değil. Bu ortamda import edilen sürüm pip kurulumundan geliyor. |
| Orta | API girdi doğrulaması eksik. | urls bir liste yerine string gönderilince /download 200 döndü. /open-folder boş JSON ile 500 üretti. Format, kalite ve eşzamanlılık sınırları da sunucuda doğrulanmalı. |
| Orta | Arayüzde tamamlanma sonrası tanımsız fonksiyon var. | index.html `fetchHistory()` çağırıyor; kaynakta tanımı yok. Tarayıcı konsolunda ReferenceError beklenir. |
| Orta | Otomatik sıkıştırma bağlantısı eksik. | Arayüz /compress çağrısı içeriyor ama backend'de rota yok. Çağrı için item.id gerekiyor; indirme öğeleri id üretmiyor. auto_compress ayarı kaydediliyor fakat uygulama kodunda uygulanmıyor. |
| Orta | Platform kapsamı daraltılıyor. | queue_manager.py tanınmış kısa host listesindeki olmayan URL'leri önce HTML extractor'a gönderiyor. Extractor sonuç bulamazsa yt-dlp'ye deneme şansı vermeden tüm işlem bitiyor. Kick/Twitch gibi servisler bu akışta ayrıca kontrol edilmeli. |
| Orta | Playlist açıkken yalnız ilk kuyruk URL'si çözümleniyor. | run_download `urls[0]` kullanıyor; diğer girilen bağlantılar işlenmiyor. Playlist klasör adı Windows'un yasak karakterlerine karşı tam temizlenmiyor. |
| Düşük | Ürün adı tutarsız. | Kullanıcının belirttiği Video Downloader Pro yerine HTML'de Studio Downloader Pro, başlıklarda Studio Downloader, masaüstü penceresinde YoutubePro Downloader var. Ürün adı testi başarısız. |

Ek notlar: Ayarlar arayüzü kayıtları /get-settings üzerinden geri yüklemiyor. requirements.txt `packaging` bağımlılığını açıkça belirtmiyor; güncelleme sürüm karşılaştırması bunu kullanıyor. MP4 dönüştürücü seçeneği tek başına H.264 garantisi vermiyor; README'deki editör uyumluluğu iddiası codec testi gerektiriyor. Bu klasörde Git deposu bulunmadı. dist altında birden fazla eski isimli çıktı mevcut; kaynak kod testi için aşağıdaki başlatma komutunu kullan.

## Sen nasıl test edeceksin?

PowerShell'i proje klasöründe aç. Mevcut makinede bağımlılıklar kurulu olduğu için ilk deneme:

```powershell
python src/main.py
```

Bu komut masaüstü penceresini açar. Hataları görmek için PowerShell'i açık tut. Tarayıcı konsoluyla hata ayıklamak için alternatif:

```powershell
python -m flask --app src/app.py run --host 127.0.0.1 --port 5000
```

Ardından http://127.0.0.1:5000 adresini aç. F12 ile Console ve Network sekmelerini izle. Durdurmak için PowerShell'de Ctrl+C kullan. Tarayıcı modunda masaüstüne özgü tam ekran/bildirim davranışını ayrıca masaüstü modunda dene.

### Tekrarlanabilir otomatik kontroller

```powershell
python -m unittest discover -s tests -p test_audit.py -v
python -m unittest discover -s tests -p test_local_download.py -v
```

İlk komutun mevcut sürümde 5 hata vermesi bekleniyor; düzeltmeler sonrası bu sayının sıfıra inmesi hedef. İkinci komut %APPDATA%/YoutubePro/bin altında ffmpeg.exe ve ffprobe.exe gerektirir; yoksa atlanır. Localhost erişiminin açık olması gerekir. Testler gerçek ayar dosyasını değiştirmez; kullanıcı çerezlerini kullanmaz.

**Genel `pytest` komutunu şimdilik kullanma:** mevcut test_mp4.py ve test_ytdlp.py import sırasında internete bağlanıyor; test_kick.py Edge çerezlerini okumayı deniyor. Bunlar assertion içeren, izole bir test takımı değil.

### Elle deneme sırası

Kendine ait veya indirme iznin olan kısa içerikleri ve boş bir `VDP-Test` klasörünü kullan.

| Sıra | İşlem | Beklenen sonuç |
|---|---|---|
| 1 | Klasör seçmeden ve boş kuyrukla başlatmayı dene. | Anlaşılır hata; uygulama yanıt vermeye devam etmeli. |
| 2 | Klasör seç, kısa bir video ekle, MP4/720p indir. | Dosya açılmalı; hem ses hem görüntü olmalı. Kaynakta varsa çözünürlük en fazla 720p olmalı. |
| 3 | Aynı içeriği MP3, M4A, WAV ve Opus olarak ayrı ayrı dene. | Her dosya doğru uzantıyla oluşmalı ve oynatılmalı. MP3/M4A kapakları ayrıca kontrol edilmeli. |
| 4 | Aynı videoyu tekrar indir. | Önceki dosya korunmalı, yeni dosya numaralı isim almalı. |
| 5 | İki farklı bağlantıyı kuyruğa ekle. | İkisi de Toplu_Indirmeler klasörüne inmeli. Birini hatalı bağlantıyla değiştirerek hata görünürlüğünü dene. |
| 6 | En fazla 2–3 öğelik playlist ile playlist seçeneğini aç. | Öğelerin tümü listelenmeli ve playlist klasörüne inmeli. |
| 7 | Daha uzun indirmede duraklat/devam et. | Durum, diğer kuyruk öğeleri ve ayarlar korunmalı. Bu sürümde bilinen riskli akış. |
| 8 | İndirme sırasında interneti kes, sonra geri getir. | Hata görünür olmalı; yanlış başarı veya kaybolan kuyruk olmamalı. |
| 9 | Hız sınırı ve eşzamanlı indirme sayısını değiştir. | Sınırlar uygulanmalı. Kapat/aç sonrasında arayüzde kayıtlı değerleri kontrol et. |
| 10 | Dil, açık/koyu tema, pencere boyutu ve tam ekranı dene. | Taşma, görünmeyen buton ve Console hatası olmamalı. |
| 11 | Altyazılı bir kaynakla altyazı seçeneğini dene. | Çıkan dosyada seçilebilir altyazı akışı bulunmalı. |

Her hata için şu bilgileri kaydet:

```text
Adım:
Bağlantı / platform:
Format ve kalite:
Playlist / altyazı / hız / eşzamanlılık ayarları:
Beklenen:
Gerçekte olan:
PowerShell veya Console hata metni:
Tekrar denenince oluyor mu?:
```

Önerilen düzeltme sırası: hata/başarı raporlama → kuyruk ve duraklat/devam et → motor güncelleme → API doğrulaması → eksik arayüz bağlantıları → ürün adı ve dokümantasyon. Yeni özelliklerden önce bu temel akışları kararlı hale getirmek uygun olur.
