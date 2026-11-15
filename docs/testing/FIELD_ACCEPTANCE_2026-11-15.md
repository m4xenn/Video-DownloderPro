# Saha ve saldırgan senaryo kabulü — 15 Kasım 2026

**Yayımlandı:** Aynı doğrulanmış dosya 15 Kasım 2026'da kararlı/en güncel 1.4.7
olarak açıldı. [Yayın doğrulaması](../releases/PUBLISHED_1.4.7.md), aşağıdaki
hazırlık zamanına ait yayımlanmadı ifadelerinin yerini alır.

## Sonuç güncellemesi — 15 Kasım 2026, 19:21 (İstanbul)

**Sekiz saatlik test GEÇTİ.** Kayıt süresi 28.800,107 saniye; tüm ses/görüntünün
sıkı decode'u başarılı, kayıt hata kuyruğu boş. Kararlı dönem RSS farkı
−17.866.752 bayt; bellek büyümesi kontrolü geçti. Çıktı 1.269.201.598 bayt.
Yedi motor hash'i test sonunda ve sonuç işlenirken kaynakla eşleşti.

630 Python/28 JavaScript testi, gerçek 50 dosyalık kuyruk, 40 gerçek frozen HTTP
saldırgan isteği ve izole kurulum/yükseltme de geçti. `acceptance.json` artık
`passed` / `ready_for_publication:true` / `published:false` durumundadır.
Tanımlanan kabul kapıları tamamlandı; **yayın yapılmadı**. Aşağıdaki çalışıyor,
bekliyor ve yayın kapısı açık ifadeleri test sırasında yazılmış tarihsel kayıttır;
bu sonuç güncellemesi onların yerini alır. Kapsam/sınırlar geçerliliğini korur.

**Durum: sürüm kabulü açık. Sekiz saatlik test henüz bitmedi. Yayımlanmadı.**
Son yerel aday 1.4.7; bu belge önceki adayların hazır olma durumunu bu kapsam
için geçersiz kılar. Sekiz saatlik sonuç `passed` olmadan nihai kararlılık kabulü
tamamlandı denmemeli. Kullanıcının programı/profili ve yayındaki 1.4.3 değiştirilmedi.

## Uzun kayıt — devam ediyor

- `scripts/check_recording_endurance.py --minutes 480 --label release-acceptance-eight-hour`
- Çalışan exec oturumu: **48975**.
- Canlı durum: `build/stability/release-acceptance-eight-hour/result.json`.
- Yerel, sürekli H264/AAC kaynağı; gerçek duvar saatiyle sekiz saat kayıt,
  15 saniyede RSS/handle/thread ölçümü, ardından süre ve tüm ses/görüntü decode'u.
- Üretim ağı gevşetilmedi; loopback istisnaları yalnız bu test sürecinin kaynağına ait.
- Testin yedi motor dosyası test süresince değiştirilmemeli. Motor, ana kuyruk
  yöneticisinden ayrı sınanıyor; uygulama entegrasyonu aşağıdaki testlerde sınandı.
- Henüz sekiz saatlik başarı, son bellek sonucu veya tam decode sonucu yok.

## Gerçek kuyruk — geçti

`scripts/check_queue_acceptance.py`, ayrı profil/veritabanı ve yerel kaynakla
50 gerçek video indirdi. Üç eşzamanlı iş, aynı dosya adları için 50 ayrı çıktı,
50 dosyanın video/ses/süre doğrulaması ve yönetici yeniden açılışından sonra 50
geçmiş kaydı geçti. Süre yaklaşık 29,9 saniye. Kanıt:
`build/field-acceptance-2026-11-15/queue/result.json`.

## Dışarıdan saldırgan yaklaşımı

`tests/test_adversarial_acceptance.py`:

- Bütün parametresiz API yollarında yabancı Origin reddi; ayrı kritik işlem matrisi.
- Sahte Host/DNS-rebinding adı, sayısal loopback/IPv6 alias'ları, metadata IP'si,
  dosya protokolü ve URL içine gömülü kimlik bilgisi reddi.
