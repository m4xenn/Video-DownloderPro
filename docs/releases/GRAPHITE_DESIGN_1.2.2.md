# Video Downloader Pro 1.2.2 — Grafit yüzeyler

18 Ekim 2026. Kullanıcının paylaştığı koyu, yansımalı kontrol referansına göre görsel düzenleme. Yeni indirme özelliği eklenmedi.

- Lacivert arka plan grafit/kömür grisine çevrildi. Ana kart, araç çubuğu ve açılan pencereler aynı yüzey dilini kullanır.
- Büyük tanıtım sloganı kaldırıldı; ana bölüm artık “Yeni indirme”. Boş durum ve alt bilgi sadeleştirildi.
- Mavi yalnız ana eylem ve seçili durumlarda kullanılır. Ana düğmeler kapsül, ekleme düğmesi daireseldir. Açık anahtarlar yeşildir.
- Yüzeylerde üst kenar ışığı, alt gölge ve sınırlı mavi/pembe kenar yansıması bulunur. Arka plan sürekli hareket etmez.
- Fare hareketinde ana yüzeyin ışık merkezi ve üstüne gelinen kontrolün yansıması güncellenir. Aynı anda en fazla bir requestAnimationFrame bekler; fare ayrılınca bekleyen kare ve konum değişkenleri temizlenir. Azaltılmış hareket tercihinde bu davranış kapalıdır. Dokunmatik girişte takip efekti çalışmaz.
- Koyu/açık tema, klavye odağı, Escape ve küçük pencere kaydırma davranışı korunur. Ana kısa metinler mevcut 10 dil için güncellendi.

## Doğrulama

Yalıtılmış örnek sunucu üzerinde 900×710 ve 600×460 içerik alanları incelendi. Ayarlar küçük ekranda 520×416 ölçüsünde ekran sınırları içinde kaldı; yatay taşma görülmedi. Anahtarların açık/kapalı durumları, tema geçişi, ayarlar ve fare hareketinde ışık konum değişkenlerinin değiştiği kontrol edildi. Kullanıcının gerçek ayar/geçmiş dosyaları değiştirilmedi.

44 mevcut JavaScript arayüz/akış kontrolü ve 4 Studio Python kontrolü geçti. İndirme motoru bu görsel değişiklikte değiştirilmedi; önceki 1.2.1 medya testlerinin kapsamı `BATCH_QUALITY_1.2.1.md` içindedir. Bu turda 133 Python testinin tümü yeniden çalıştırılmış olarak sunulmaz.

Görseller: `tests/graphite-dark.png`, `tests/graphite-light.png`, `tests/graphite-settings.png`.

Yeni kurulum: `releases/v1.2.2/VideoDownloaderPro_Setup.exe`. Paket sürümü, statik dosyalar ve SHA256 son derleme sonrası doğrulanır. GitHub'a otomatik yayın yapılmaz. Windows WebView2 ve farklı ekran ölçeklerinde kurulu uygulama kabul kontrolü ayrıca yapılmalıdır.
