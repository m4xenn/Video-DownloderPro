# Klasör seçici düzeltmesi — 15 Kasım 2026

**Sonraki güncelleme:** [Masaüstü taraması](DESKTOP_AUDIT_2026-11-15.md) ek hata
düzeltmeleri ve güvenlik bağımlılığı güncellemesini içerir. Kullanılacak son aday
1.4.5'tir; aşağıdaki 1.4.4 dosyası ilk düzeltmenin tarihsel kanıtıdır.

Durum: **1.4.4 yerel düzeltme adayı hazır, yayımlanmadı.** Mevcut kurulum ve
kullanıcının ayarları değiştirilmedi. Önceki 1.4.3 varlıkları korunuyor.

## Neden

1.4.3'ün güvenli Python ortamında Tkinter yoktu. Yayımlanan paketin PYZ'sinde
`tkinter` modülü, `_internal` altında `_tkinter` uzantısı bulunmadığı doğrulandı.
`folder_service.open_folder_dialog` ise Windows'ta Tkinter kullanıyor, hatayı
yalnız konsola yazıp `None` döndürüyordu. API bunu kullanıcı iptali sayıyordu;
bu nedenle düğme hiçbir şey yapmıyormuş gibi görünüyordu.

## Düzeltme

- Tkinter yerine uygulamanın ana pywebview penceresine bağlı yerel
  `create_file_dialog(FileDialog.FOLDER)` kullanılıyor. Yeni bağımlılık eklenmedi.
- Kullanıcı iptali ile servis hatası ayrıldı. Masaüstü penceresi bulunmaması,
  seçicinin açılamaması ve zaten açık seçici için on dilde mesaj var.
- İptal/hata mevcut kayıt yolunu değiştirmiyor. Seçilen yol `innerText` ile
  gösteriliyor; Unicode karakterler korunuyor, kod olarak kullanılmıyor.
- İstemci ve servis aynı anda birden fazla seçici açmayı engelliyor; hata ve
  iptalden sonra tekrar deneme kullanılabilir kalıyor.
- macOS'un bağımsız AppleScript geri dönüşü korundu; seçilen yol betiğe eklenmiyor.

## Doğrulama

- **615 Python testi** geçti: sıfır hata/başarısızlık/atlama.
  `build/folder-picker-fix/regression.json` ve `.log`.
- **28 JavaScript testi** geçti. Yeni test: iptal, HTTP/ağ hatası, tekrar deneme,
  çift tıklama ve Unicode yol; `build/folder-picker-fix/javascript.log`.
- Son gerçek Windows EXE, izole profille açıldı ve düğmeden işletim sisteminin
  ana pencereye bağlı **Klasör Seç** iletişim kutusunun açıldığı gözlendi.
  Yerel pencerenin alanlarına otomasyon erişimi başarısız olduğundan tam native
  seçim/iptal tıklaması iddia edilmiyor; bu durumların servis/API/arayüz sözleşmeleri
  birim testlerinde doğrulandı. `build/folder-picker-fix/native-ui-result.json`.
  Test uygulaması kapatıldı; kişisel profil açılmadı/değiştirilmedi.
- Paket içindeki modüller, giriş ve arayüz varlıkları kaynakla karşılaştırıldı:
  `build/folder-picker-fix/payload-verification.json`.
- Son EXE ile gerçek MP4/MP3/M4A/WAV/Opus indirmeleri ve Defender kontrolleri,
  yabancı Origin/özel IP reddi ve yeniden açılışta ayar/geçmiş korunması geçti.
  `build/folder-picker-fix/native-downloads/result.json`.
- Ayrı kurulum kimliğiyle **1.4.3 → 1.4.4** yükseltme ve temiz kurulum geçti;
  ayarlar, dil, geçmiş, taslak ve duraklatılmış iş korundu. 568 kurulu dosya hash'i
  dağıtımla eşleşti. Aynı sürüm/sürüm düşürme reddi ve profili koruyan kaldırma
  geçti; test kurulumu sonrasında kaldırıldı.
  `build/folder-picker-fix/installer/result.json`.

Bu, üretim UAC veya temiz Windows VM testi değildir. Canlı kayıt motoru
değiştirilmedi; yeni dört saatlik kayıt koşusu yapılmadı.

## Son yerel aday

- `build/folder-picker-fix/candidate/VideoDownloaderPro_Setup.exe`
- Sürüm **1.4.4**, boyut **45.637.907 bayt**.
- SHA-256: `d03dee632d7dbdf0d0d383b1bd6fe6ec5a0a4668e823ddad5cfd94e1d46720bf`.
- EXE: `build/folder-picker-package/YoutubePro/YoutubePro.exe` (`_internal` ile).
- EXE SHA-256: `ba98d5759951512359abc9f829a7db95a92868d171ba4ae81682a68a0143d9cd`.

GitHub sürümü veya etiketi oluşturulmadı; `source-sync` yayımlanmış 1.4.3
kaynaklarında bırakıldı. Bu düzeltmeyi yayımlamak için yeni kaynak ve bu adayın
aynı sürüm altında eşlenmesi, sürüm notları ve yayın doğrulaması gerekir.
