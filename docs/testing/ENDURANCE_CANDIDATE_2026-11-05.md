# 1.4.3 son kurulum adayı — 5 Kasım 2026

**Yerel kabul kontrolleri geçti. Aday hazırlandı; yayımlanmadı.** Bu rapor önceki
kararlılık adaylarının ve uzun kayıt için açık bırakılan kabul durumunun yerini alır.

## Doğrulanan kaynak ve paket

- Dört saatlik düzeltilmiş kayıt: **14.399,947528 saniye** (yaklaşık dört saat).
  Tüm ses/görüntünün sıkı decode'u geçti, kayıt hata kuyruğu boştu. Bellek büyümesi
  kontrolü geçti; kararlı dönem RSS farkı −17.403.904 bayt. Dosya 634.649.035 bayt.
  Kanıt: `build/stability/four-hour-corrected/result.json`.
- Bu koşudaki **yedi kaynak hash'i**, paketleme öncesinde güncel dosyalarla
  karşılaştırıldı. Erken, doğrulanmamış bitiş koruması yeni paketin içinde.
- Güncel kaynakla 607 Python testi geçti, sıfır başarısızlık/hata/atlama.
  `build/stability/endurance-review-regression.json` ve `.log`.
  Değişmeyen arayüzün önceki 27 JavaScript testi ve on dil kontrolleri geçerli.
- PYZ'de bulunan yerel modüller, ana giriş ve tüm static/template dosyaları
  kaynakla eşleşiyor. `services.live_completion` dahil yeni modüller zorunlu
  olarak kontrol edildi: `build/endurance-release/payload-verification.json`.

## Gerçek Windows uygulaması

- Yeni EXE ile MP4, MP3, M4A, WAV, Opus ve ayrıca MKV indirmeleri geçti.
  Her gerçek indirmede Defender sonucu `checked`; eski çıktılar korundu.
- Yabancı Origin/özel IP bağlantısı reddi ve Fransızca hata mesajı kontrolü geçti.
- Uygulama yeniden başlatıldığında dil, bildirim ayarı ve geçmiş korundu.
- Kanıt: `build/endurance-release/native/result.json` ve `native-mkv/result.json`.

## Kurulum ve yükseltme

Yeni üretim kurulum dosyası derlendi. Aynı paketle ayrı kurulum kimliği ve çalışma
alanı altında gerçek eski sürümden yükseltme ve temiz kurulum test edildi:

- 1.4.2 → 1.4.3 geçişinde ayarlar, dil, geçmiş, taslaklar ve duraklatılmış iş korundu.
- **568 kurulu dosyanın SHA-256 değeri** yeni dağıtımla eşleşti.
- Aynı sürümü tekrar kurma ve sürüm düşürme reddedildi; dosyalar değişmedi.
- Kaldırmada test profili korundu. Son test kurulumu ve kayıt defteri kimliği kaldırıldı.
- Mevcut kullanıcı kurulumu ve eski `releases/v1.4.3` dosyası değiştirilmedi.

Kanıt: `build/endurance-release/installer/result.json` ve kurulum/kaldırma günlükleri.
Bu test ayrı kullanıcı kimliğiyle yapıldı; üretim UAC akışı veya temiz Windows VM
testi değildir. Dört saatlik tek kaynak koşusu tüm kaynak/codec/USB/NAS veya
24 saat kayıt garantisi vermez. Önceki güvenlik raporunun okuma izolasyonu sınırı
devam eder.

## Kullanılacak son aday

- Kurulum: `build/endurance-release/candidate/VideoDownloaderPro_Setup.exe`.
- Sürüm: **1.4.3**, boyut **45.631.440 bayt**.
- SHA-256: `4ad541cd437ee10a4ffb34335ebb36b0ec76104f5b64b49a25027e495d1ecfbd`.
- Yanında `SHA256SUMS.txt` ve `release-info.json` var.
- Paket: `build/endurance-release-package/YoutubePro`, `_internal` ile birlikte.
- EXE SHA-256: `06ba9c56ed39c6af1cd47773729b44179143d673aa6b2fc647df25a342d038e6`.

Eski `releases/v1.4.3`, `build/performance/candidate` ve
`build/stability/candidate-final` bu son düzeltmeyi içeren kurulum değildir.
GitHub sürümü/tag'i oluşturulmadı, otomatik güncelleme yayını yapılmadı.
