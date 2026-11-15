# Masaüstü hata ve güvenlik taraması — 15 Kasım 2026

**Sonraki tur:** [İkinci köşe durumu taraması](FINAL_EDGE_AUDIT_2026-11-15.md),
iki ek ayar hatasını gideren son 1.4.6 adayını ve kanıtlarını içerir.

Son yerel aday **1.4.5**, yayımlanmadı. Mevcut kullanıcı kurulumu, ayarlar,
geçmiş ve tarayıcı profilleri değiştirilmedi. `source-sync` yayımlanmış 1.4.3'te.

## Bulunan ve düzeltilen sorunlar

1. Önceki klasör seçici düzeltmesi korundu: paketlenmiş Python'da olmayan Tkinter
   yerine ana pencereye bağlı yerel pywebview seçicisi, hata/iptal ayrımı, on dilde
   hata mesajları, çift açılma engeli ve mevcut hedefi koruma.
2. `/open-folder`, JSON içindeki gerçek dosya yolunu URL-decode ediyordu. `%41`
   gibi geçerli dosya adı parçaları değişebiliyor, yanlış hedefe bakılabiliyordu.
   Artık yol olduğu gibi kullanılıyor.
3. Aynı işlem bir klasör verildiğinde onun üst klasörünü açıyordu; artık klasörün
   kendisini açıyor. Olmayan hedef veya işletim sistemi hatası başarı sayılmıyor.
   Başlatma hatası JSON ve yerelleştirilmiş mesajla dönüyor; shell kullanılmıyor.
4. Geçmişteki tek bir `track_options` kaydının bozuk JSON, liste veya null olması
   bütün geçmiş sayfasını bozabiliyordu. Optional metadata okuması güvenli hale
   getirildi. `recording_parts:null` da artık sayfayı bozmuyor. Okuma, bozuk
   veritabanı içeriğini otomatik olarak değiştirmiyor; bu durum test edildi.
5. Bağımlılık taraması Soup Sieve 2.10 için üç bilinen açık bildirdi:
   CVE-2026-126190, CVE-2026-126193, CVE-2026-126191. Bunlar HTML eşleştirme ve
   CSS seçici ayrıştırmada aşırı CPU/özyineleme riskleri. Uygulamadaki seçiciler
   genellikle sabit olduğu için her seçici açığının uygulamada istismar edilebilir
   olduğu iddia edilmiyor; dışarıdan HTML işleme senaryosu önemlidir.
   Soup Sieve **4.0.0** ile tüm sürümler sabitlendi ve paketleme ortamı güncellendi.

## Doğrulama ve kapsam

- Yeni dört masaüstü regresyonu: klasörün kendisini açma, gerçek `%xx` dosya adı,
  olmayan hedef/OS hatası ve bozuk geçmiş metadata'sının diğer kayıtları gizlememesi.
- Ek kötü niyetli HTML testi: 200 seviyelik iç içe HTML'de `section div div div`
  eşleştirmesi güncel motorla zaman sınırı içinde sonuçlanıyor.
- 57 ilk hedefli test ve 28 JavaScript testi geçti. Son güvenlik güncellemesiyle
  **620 Python testinin tamamı geçti**; sıfır hata/başarısızlık/atlama.
  Kanıt: `build/desktop-security/regression.json` ve `.log`.
- pip-audit ilk tarama: bir pakette üç açık. Son tarama: **bilinen açık yok,
  atlanan bağımlılık yok**. JSON/loglar `build/desktop-audit/dependency-audit*`.
- Bandit: yüksek önem bulgusu yok; dört mevcut orta önem B310 uyarısı sabit/doğrulanan
  güncelleme indirme yollarında. Bunlar sıfır bulgu veya tam izolasyon iddiası değildir.
- Yeni pakette Soup Sieve'in sekiz modülü kurulu 4.0 koduyla karşılaştırıldı:
  `build/desktop-security/dependency-payload.json`. Ana uygulama modülleri/giriş ve
  arayüz varlıkları da kaynakla eşleşti (`payload-verification.json`).
- Yeni EXE: gerçek MP4/MP3/M4A/WAV/Opus indirmeleri ve Defender kontrolü, yabancı
  Origin/özel IP reddi, yeniden açılışta ayar ve geçmiş korunması geçti.
- Ayrı kimlikle 1.4.3 → 1.4.5 yükseltme, temiz kurulum, aynı sürüm ve sürüm düşürme
  reddi, profili koruyan kaldırma geçti. Test kurulumu sonrasında kaldırıldı.
- Gerçek yerel klasör penceresinin açılması önceki 1.4.4 testinde gözlendi; aynı
  seçici kodu korundu. Native seçme/iptal tıklaması otomasyonla tamamlanmış
  sayılmıyor; servis/API/JS durumları test edildi. Önceki rapordaki sınırlar geçerli.

Bu çalışma tüm siteleri/donanımları kapsayan penetrasyon testi veya hatasızlık
garantisi değildir. Üretim UAC/temiz Windows VM testi yapılmadı. Canlı kayıt
motoru değiştirilmedi; dört saatlik test yeniden çalıştırılmadı.

## Kullanılacak aday

`build/desktop-security/candidate/VideoDownloaderPro_Setup.exe`

- Sürüm: **1.4.5**, boyut **45.656.064 bayt**.
- SHA-256: `dd8320d2c4a402511c9e48b0b02b3905bed51f1f43c7e4b90177174323d9a351`.
- EXE SHA-256: `4d515b1eef757717dea86ad479f7d3753bb30e54c84ab901a3953f13428f322b`.
- Yeni paketin indirme/kurulum kanıtları `build/desktop-security/` altında.
- Eski `folder-picker-fix`, `desktop-audit` ve `desktop-audit-final` paketleri
  son bağımlılık güncellemesini içermez; bu adayın yerine kullanılmamalı.
- 1.4.4 daha önce yerel kurulum olarak verilmiş olabileceğinden yeni sürüm 1.4.5
  seçildi. Aynı sürümün farklı baytlarıyla yükseltme engeline takılmak önlendi.

GitHub yayını veya kullanıcı uygulamasının kurulumu otomatik yapılmadı.
