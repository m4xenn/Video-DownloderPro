# Kararlılık sürümü — 4 Kasım 2026

**Son durum (5 Kasım):** Düzeltilmiş dört saatlik koşu ve yeni kurulumun kabul
kontrolleri geçti. [Son aday raporu](ENDURANCE_CANDIDATE_2026-11-05.md) bu belgedeki
bekleyen durumların ve eski adayların yerini alır. Henüz yayımlanmadı.

**5 Kasım güncellemesi:** Eski dört saat testi erken bitti ve başarısız oldu.
[İnceleme ve düzeltme](LIVE_ENDURANCE_REVIEW_2026-11-05.md) yeni kaynak değişikliği
ve tekrar koşusunu açıklar. Aşağıdaki aday yeni bitiş düzeltmesini içermez;
yeniden paketlenmeden yayımlanamaz. Aşağıdaki “çalışıyor” kayıtları tarihsel durumdur.

Durum: geliştirmeler uygulandı, son aday üretildi. **Yayımlanmadı. Dört saatlik
kayıt kapısı henüz tamamlanmadığından yayın kabulü açık.**

## Uygulanan davranış

- İş denemeleri ve aşama süreleri kalıcı tutuluyor. Dosyayı kaydetme ile geçmişe
  yazma arasındaki kesintilerde kayıtlı dosya kimliği doğrulanıyor; yeniden indirme
  gerekmiyor. Değişmiş/işgal edilmiş hedefin üzerine yazılmıyor.
- Kesilen canlı oturumların parçaları ve bağımsız manifesti korunuyor. Kuyruktan
  kaldırılan işlerin parça referansları geçmişte kurtarılabilir kalıyor. Parçalar
  ayrı aktarılabiliyor; gerçek akışları uyumlu olanlar açık boşluk onayıyla
  birleştirilebiliyor. Farklı oturumların arası kesintisiz kabul edilmiyor.
- VOD video için MP4/MKV seçimi ve video akışını yeniden kodlamadan remux var.
  Bilinen kaynak codec/çözünürlük/fps/HDR beklentileri çıktıda kontrol ediliyor.
  Bilinmeyen özellikler doğrulanmış gösterilmiyor. Ses biçimi seçimi amaçlı ses
  dönüşümü yapabilir. Canlı kayıt MP4 olarak kalıyor.
- Kurtarma merkezinde dosyayı tamamlama, klasör değiştirme, MKV ve en yüksek kalite
  denemesi; parça aktarma/birleştirme ve işlem iptali var. Arayüz on dili izliyor.
- İşleme aşamalarında geçen süre ve belirsiz ilerleme görünümü var. Değişmeyen
  satırların DOM güncellemesi atlanıyor; hız örnekleri yaklaşık 101 kovayla sınırlı.

## Doğrulama

- Nihai kaynakla **602 testlik tam regresyon**: sıfır hata/başarısızlık/atlama
  (`build/stability/regression-final.json` ve `regression-final.log`). Son eklenen
  gerçek HDR ve yeniden başlatma kontrolleri dahil 23 hedefli test de ayrıca geçti
  (`final-targeted.json`). Mevcut 27 JavaScript testinin tamamı geçti.
- Gerçek FFmpeg/FFprobe: ayrı aktarımda kodlanmış paket hash'leri değişmedi;
  uyumsuz boyut/ses akışları birleştirilmiyor; iptal asıl parçaları koruyor.
  Kaydedilmiş gerçek medya, yeniden indirme işçisi çağrılmadan doğrulanıp kurtarıldı.
- Gerçek yt-dlp remuxer: 10 bit VP9 HDR ve 59,94 fps, MP4 ve MKV'ye aktarımda
  paket hash'leri, piksel biçimi ve HDR aktarım/renk bilgileri korundu. Test kaynağı
  lavfi ile üretildi; bu, tüm codec/donanım/kapsayıcı kombinasyonları garantisi değil.
