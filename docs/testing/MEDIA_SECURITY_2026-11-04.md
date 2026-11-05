# Medya güvenliği ve kullanıcı deneyimi — 4 Kasım 2026

Güncel önizleme ve kurulum adayı için `PERFORMANCE_OPTIMIZATION_2026-11-04.md` raporuna bakın. Aşağıdaki güvenlik çalışmasının kapsamı korunmuş, üzerine ölçülmüş optimizasyonlar eklenmiştir.

Durum: kaynak kod uygulandı, yeni Windows önizlemesi hazırlandı. **Yayımlanmadı.**
Sürüm numarası 1.4.3; mevcut 1.4.3 kurulum dosyası bu çalışmayı içermez.

## Uygulanan korumalar

- FFmpeg/FFprobe, düşük bütünlük seviyesinde ve ayrı Windows Job nesnelerinde çalışır. Yönetici ayrıcalıkları kaldırılır; süreç askıda oluşturulur, sınırlar uygulandıktan sonra başlatılır. Koruma kurulamazsa sınırsız bir sürece geri dönülmez.
- Süreç başına alt süreç sınırı 6; tüm medya işleri için toplam sınır 64. Toplam bellek bütçesi fiziksel belleğin yarısı, 2–8 GiB aralığında sınırlanır. CPU hızına veya indirme bant genişliğine ek sınır konulmaz. Ana uygulama kapanınca medya süreçleri ve beklenmeyen alt süreçler kapanır.
- Her iş özel, gizli ve kalıcı bir çalışma klasörü kullanır. Varsayılan olarak hedef disktedir. ACL/bütünlük etiketi desteklemeyen USB/ağ hedeflerinde yerel çalışma klasörü kullanılır. Eski kontrol noktaları ve yarım dosyalar korunarak taşınır; farklı disklere aktarımda önce tamamlanmış geçici kopya oluşturulur.
- Hedef yol ilk indirme baytından önce ve tamamlanmış dosya aşamasında doğrulanır. Bağlantı/junction/hard-link üzerinden çıktı kaçışı kabul edilmez. Mevcut kullanıcı dosyalarının üzerine yazılmaz.
- Dosyanın gerçek başlığı seçilen kapsayıcıyla eşleşmelidir. Tüm kaynaklarda beklenen video/ses akışları doğrulanır; yerel doğrulama sırasında ağ protokolleri kapalıdır. Uzantısı MP4 yapılmış bir EXE, HTML veya playlist tamamlanmış indirme olarak sunulmaz.
- Windows Defender varsa yalnızca indirilen dosya için, yönetici izni istemeden özel tarama denenir. `-DisableRemediation` kullanılır. Başarılı tarama ile tarama yapılamaması ayrıdır. Tarama için bekleme 15 saniyeyle sınırlıdır; eşzamanlı taramalar sıraya alınır.
- Defender'ın belirsiz `2` sonucu “zararlı kesin bulundu” olarak yorumlanmaz: dosya inceleme için tutulur. Bilinen erişim/kapalı hizmet hataları ve zaman aşımı “ek tarama yapılamadı” olur; hiçbir zaman “güvenli” etiketi verilmez. Gerçek zamanlı antivirüsün bağımsız koruması kapatılmaz/değiştirilmez.
- Başarısız başlık/medya kontrolleri ve inceleme gerektiren taramalar normal klasöre/geçmişe yayımlanmaz; özel klasörde `.blocked` olarak tutulur. Otomatik yeniden deneme veya açma yapılmaz. Geçmişten elle açarken bile gerçek dosya başlığı yeniden kontrol edilir.
- Başarılı dosya doğrulama/taramadan sonra başka bir dosyaya dönüşmüşse yayımlanmaz. Son kaydetme atomik ve üzerine yazmadan yapılır; Windows Internet-zone işareti korunur. Yayımlanan dosyanın bütünlük etiketi ana uygulamanın seviyesine geri alınır.
- Diskte 32 MiB güvenlik payı kalmazsa yarım dosyaları silmeden işlem durur. Medya yardımcılarının çıktıları sınırlı bellekte okunur. yt-dlp dönüşüm günlüklerinin son 256 KiB bölümü korunur; normal uzun loglar bellekte biriktirilmez. Aşırı çıktı üreten süreç durdurulur.

## Kullanıcıya etkisi

Normal indirmelerde yeni onay/UAC penceresi veya URL/site izin listesi yoktur.
Kontrollerin çoğu dosyanın sonunda yapılır; canlı geçmiş yakalama algoritması,
paralel parçalar, bant genişliği bütçesi ve hız kontrolü değiştirilmez.
Kuyrukta kısa doğrulama/tarama/kaydetme durumu görünür. Ek antivirüs taraması
yapılamadıysa tamamlanma satırında açıkça belirtilir. Bu metinler desteklenen
on dilde ve anlık dil değişiminde çalışır.

