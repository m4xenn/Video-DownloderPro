# v1.1.4 — Ortak kuyruk ve otomatik indirme

## Kullanım

Ayarlar → İndirme yönetimi varsayılan olarak **Otomatik (önerilen)**. Otomatik mod 2 indirmeyle başlar ve 1–4 aralığında çalışır. **Gelişmiş ayarlar** içindeki 1–10 manuel sayı yalnız manuel mod seçilince etkinleşir. Ayarların uygulanması için Kaydet'e bas.

**Toplam indirme hızı sınırı** artık Mbps biriminde ve bütün medya kuyruğu tarafından paylaşılır. Örneğin 8 Mbps yaklaşık 1 MB/s; 0 sınırsızdır. Önceki Kbps ayarı okunurken Mbps'ye çevrilir. Hız sınırı canlı olarak değiştirilebilir. Uygulama güncellemesi, bileşen indirmeleri ve ayrı önizleme istekleri bu medya bütçesine dahil değildir. Bu ayar bilgisayarın tüm internet trafiğini sınırlamaz.

Yeni ayarlar `%APPDATA%/YoutubePro/settings.json` içine atomik kaydedilir; kurulum klasöründeki eski settings.json dosyası yeni kayıt yoksa okunur. Program Files içine yazma gereği kaldırılmıştır. Uygulama açıldığında kayıtlı ayarlar ekrana geri yüklenir.

## Nasıl optimize ediliyor?

- Tüm /download istekleri aynı uygulama içi yönetici ve işçi havuzuna gönderilir; yeni istek kendi bağımsız havuzunu açmaz.
- Ölçüm, native yt-dlp HTTP yanıtlarından okunan toplam baytlarla son 10 saniye üzerinden yapılır. Başlangıç/az iş bulunan dönemler hız karşılaştırmasına alınmaz.
- Yeterince iş varsa, işlemci yükü düşükse ve hız sınırına yaklaşılmamışsa 10 saniyelik örnekten sonra bir ek iş denenir. Sonraki örnekte toplam hız en az %8 artmazsa önceki sayıya dönülür. Denemeler arasında 30 saniye beklenir.
- İşlemci kullanımı %80 veya üzerindeyse, hata oluşursa ya da dönüştürme yükü varsa daha az yeni iş başlatılır. Bu algoritma her bağlantıda mutlak en hızlı sayıyı garanti etmez; amaç ölçerek, sınırlı denemelerle kararlı çalışmaktır.
- Çalışan indirmeler sayı azaldı diye öldürülmez; yeni iş başlatılması bekletilir. Bu nedenle bir azaltma sonrasında aktif sayı kısa süreliğine hedefin üstünde görünebilir.
- Aynı anda en fazla bir postprocessor/FFmpeg dönüşüm zinciri çalışır. Dönüştürme varken yeni indirme başlatılmaz; mevcut indirmeler devam eder. İç içe yt-dlp postprocessor bildirimleri kilitlenmeden ele alınır.
- Video başına native parça paralelliği 3 olarak sınırlandı. Parçalar da aynı toplam hız bütçesini kullanır.

## Kuyruk ve devam ettirme

Duraklatma mevcut öğeye işaret koyar ve ağ okuması/progress callback'i üzerinden işçiyi durdurur. İşçi gerçekten bitmeden yeniden başlatılmaz. Devam et/tekrar dene aynı kuyruk kaydını, formatı, kaliteyi, altyazı seçimini, hedef klasörü ve ortak hız bütçesini kullanır. Ayrı /download isteğiyle global kuyruk sıfırlanmaz.

Sunucu byte-range/resume destekliyorsa yt-dlp `.part` dosyasını kullanarak devam edebilir. Desteklemeyen kaynakta baştan indirme gerekebilir. FFmpeg dönüştürmesi sırasında duraklatma düğmesi kapatılır. 1.1.5 ile kuyruk uygulama yeniden açıldığında duraklatılmış olarak geri yüklenir. Yeni kalıcı kuyruk, geçmiş, playlist seçimi ve tekrarlanan indirme uyarısı için `FEATURE_ACCEPTANCE_TESTS.md` dosyasına bak.

Hatalı öğeler başarı sayılmaz, hata metni saklanır ve tekrar denenebilir. Yalnız tüm görünür işler başarıyla tamamlandığında başarı bildirimi gönderilir. Tamamlanan/hatalı satırlar otomatik silinmez. Çalışan öğeyi kaldırmak için önce duraklatmak gerekir.