- Chromium: on dil, beş aşama, canlı kapsayıcı kilidi, boşluk onayının Escape ile
  iptali, sıfır sayfa hatası. Bin öğe: oluşturma 189,9 ms, ilk yerelleştirme 65 ms,
  değişmeyen yenileme 4,3 ms. Değişmeyen satırda sıfır DOM mutasyonu.
  Kanıt: `build/stability/ui/result.json`, açık/koyu tema ekran görüntüleri.
- Son gerçek Windows EXE: MP4/MP3/M4A/WAV/Opus indirildi, gerçek Defender kontrolü
  geçti; yabancı Origin ve özel IP bağlantıları reddedildi; yeniden açılışta dil,
  ayarlar ve geçmiş korundu. `build/stability/native-final-verified/result.json`.
  Yeni MKV seçimi de son EXE'de gerçek MKV çıktı ve geçmişten tekrar indirme ile
  doğrulandı (`build/stability/native-mkv-final/result.json`).
- Son kurulum: ayrı kullanıcı kimliği/klasöründe eski sürümden yükseltme, temiz
  kurulum, aynı sürüm ve sürüm düşürme reddi, profili koruyan kaldırma geçti.
  **566 dosya** dağıtım hash'leriyle eşleşti; test kurulumu sonrasında kaldırıldı.
  `build/stability/installer-final/result.json`. Gerçek üretim kurulumu değişmedi.
- Beşer dönüşümlü açılış: önceki optimize pakette medyan 1,085 sn, yeni pakette
  1,099 sn. Yaklaşık 14 ms fark ölçüm değişkenliği düzeyinde; hızlanma iddiası yok.
  Ölçüm HTTP arayüz hazır olma anına kadar, görsel ilk kareye kadar değil.
- Bandit: sıfır yüksek önem, dört daha önce incelenmiş orta önem bulgusu
  (sabit güncelleme URL'leri); `build/stability/bandit.json`.

## Açık yayın kapısı

`scripts/check_recording_endurance.py --minutes 240 --label four-hour` gerçek
duvar saatiyle çalışıyor. Güncel durum `build/stability/four-hour/result.json`.
Yaklaşık 76 dakika kayıtta test hâlâ çalışıyordu; **dört saat geçti denmedi**.
Tamamlanınca tüm ses/görüntünün sıkı decode'u, süre, bellek büyümesi ve motorun
altı kaynak hash'inin değişmediği kontrol edilecek. Sonuç `passed` olmadan
uzun kayıt/yayın kabulü tamamlanmış sayılmamalı. Bu test, değiştirilmemiş yakalama
motorunu sınar; yeni kurtarma katmanı yukarıdaki kısa hata/medya testleriyle sınandı.

Taze Windows VM, üretim UAC akışı, 24 saat kayıt ve tüm USB/NAS senaryoları
denenmedi. Ağ/servis kısıtları ve eksik yayın geçmişi tamamen giderilemez. Önceki
güvenlik raporunun tam dosya okuma izolasyonu sınırı devam ediyor.

## Son aday (yayın kapısı açık)

- `build/stability-final-package/YoutubePro/YoutubePro.exe`, `_internal` ile.
- EXE SHA-256: `6f10689adc8e857e460029b33fa7f24a76b6fff879eb07e718b423855097c4a1`.
- `build/stability/candidate-final/VideoDownloaderPro_Setup.exe`, 45.633.830 bayt.
- Kurulum SHA-256: `450829c42878f143ca66eaf1573f386f54795afd4e2b72bd8a26be211a40bfb9`.
- PYZ'de bulunan yerel kaynak modülleri, ana giriş ve tüm static/template varlıkları
  kaynakla birebir karşılaştırıldı (`build/stability/payload-verification.json`).
- Eski `releases/v1.4.3`, `build/performance/candidate` ve `candidate-2` bu
  geliştirmeleri içeren son aday değildir. Bunları yeni sürüm diye yayımlamayın.