## Doğrulama kanıtları

- Geniş Python paketi: **571 test**, sıfır hata/başarısızlık/atlama (`build/security-upgrade-regression/full-result.json`).
- Ardından eklenen ilk-bayt çıktı yolu kontrolüyle **53 odaklı test**, gerçek kesinti/devam etme dahil, geçti. Son yt-dlp günlük belleği düzeltmesiyle **47 odaklı test**, MP4, dört ses biçimi, HLS/DASH/altyazı/birleştirme ve tarayıcı aktarımı dahil, geçti (`build/security-upgrade-regression/result.json`). Bu sayılar benzersiz test toplamı olarak toplanmamalıdır.
- Windows'ta gerçek süreç testi: düşük bütünlük seviyesi; kendi çalışma klasörüne yazabilme; normal klasördeki örnek kullanıcı dosyasına yazamama; zaman aşımı; aşırı çıktı; beklenmeyen alt sürecin kapanması. Uzun, zararsız hata günlüğünün sınırlı bellekte tutulduğu da test edildi.
- Ayrı canlı/DVR uyumluluk çalışması: **62 test**, sıfır hata. Gerçek FFmpeg ile ses/video, hızlı geçmişten canlıya geçiş, bağlantı kesintisi, 429/503, yenilenen kaynaklar, duraklatma ve bozuk/kayıp parçada dosya koruma.
- **27 JavaScript test dosyası** geçti. Gerçek tarayıcıda on dilde üç güvenlik aşaması görünürlük kontrolü, tarama kullanılamıyor ve inceleme durumları geçti; sayfa hatası yok (`build/security-upgrade-ui/result.json`).
- Paketlenmiş gerçek uygulama: herkese açık W3Schools MP4 kaynağından **MP4, MP3, M4A, WAV, Opus** indirmeleri, gerçek ses/video doğrulaması ve beş başarılı Defender taraması. Yabancı Origin/özel ağ URL reddi, Fransızca hata metni, yeniden açılışta dil/bildirim/geçmiş korunması kontrol edildi (`build/protected-native-final/result.json`).
- **25 derlenmiş modül ve 5 arayüz dosyası** kaynakla eşleşir (`build/protected-payload-verification.json`). Python 3.14.10 güvenlik güncellemeli derleme ortamı kullanılır.
- Statik taramada yüksek önem dereceli bulgu yok. Dört orta B310 kaydı, önceki denetimde incelenmiş sabit ve doğrulanan güncelleme kaynaklarıdır; yeni medya korumasında orta/yüksek bulgu yok.

## Kapsam sınırı

**Düşük bütünlük, tam dosya okuma izolasyonu değildir.** Medya sürecinin normal
kullanıcı dosyalarını değiştirmesi sınırlanır; mevcut kullanıcının okuyabildiği
dosyaları bütünüyle gizleyen AppContainer uygulanmamıştır. Python kaynak
çözümleme motoru da ana uygulamada kalır. Tam okuma/ağ izolasyonu, canlı kaydın
yerel ağ geçidi ve tarayıcı aktarımıyla uyumlu ek bir mimari çalışma gerektirir.
Bu sürüm için tam sandbox veya sıfır açık iddiası yapılmamalıdır.

Tehdit/dosya değiştirme testleri zararsız fixture ve taklit antivirüs sonuçları
kullanır; gerçek zararlı, EICAR veya bellek istismarı çalıştırılmamıştır. Gerçek
antivirüs testi zararsız medya üzerindedir. USB/ağ dosya sistemi geri dönüşü
denetimli hata/diskler arası taşıma senaryolarıyla test edildi; fiziksel tüm
USB ve NAS aygıtları denenmedi. Son doğrulamalar izole uygulama profillerindedir.

## Önizleme ve yayınlama

Önizleme: `build/protected-package/YoutubePro/YoutubePro.exe` ve yanındaki
`_internal` klasörü birlikte kullanılmalıdır. Paket hash'i ve son gerçek
çalıştırma sonucu `build/protected-native-final/result.json` içindedir.
Son EXE SHA-256: `26c96a1bb3d07368e099a9057412715f19d33b1704acdbd289e99ead1b0651c5`.
Bu önizleme önceki `build/audited-package` önizlemesini günceller.

Kurulum dosyası yeniden oluşturulmalı, kurulum/yükseltme kabul testleri
tekrarlanmalı ve eşleşen kaynak/tag ile yayımlanmalıdır. Bu görevde GitHub
yayını veya kurulu uygulama güncellemesi yapılmadı.

## Birincil kaynaklar

- [Microsoft: Mandatory Integrity Control](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control)
- [Microsoft: Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Microsoft: Defender komut satırı, sonuç kodları ve DisableRemediation](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus)
