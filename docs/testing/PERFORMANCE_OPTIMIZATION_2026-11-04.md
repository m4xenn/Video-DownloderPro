# Performans, optimizasyon ve kabul — 4 Kasım 2026

Tamamlandı; **yayımlanmadı**. Sürüm 1.4.3 adayıdır.

## Ölçüm

| Ölçüt | Önce | Sonra | Süre azalması |
|---|---:|---:|---:|
| Paketli uygulama / HTTP arayüzü hazır | 1.341 sn | 1.270 sn | +5.3% |
| İlk herkese açık link incelemesi | 0.815 sn | 0.831 sn | -1.9% |
| Yerel MP4 toplam işlem | 1.808 sn | 1.597 sn | +11.7% |
| Video önizleme hazırlığı | 0.388 sn | 0.236 sn | +39.2% |
| Yerel MP3 toplam işlem | 1.716 sn | 1.681 sn | +2.1% |

Her ölçüm beş tekrarlı medyandır. Açılışta eski/yeni gerçek EXE dönüşümlü
çalıştırıldı; denetim aralığı 30 ms, her iki profil yalıtılmıştır. HTTP hazır
olma süresi ölçülür; ilk piksel/etkileşim ölçümü veya soğuk Windows açılışı
değildir. Yeni EXE'nin ilk örneği 2,18 saniyeydi; bu örnek medyana dahildir.
İlk link internet koşullarından etkilenir; 0,81/0,83 saniye farkı anlamlı bir
gerileme/artış olarak yorumlanmamalıdır.

Yerel pipeline testinde aynı 30 saniyelik 720p MP4 dosyası, aynı yorumlayıcı,
aynı araçlar ve eski/yeni paketlerden alınan beş ilgili modül kullanıldı.
Paket arşivleri güvenilir yerel derlemelerdir; çalışma dosyaları geri alınmadı.
Bu kontrollü sonuç indirme + işleme + güvenlik + önizleme toplamıdır; internet
bant genişliğinde %12 artış iddiası değildir. MP3 farkı küçüktür; hız artışı
vaat edilmez. İlk üç tekrarlı keşif ve eşzamanlı testlerden etkilenmiş ölçümler
saklandı; nihai karşılaştırma bunlardan seçilmedi.

Ham raporlar: `build/performance/controlled-before`, `controlled-after`,
`startup-final`; önceki keşifler `baseline`, `optimized-source`,
`optimized-packaged`, `startup-comparison`, `startup-fine`.

## Değişiklikler

- Kaynak çözümleme desteği ilk pencere yüklemesini bloke etmez; WebView
  hazırlanırken arka planda içe aktarılır. Bu hazırlık ağ isteği yapmaz.
  Sadece ilk kullanıma ertelemenin ilk linkte 0,13 saniye ek gecikme yaptığı
  ölçüldüğünden son paket arka plan hazırlığını da içerir.
- Doğrulamada zaten öğrenilen gerçek süre önizlemeye aktarılır. Süresi
  bilinmeyen doğrudan video testinde gereksiz bir FFprobe çalıştırması kalktı
  (ısınmış video işinde altı yerine beş medya süreci).
- Canlı kaydın son dosyası aynı iş içinde yeniden kontrol edilirken tam
  ayrıştırma/decode yalnızca dosya değişmemiş ve Windows okuma tutamacı yeni
  veri yazmalarını engelliyorsa tekrar kullanılabilir. Rename desteklenir;
  dosya/politika değişimi veya kilit alınamaması tam doğrulamaya döner.
  Başarısız sonuç saklanmaz; kilitler iş bitiminde kapanır. Merge sonrası
  değiştirilecek büyük ara dosyalar bu yeniden kullanımın dışındadır.
- Antivirüs taraması, gerçek kapsayıcı/akış/süre/son kare kontrolleri ve güvenli
  kaydetme korunur. Ağ/parça paralelliği artırılmaz; kaynak kısıtları aşılmaz.

## Kararlılık ve güvenlik

- **579 Python testi**, sıfır hata/başarısızlık/atlama; **27 JavaScript test dosyası** geçti.
- Gerçek Windows EXE'de MP4, MP3, M4A, WAV, Opus indirme ve beş Defender
  taraması geçti. Dil/bildirim/geçmiş yeniden başlatmada korundu; özel ağ
  bağlantısı ve yabancı Origin reddi çalışıyor. 25 modül, beş arayüz dosyası
  ve ana giriş kodu kaynakla eşleşiyor.
- Gerçek zamanlı HLS: **60.00 saniye** sesli/görüntülü kayıt,
  ikinci tam doğrulama yerine tek doğrulama; 15–55 saniye aralığında ana süreç
  RSS değişimi **-0.68 MiB**. En yüksek medya
  süreçleri RSS toplamı **224.3 MiB**. Bu bir dakikalık
  örnek, 24 saatlik kayıt/bellek sızıntısı sertifikası değildir.
- Geniş pakette geçmişten canlıya geçiş, kaynak yenileme, 429/503/bağlantı
  kesintisi, duraklatma, ani kapatıp yeniden açma ve aynı baytlardan devam
  senaryoları var. İlk geniş çalışmada eski hedefi kullanan test fixture'ı
  yeni özel çalışma klasörüne uyarlandı; son geniş çalışmanın tamamı geçti.

## Kurulum ve yükseltme

Yeni üretim kurulum adayı derlendi. Ayrı uygulama/registry kimliği ve ayrı
profil kullanan gerçek Inno Setup fixture'ında eski kurulu payload'dan
yükseltme, temiz kurulum, ayar/dil/geçmiş/taslak/yarım iş korunması, tüm kurulu
payload dosyalarının hash karşılaştırması, aynı sürüm/downgrade reddi ve
profil koruyan kaldırma geçti. Test kurulumu sonunda kaldırıldı. Kişisel
kurulu uygulama ve önceki `releases/v1.4.3` dosyası değiştirilmedi.

Fixture mevcut Windows üzerinde kullanıcı yetkisiyle çalışır; üretim UAC
akışı ve temiz Windows sanal makinesi denenmedi. USB/NAS ve tüm donanım/codec
kombinasyonları için garanti verilmez. Tam dosya okuma izolasyonu eklenmedi;
önceki güvenlik raporundaki sınırlar geçerlidir.

## Son aday

- Önizleme: `build/optimized-package/YoutubePro/YoutubePro.exe`, `_internal` ile birlikte.
- EXE SHA-256: `7286776f45a619141cde0cafceed91594fdad9df2013609ae12b8ce5d5ce42db`.
- Kurulum: `build/performance/candidate/VideoDownloaderPro_Setup.exe`.
- Kurulum SHA-256: `a57c78a7eaa6673d98ce2d21c6914e4e9befc9e4dc5f32559c15f0f8337eb002`; **45,542,963 bayt**.
- Eşlik eden `SHA256SUMS.txt` ve `release-info.json` aynı klasördedir.

Bu aday önceki `protected-package` önizlemesini günceller. Eski
`releases/v1.4.3` kurulumunu yayımlamayın. Yayın istendiğinde eşleşen kaynak,
tag ve bu adayın varlıklarıyla yayınlama adımları ayrıca uygulanmalıdır.