Birden fazla playlist verilirse 1.1.5 ile önce video seçim ekranı açılır; onaylananlar ortak kuyruğa eklenir. Geçersiz Windows klasör karakterleri temizlenir. Aynı aktif URL'nin eşzamanlı iki satır oluşturup durum/dosya çakışmasına yol açması engellenir. Ayrıca yeni geçmişte aynı format/kalite/altyazı ile indirilmiş ve hâlâ mevcut dosyalar varsa kullanıcıya atlama veya yeniden indirme seçeneği sunulur. Çıktı adlarına medya kimliği eklenerek aynı başlıklı farklı videoların çakışma riski azaltıldı.

## Hız sınırının kapsamı

Tek bir cancellable token budget, native HTTP/HTTPS, HLS ve DASH indirmelerinde tüm yanıt okuyucuları tarafından paylaşılır. Her videoya aynı bağımsız yt-dlp ratelimit kopyalanmaz. Çok kısa aralıklarda tamponlama ve TCP/TLS ek yükü yüzünden ağ sayacıyla birebir eşleşme beklenmemeli; sınır uygulamanın okuduğu medya baytlarına uygulanır.

Harici FFmpeg ağ indiricisi gerektiren protokollerde bu bütçe uygulanamayacağından pozitif limit varken iş açık hata mesajıyla durdurulur. Böyle bir harici yayın zaten sınırsız çalışıyorsa, yayının ortasında desteklenmeyen bir limit kaydetme isteği reddedilir. Genel uygulama/bileşen kurulumu, ortak kuyruk aktifken engellenir.

## Doğrulama

- 30 yeni scheduler/adaptive/settings kontrolü: ortak sınır, birden fazla istek, hata, sıra bekleyen öğeyi duraklatma, seçenekleri koruyarak devam, tekrar deneme, çoklu playlist, CPU/limit tepkileri ve dönüşüm kilidi.
- 6 yeni UI akış kontrolü: ayar geri yükleme, otomatik/manüel alanlar, doğru Mbps yükü, kaydetme hatası, yalnız URL ile devam ve toplam hız özeti.
- Önceki 15 audit, 26 uygulama güncelleyici ve 20 bileşen Python kontrolü geçti. Önceki 5+6 UI kontrolü geçti.
- Gerçek localhost MP4 ve MP3 dosyaları üretildi, indirildi ve FFprobe ile doğrulandı.
- Gerçek iki HTTP aktarımı: toplam 400000 bayt, ortak 100000 bayt/s sınırıyla yaklaşık 4,5 saniyede tamamlandı. Bağımsız iki limit gibi yaklaşık 2 saniyede tamamlanmadı.
- Gerçek HTTP duraklat/devam et testi: `.part` dosyası, aynı öğe kimliği, hız bütçesi ve seçenekler korundu; dosya içeriği doğrulandı.
- FFmpeg ile üretilen 5 parçalı HLS listesi, 3 paralel parça ve ortak 100000 bayt/s sınırıyla indirildi; MP4 işlendi. Bir koşuda 455336 medya baytı toplam işlem dahil yaklaşık 6,4 saniye sürdü.
- Tarayıcıda otomatik mod ve gelişmiş alanın otomatikte kapalı/manüelde açık olması doğrulandı. Kullanıcının gerçek ayarları bu görsel kontrolde kaydedilip değiştirilmedi.

Komutlar:

```powershell
python -m unittest discover -s tests -p test_scheduler.py -v
node tests/test_download_ui.cjs
python -m unittest discover -s tests -p test_local_download.py -v
python -m unittest discover -s tests -p test_bandwidth_local.py -v
```

Son iki komut localhost erişimi ve `%APPDATA%/YoutubePro/bin` altında FFmpeg/FFprobe gerektirir. Eski test_mp4/test_kick/test_ytdlp betikleri import sırasında dış ağa/çerezlere eriştiği için genel pytest keşfi yerine hedefli komutları kullan.

Bu testler dış platformlarda evrensel hız artışı veya tüm site/protokollerde tam uyumluluk garantisi değildir. İlk kabul testini izinli kısa içeriklerden oluşan 4–6 öğelik kuyrukla yap: otomatik mod, 8 Mbps sınır, duraklat/devam et, hatalı URL'yi tekrar deneme ve bir küçük playlist.
