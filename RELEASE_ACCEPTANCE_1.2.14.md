# 1.2.14 yayın öncesi doğrulama

Yerel yayın öncesi kontroller tamamlandı. Sürüm: 1.2.14. Kesit indirme kapsam dışıdır.

## Bulunan ve düzeltilen hata

1.2.13 paketinin gerçek indirme testinde, aynı klasöre MP4 indirdikten sonra MP3
dönüşümü yapmanın tamamlanmış MP4'ü silebildiği doğrulandı. yt-dlp, ses dönüşümü
için aynı adlı MP4'ü geçici girdi olarak yeniden kullanıyordu. Önceki dosya adı
koruması yalnız nihai uzantıyı kontrol ettiği için bu çakışmayı önlemiyordu.

Yeni indirme artık bütün uzantılar ve kısmi dosyalar için boş bir temel ad seçer.
İşlem boyunca tutulan rezervasyon, eşzamanlı işlerin aynı adı seçmesini de önler.
Devam ettirilen iş kendi dosya adını korur; başka aktif işin kullandığı ada yazmaz.
Rezervasyon başarı, hata ve duraklatma sonrasında bırakılır.

## Tamamlanan kontroller

- 285 Python kontrolü geçti. Yeni test önce eski davranışta MP4'ün silindiğini
  yakaladı; düzeltmeden sonra MP4, MP3, M4A, WAV ve Opus dosyalarının bütünlüğü
  her yeni dönüşümden sonra korundu.
- 133 JavaScript arayüz kontrolü geçti.
- Gerçek WebView2 sentetik testinin 18 kontrolü geçti: iç içe oynatıcı, HTML5,
  JW Player/Video.js, HLS/DASH, ağdan kaynak bulma, kalite, sesli indirme ve oturum
  devri/temizliği dahil.
- Dört dış bağlantının kaynak/metadata ve en fazla 16 KiB medya örneği kontrolü
  başarılı oldu. Bunlar tam video indirme testi değildir.
- Paketlenmiş 1.2.14 EXE ayrı APPDATA/LOCALAPPDATA ile çalıştırıldı. Paket içindeki
  dokuz statik giriş dosyası başarıyla sunuldu.
- Dört dış bağlantı ayrıca paketlenmiş EXE'nin gerçek /get-info girişinden
  başarıyla okundu; beklenen kalite seçenekleri ve süre bilgileri alındı.
- EXE'nin gerçek API akışında MP4, MP3, M4A, WAV ve Opus çıktıları FFprobe ile
  doğrulandı; tekrar indirmede eski dosya korunup ayrı çıktı üretildi.
- Gerçek duraklatma, sürecin kapanması, kuyruğun/ayarların geri yüklenmesi ve
  devam ettirme geçti.
- Gerçek HTTP 404 hata olarak kaldı; bütün işler başarılı gösterilmedi. İlgili
  tanılama raporunda ham URL, yerel dosya yolu ve oturum başlıkları bulunmadı.
- Python bağımlılık kontrolü ve kaynak derleme kontrolleri geçti.
- 1.2.14 üretim EXE'si, kurulum dosyası, SHA256SUMS.txt ve release-info.json hazır.

## Gerçek yükseltme durumu

- Mevcut 1.2.8 kullanıcı verileri build/real-upgrade-1.2.13/backup altında özel
  olarak yedeklendi. Üç dosyanın toplamı 73885 bayt; kopyalar SHA-256 ile doğrulandı.
- Kaynak testlerinin eklediği tanılama kayıtları ayrı kopyaya alındı ve kişisel
  tanılama dosyası yedekten geri getirildi. Sonraki testler ayrı veri klasörlerinde
  çalıştırıldı. Ayarlar ve indirme geçmişi yedekle eşleşti.
- Gerçek 1.2.13 kurulum girişimi tamamlanmış olarak doğrulanamadı; Windows kaydı
  ve kurulu sürüm dosyası 1.2.8 gösterdi. 1.2.13 yayımlanmayacak.
- Eski 1.2.13 sihirbazı kapatıldı. Doğrulanmış 1.2.14 üretim paketi, normal Windows
  yönetici onayıyla otomatik kurulum modunda başarıyla kuruldu. Yeniden başlatma
  gerekmedi. Windows kaydı ve paket içi sürüm dosyası 1.2.14 gösteriyor.
- Gerçek 1.2.8 → 1.2.14 yükseltmesinde 1879 kurulu dosyanın tamamı dağıtımla SHA-256
  düzeyinde eşleşti. İlk açılıştan önce üç kişisel veri dosyası da orijinal yedekle
  birebir aynıydı.
- Kurulu EXE, ayrı test profiliyle beş çıktı formatı, dosya koruma, tekrar indirme,
  süreç yeniden başlatma sonrası devam ve hata raporu testlerinin tamamını geçti.
- Masaüstü ve Başlat menüsü kısayollarının doğru EXE'ye gittiği doğrulandı.
  Masaüstü kısayoluyla gerçek kişisel profil açıldı; bekleyen işler kendiliğinden
  başlamadı. Ana ekran ve Ayarlar'da v1.2.14 görsel olarak doğrulandı.
- Manuel güncelleme kontrolü canlı GitHub yanıtıyla sınandı: kullanılan sürüm
  v1.2.14, son yayımlanan sürüm v1.2.8; yanlış güncelleme önerilmedi.
- Gerçek uygulama normal yoldan kapatıldı. Kapanış sonrasında kişisel ayarlar,
  geçmiş, kuyruk taslakları ve devam ettirilebilir işler korundu. SQLite
  integrity_check sonucu ok. Yedekler özel build klasöründe tutuluyor.
- Sonuçlar build/real-upgrade-1.2.13/production-result.json ve
  build/real-upgrade-1.2.14/ altındaki kabul raporlarında kayıtlıdır.

## Sınırlar

Temiz Windows sanal ortamı kullanılmadı. Gerçek GitHub üzerinden iki sürümlü
indir-kur döngüsü henüz yapılmadı; yayın sonrası asset digest ve sürüm kontrolü
ayrıca doğrulanmalı. Kişisel veri yedekleri ve build altındaki test kurulumları
yayımlanacak dosyalara dahil edilmemeli.
