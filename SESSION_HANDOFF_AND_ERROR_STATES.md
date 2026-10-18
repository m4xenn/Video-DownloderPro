# Oturum devri, sınırlı kaynak yenileme ve kalıcı hata durumu

Yayımlanmamış kaynak değişikliğidir; mevcut kurulum dosyasını değiştirmez.

## Tarayıcıdan indirmeye geçiş

- Link önizlemesinde medya bulunduğunda tarayıcı hemen kapatılmaz. Kısa ömürlü bir oturum devri kaydı tutulur; kullanıcı indirmeyi başlatınca önbellekteki aynı kaynakla birlikte indirme işlemine devredilir.
- İlk medya baytları indirme ilerlemesine ulaştığında yardımcı tarayıcı bırakılır. Hata ve iptal de sahip olunan kaynakları bırakır. Ömür üst sınırı 45 saniyedir; çok yavaş/yanıt vermeyen sunucularda pencere sonsuza kadar açık kalmaz.
- Aynı anda en fazla iki kaynak hazırlama/devretme slotu vardır. İptal edilebilir bekleme kullanılır. Yeni önizleme eski, indirmeye devredilmemiş önizlemeyi kapatabilir; aktif indirme oturumları bundan etkilenmez. Uygulama kapanırken aktif ve devredilmiş bütün yardımcı pencereler temizlenir.
- Otomatik kaynak inceleme WebView2 pencerelerinde `NewWindowRequested` ele alınarak yeni popup pencereleri engellenir. Oynatıcının gerekli ağ istekleri topluca reklam filtresine sokulmaz.
- Oturum tutulurken oynatma API'leri duraklatılır; tarayıcının arka planda ikinci bir video indirmesi yapması önlenmeye çalışılır. Sayfa/iframe ve oturum kapatılmaz.

## HTTP başlıklarının gerçekten uygulanması

Uygulamanın tam `/get-info` yolunda, bağımsız keşif aracında görülmeyen bir 404 yeniden üretildi. Nedeni yt-dlp'nin ilk yerel HTTP denemesinde varsayılan başlıkların bir kopyasıyla istemci oluşturmasıydı. Sonradan yalnız `params['http_headers']` değiştirmek, hazır istemcinin eski Referer/User-Agent ile devam etmesini engellemiyordu.

Tarayıcı bağlamı uygulanırken başlıklar değişmişse boşta olan HTTP transport kapatılıp yeni başlıklarla yeniden oluşturulur; aynı dar kapsamlı cookie jar korunur. Global Cookie/Authorization/Proxy-Authorization taşınmaz. Düz HTTP istemcisinin genel bir sayfada 403 alması, özel/giriş/DRM veya doğrudan medya hatası değilse, bir kez mevcut normal tarayıcı keşfine geçebilir. CAPTCHA çözümü eklenmemiştir.

Yerel ağ testi aynı istemcide önce eski User-Agent ile bir istek yapar, ardından Referer/User-Agent/Cookie şartı arayan endpoint'e yeni bağlamla başarıyla bağlanır. Esaretin Bedeli bağlantısı uygulamanın gerçek `/get-info` yolunda 1080p ve 8553 saniye olarak okunmuş; bir önizleme oturumunun açık kaldığı doğrulanmıştır. Diğer üç bağlantı da aynı uygulama girişinde başarılıdır: Aniwatch 1080p, önceki HDFilm bağlantısı 1080p, FullHD 360p–2160p. Tarayıcı kullanan üç bağlantıda oturum devre açık tutulmuş, hızlı adaptör yolunda gereksiz pencere oluşturulmamıştır. Sonuçlar `tests/site_app_flow_after_handoff.json` dosyasındadır. Bu tam uygulama kontrolü, yalnız GenericResolver yolunu ölçen önceki dört sayfalık testten ayrıdır.

## 403 sonrası toparlanma