- Content-Length olmayan büyük JSON: mevcut 2 MiB okuma sınırı doğrulandı. Hatalı
  kesilmiş JSON'un 400 veya 413 ile reddi geçerlidir; bu koruma zaten çalışıyordu,
  yeni açık düzeltmesi olarak sayılmadı.
- Yalnız kendi test eklenti sunucusuna sahte token, geçerli token+yabancı Origin,
  aşırı boyutlu içerik denemeleri; reddedildiler. Gerçek kullanıcı token'ı kullanılmadı.

Bulunan gerçek doğrulama hatası: `public_link` içindeki `parsed.port or default`
ifadesi açıkça yazılmış `:0` portunu varsayılan porta çeviriyordu. Artık yalnız
port belirtilmemişse varsayılana dönülür; sıfır reddedilir. Bu bir doğrulama
düzeltmesidir; uzaktan kod çalıştırma veya özel ağa erişim açığı diye sunulmuyor.

İlk tam koşuda Windows'ta reddedilen eklenti isteği için bir bağlantı sıfırlaması
görüldü. Sunucu gövdeyi okumadan bağlantıyı kapattığında bu sonuç mümkün.
Regresyon testi 403 veya bağlantı reddini kabul ederken **işlem yan etkisi olmamasını
ve ardından geçerli isteğin çalışmasını** da kontrol edecek şekilde düzeltildi.
Koruma gevşetilmedi; kabul edilen istek veya sunucu çökmesi başarılı sayılmıyor.

Önceki testler ayrıca 503/429, reset, eksik/kısa parça, kaynak yenileme, gerçek
graceful/abrupt restart ve Range ile aynı tam medya çıktısına devamı kapsar.
Son tam regresyon **630 Python testiyle geçti**; sıfır hata/başarısızlık/atlama.
28 JavaScript testi de geçti. Kanıtlar `regression.json/.log` ve `javascript.log`.
Gerçek frozen EXE'nin HTTP sunucusunda ayrıca 40 yabancı Origin/Host isteği
reddedildi; kuyruk değişmedi ve sonrasında normal istek çalıştı:
`frozen-adversarial/result.json`. Son bağımlılık taramasında bilinen açık yok.
Bu kısa kontroller uzun kayıt sonucunun yerine geçmez.

## Paket ve yayın kapısı

- Paket: `build/field-acceptance-package/YoutubePro`.
- Aday: `build/field-acceptance-2026-11-15/candidate/VideoDownloaderPro_Setup.exe`.
- Sürüm 1.4.7; 45.658.020 bayt.
- SHA-256: `fb3693254ccfa4b89aca9fa3a91d020ede32c7204205a849faef130e348fe8c6`.
- Gerçek beş biçim indirme, Defender, yabancı Origin/özel IP ve yeniden açılış
  kontrolleri `native-downloads/result.json` içinde; kurulum kanıtı `installer/`.
- Kaynak/giriş/arayüz karşılaştırması, izole temiz kurulum, 1.4.3 → 1.4.7
  yükseltme, aynı sürüm/sürüm düşürme reddi ve profili koruyan kaldırma geçti.
- `build/field-acceptance-2026-11-15/acceptance.json` yayın kapısını
  `pending_eight_hour` / `ready_for_publication:false` olarak kaydeder.
- **Adayın hazırlanmış olması sekiz saatlik kabulün tamamlandığı anlamına gelmez.**

Kapsam: kullanıcıya ait uygulama, ayrı profiller ve sahip olunan test sunucuları.
Üçüncü taraf hizmetlerine saldırı yapılmadı. Yerel kötü niyetli yönetici/süreçlere
karşı tam koruma, temiz Windows VM/UAC, bütün siteler/codec'ler ve gerçek internet
canlı yayınında sekiz saatlik saha koşusu iddia edilmiyor. Dispozabl WebView için
önceki DNS/izin sınırları ve medya süreçlerinde tam okuma izolasyonu olmaması
geçerlidir. Bilinen bağımlılık taraması ve statik analiz tam penetrasyon testi
veya hatasızlık garantisi değildir.
