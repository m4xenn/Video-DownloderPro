> Superseded by 1.2.14. Do not publish 1.2.13; cross-format output loss was found during additional tests.

# 1.2.13 kararlı sürüm adayı

Kesit indirme kapsam dışıdır. Henüz yayımlanmamıştır.

## Bu oturumda doğrulananlar
- 270 izole Python kontrolü geçti. İlk toplu koşu toplam 273 kontroldü; yerel ağ gerektiren iki kontrol sandbox nedeniyle çalışmadı.
- Fragment recovery paketi kısıt dışında yeniden çalıştırıldı: 3/3 başarılı.
- 133 JavaScript arayüz kontrolü başarılı.
- Yerel MP4/MP3 smoke testi: 1/1 başarılı.
- Yerel bant genişliği, eşzamanlı aktarım ve duraklat/devam paketi: 3/3 başarılı.
- Yerel 403 kaynak yenileme ve HTTP başlık aktarımı: 2/2 başarılı.
- Gerçek WebView2 sentetik uçtan uca testi: 18 kontrol başarılı; iç içe iframe, otomatik oynatıcı aktivasyonu, ağdan keşif, sesli HLS indirmeleri ve önizleme oturum devri dahil.

## Paket ve kurulum kabul kontrolleri
- 1.2.13 kurulum paketi oluşturuldu; SHA-256 bilgisi tekrar doğrulandı.
- Paketlenmiş EXE geçici APPDATA ile açıldı; arayüz ve 1.2.13 sürümü doğrulandı.
- Gerçek kurulu 1.2.8 dosyaları ile 1.2.13 dağıtım dosyalarından ayrı kimlikli kullanıcı kurulumu üretildi. Üretim kurulum betiğinde yalnız kimlik, yönetici gereksinimi, hedef klasör ve kısayol/kurulum sonrası çalıştırma bölümü test ortamına uyarlandı.
- 1.2.8 kurulumu, uygulamanın açılması ve 1.2.13'e yükseltme geçti. Kurulan 1877 dosyanın tamamı dağıtımla SHA-256 düzeyinde eşleşti.
- Dil, manuel eşzamanlılık, hız limiti, geçmiş, kuyruk taslağı ve duraklatılmış iş yükseltmede korundu.
- Aynı sürümü yeniden kurma ve eski sürüme dönme engellendi; uygulama dosyaları değişmedi.
- Kaldırma testi geçti; test profilindeki veriler korundu. Ardından boş uygulama klasörüne 1.2.13 kurulumu da geçti.
- Tamamen boş kullanıcı profiliyle ilk açılış geçti: varsayılan ayarlar, boş geçmiş ve boş kuyruk doğrulandı.
- Gerçek Windows penceresinde ana ekran, açık/koyu tema, bileşen durumu, ayarlar, kaydırma, Kaydet, v1.2.13 gösterimi, geçmiş ve video/ses seçimi gözle kontrol edildi. Bu kontrollerde engelleyici arayüz sorunu görülmedi.
- Test kurulumu ve geçici kaldırma kaydı temizlendi. Gerçek kurulum 1.2.8 olarak korundu.
- Makine okunabilir sonuçlar: build/installer-acceptance-1.2.13/result.json.

## Doğrulama sınırları ve yayın
- Bu bilgisayarda temiz Windows sanal ortamı yok. Gerçek üretim paketinin yönetici/UAC ve kısayol oluşturma adımları sınanmadı; testler ayrı kimlikli, yönetici istemeyen kurulumla yapıldı. Bu sonuçlar temiz Windows testi olarak değerlendirilmemeli.
- Tam iki sürümlü GitHub üzerinden indir-kur güncelleme kabul testi bu oturumda yapılmadı.
- Kaynak kopyası eşitlendi; yayın etiketi hazırlanan kaynak commitinden oluşturulmalı.
- Henüz GitHub'da yayımlanmadı. Yayında yalnız üretim kurulum dosyası ve SHA256SUMS.txt kullanılmalı; build/ altındaki ayrı kimlikli test kurulumları dağıtılmamalı.
- Yayın sonrası GitHub asset digest ile eski/yeni sürüm karşılaştırması doğrulanmalı.