- Yalnız gömülü kaynaklarda tek otomatik yenileme bütçesi vardır; metadata sırasında kullanıldıysa indirme sırasında yeniden kullanılmaz.
- Eski kaynak/oynatıcı önbelleği atılır ve kaynak tekrar çözümlenir. İndirme aşamasındaki yenilemede sayfa/video kimliği, VOD süresi ve seçilen ses/video özellikleri karşılaştırılır. Canlı yayın, bilinmeyen süre veya farklı format otomatik eşleşmiş kabul edilmez.
- Hiç medya yazılmamışsa, aynı içerik/format kontrolünü geçen yeni kaynakla aynı çıktı hedefinde bir kez daha denenir. İlk HLS başarısız isteğinde oluşturulan boş `.part` ve sıfır indeksli `.ytdl` checkpoint'i, indirilmiş medya sayılmaz.
- Medya baytları veya dolu bir kısmi dosya varsa yenilenmiş kaynak mevcut dosyaya otomatik eklenmez. Kısmi dosya silinmez. Yeniden gönderilen yeni bir indirme, korunmuş kısmi dosyanın üzerine yazmak yerine numaralı yeni dosya adı kullanır.
- Kuyrukta devam ettirilen gömülü işlerde seçilen kaynağın SHA-256 özeti ve video/format metadata checkpoint'i de karşılaştırılır. Adres değiştiyse veya önceki sürümden kalan kısmi kaydın doğrulama bilgisi yoksa güvenli tarafta kalınarak dosya korunur ve yeni indirme gerektiği bildirilir. Bu metadata kontrolü kriptografik içerik/timeline doğrulaması değildir; farklı kaynaklar arasında otomatik kısmi birleştirme yapılmaz.
- Kalıcı 403 sonsuz döngüye girmez. yt-dlp'nin fragment hatalarını `logger.debug/to_screen` kanalından da bildirdiği hesaba katılır; 403 için 429'a ait uzun beklemeler uygulanmaz. 429'un artan beklemesi korunur. CAPTCHA ve DRM kuralları değiştirilmemiştir.

## Kullanıcıya görünen durumlar

Kaynak incelemesinde ve kuyrukta **Oynatıcı aranıyor**, **Oynatıcı başlatılıyor**, **Kaynak doğrulanıyor**, **Sunucu bekleniyor**, **Kaynak yenileniyor** ve **Video işleniyor** durumları gösterilir.

Hata kodu ve gerçekleştiği aşama kuyruk satırında kalır; yeniden deneme sırasında yeni işlem aşaması ayrıca gösterilir. Başarıyla tamamlandığında eski hata satırı temizlenir; kalıcı tanılama kaydı korunur. Kuyruktaki kopyalama simgesi yalnız ilgili bağlantının güvenli raporunu kopyalar. Pano erişimi yoksa rapor Ayarlar'da seçili metin olarak açılır ve Ctrl+C kullanılabilir.

Kaynak ilerlemesi yerel endpoint'ten okunur; istekler çakışmaz ve işlem bitince izleme durur. İlerleme deposu yalnız URL özeti, aşama ve zaman tutar. Hata raporlarında ham URL, Cookie/Authorization, oturum belirteci ve dosya yolu bulunmaz. Metadata hata yanıtı ve genel hata bildirimi de ham istisna metnini ekrana taşımaz. Teknik rapor İngilizce; yeni arayüz metinleri Türkçe/İngilizcedir.

## Doğrulama

```powershell
python -m unittest discover -s tests -p test_source_handoff.py
python tests/test_source_recovery_local.py
node tests/test_source_progress_ui.cjs
python tests/verify_generic_native.py
python tests/probe_app_info_native.py PUBLIC_PAGE_URL
```

Gerçek yerel HLS testinde ilk parça 403 verir; tek kaynak yenilemesinden sonra tam süreli, doğru çözünürlüklü ve sesli sentetik dosya üretilir. Native WebView2 testi, hem doğrudan indirme çözümlemesinin hem önizlemeden önbelleğe geçen tarayıcının ilk parça isteğine kadar açık kaldığını ve ilk baytlardan sonra kapandığını doğrular. Birim kontrolleri; ikinci 403'te durmayı, değişen formatı reddetmeyi, kısmi dosyayı korumayı, boş checkpoint'i tanımayı, slot/iptal temizliğini ve kaynak özeti eşleşmesini kapsar.

Güncel dört gerçek sayfada metadata ve 16 KiB HLS örneği okunması `tests/site_matrix_after_handoff.json` içinde kaydedilmiştir. Bunlar tam film indirme veya bütün sitelerde çalışma garantisi değildir.
