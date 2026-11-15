# İkinci köşe durumu taraması — 15 Kasım 2026

Son aday 1.4.6; henüz yayımlanmadı. 1.4.4/1.4.5 yerel kurulumlarından sürüm
numarası nedeniyle engellenmeden güncellenebilmesi için sürüm artırıldı.

## Testle doğrulanan iki ek hata

- Diskteki ayarların yalnız bir alanı geçersizse `load_settings` tüm tercihleri
  atıp varsayılana düşüyordu. Dil/bildirim/ilk kullanım tercihi gibi sağlam alanlar
  da kaybolmuş görünüyordu. Yeni test düzeltmeden önce `language` için KeyError
  verdi. Okuma artık yalnız geçersiz alan grubunu varsayılana döndürüyor. JSON
  dosyası okuma sırasında değiştirilmez; normal ayar kaydetme hâlâ sıkı doğrulanır.
- `/save-settings` dosyayı işlem kilidini almadan okuyordu. Dil değiştirme ile
  aynı anda gerçekleşince eski dil sonradan geri yazılabiliyordu. Deterministik
  yarış testinde düzeltmeden önce Fransızca yerine İngilizce kaldı. Okuma,
  birleştirme ve doğrulama artık aynı işlem kilidi içinde gerçekleşiyor.

`tests/test_final_edge_cases.py` bu iki durumu kalıcı regresyon olarak içerir.
Önceki klasör/dosya/geçmiş/Soup Sieve güvenlik düzeltmeleri de son adayda korunur.

## Hatalı istek ve entegrasyon kontrolü

12 API işleminde 60 hatalı JSON kombinasyonu denendi: ayarlar, indirme, taslak,
liste önizlemesi, kaynak inceleme, geçmiş, duraklat/devam/kaldır, kayıt kurtarma,
kuyruk kurtarma ve dil. Bu denemelerde sunucu hatası oluşmadı. Bozuk IPv6 liste
bağlantısı da ağ işi başlatmadan istemci hatası verdi; bu zaten çalışan koruma
ayrıca teste alındı, yeni düzeltme diye sayılmadı.

İlk 40 ilgili Python testi ve 28 JavaScript testi geçti. Son tam regresyonda
**624 Python testi geçti; sıfır başarısızlık/hata/atlama**. JSON/günlüğü
`build/final-audit/regression.*` altında saklanır.

Son EXE ile gerçek MP4/MP3/M4A/WAV/Opus indirmeleri, Defender kontrolleri,
yabancı Origin/özel IP reddi ve yeniden açılışta ayar/geçmiş korunması geçti.
Kaynak/PYZ/giriş/arayüz karşılaştırması: `build/final-audit/payload-verification.json`.
İzole 1.4.3 → 1.4.6 yükseltme, temiz kurulum, aynı sürüm/sürüm düşürme reddi,
profili koruyan kaldırma geçti. Son test kurulumu kaldırıldı; kişisel uygulama,
ayarlar, geçmiş ve tarayıcı profilleri değiştirilmedi.

## Güvenlik ve sınırlar

Son bağımlılık taramasında bilinen açık yok. Soup Sieve 4.0 sabitlemesi korundu.
Bandit raporundaki mevcut güncelleme URL uyarıları ayrıca korunuyor; bu çalışma
her türlü açığın bulunacağı garantisi değildir. Kanıtlar `build/final-audit/`
altında. Gerçek native klasör penceresinin açılması önceki turda gözlendi;
tam native seçim/iptal otomasyonu ve temiz Windows VM/üretim UAC testi yapılmadı.
Canlı motor değişmediği için dört saatlik kayıt testi yeniden çalıştırılmadı.

## Kullanılacak son aday

- `build/final-audit/candidate/VideoDownloaderPro_Setup.exe`
- Sürüm 1.4.6, **45.663.423 bayt**.
- SHA-256 `4fdd58345726e7c8612481232244b826aaff32811f7d8186738250c537644192`.
- EXE SHA-256 `7e9a89a080bc8048a2451b2872151a79601cedf21728929f732e627575144df7`.

Önceki yerel adaylar bu son iki ayar düzeltmesini içermez. GitHub etiketi/sürümü
oluşturulmadı; yayın aynası yayımlanmış 1.4.3 kaynaklarında bırakıldı.
