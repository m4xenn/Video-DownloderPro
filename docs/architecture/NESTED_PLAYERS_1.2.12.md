# İç içe oynatıcı düzeltmesi — 1.2.12 test sürümü

## Sorun ve çözüm

Aniwatch bölüm sayfasındaki video, iki farklı kökene gömülü bir oynatıcı zincirinden yükleniyordu. 1.2.11 bu çerçeveleri ayrı üst sayfalar olarak açtığından oynatıcının gerçek üst sayfa ortamı kayboluyordu. Ayrıca ilk yapılandırmadaki kaynak adresi, gerçek medya isteğinin Origin/Referer bilgileri olmadan uygulamaya aktarılabiliyordu.

- Windows WebView2 `FrameCreated` / `ExecuteScriptAsync` API'leriyle iç çerçeveler özgün sayfanın içinde incelenir. Bu değişiklik film, bölüm veya site kimliğine bağlı değildir.
- Yalnızca DOM'da görülen ve yeterli alana sahip oynatıcı çerçeveleri ile bunların doğrulanmış alt çerçeveleri aday sağlar. Çerçeve derinliği 3, kayıt sayısı 24 ile sınırlıdır. Tanınmayan platformlarda sınırlandırılmış eski gezinme yolu korunur.
- Farklı süreçteki çerçeve/worker istekleri WebView2'nin uygulama içi protokol API'sinden gözlemlenir. Uzaktan hata ayıklama portu açılmaz; tarayıcı güvenlik ayarları kapatılmaz. İstek/ek başlık gözlemleri 256 kayıtla sınırlıdır.
- Yalnızca seçilen kaynağın gerçek Referer, Origin, User-Agent ve Cookie alanları aktarılır. Authorization ve bilinmeyen özel kimlik doğrulama başlıkları kopyalanmaz. Çerezlerin başka sunuculara taşınmaması için önceki dar kapsamlı çerez deposu kullanılır.
- İç oynatıcı kaynağı yapılandırmada görünse bile gerçek istek bağlamı henüz oluşmadıysa erken sonuç verilmez. Gerekirse mevcut “Tarayıcıda devam et / Tekrar kontrol et” arayüzüne geçilir.
- Windows'ta başta gizli oluşturulan kontrol sonradan hâlâ arka planda kalabildiğinden, ilk “Tarayıcıda devam et” tıklaması aynı inceleme kimliği ve keşif konumuyla görünür bir kontrol oluşturur. Bu ilk gösterimde sayfa yeniden yüklenir. Daha sonraki gösterimler kullanıcı oturumunu veya doğrulama ilerlemesini sıfırlamaz. Eski pencerenin kapanması yeni oturumu kapatmaz.
- Normal incelemede pencere gizlidir; yalnızca kullanıcının açık devam eylemi görünür pencere açar. Video bulunduğunda ve uygulama kapatıldığında yardımcı kontrol temizlenir.

## Gerçek sayfa doğrulaması

`https://aniwatch.co.at/one-piece-episode-1-english-subbed/` bağlantısı gerçek Windows WebView2 üzerinde yeniden üretildi. Son akışta ilk “Tarayıcıda devam et” adımından sonra bir kontrolle kaynak okunabildi: **1080p**, **1477 saniye (24:37)**. Aynı istek bağlamıyla ilk HLS parçasından **16.384 bayt** okundu. Sunucu Range isteğine HTTP 200 döndüğü için istemci okuması açıkça 16 KiB ile kesildi; bölümün tamamı indirilmedi ve medya dosyası kaydedilmedi.

Yerel sentetik fixture, üst pencereye gerçekten bağımlı çapraz kökenli iç oynatıcıyı, HTML5/JW Player/Video.js/DASH/blob kaynaklarını ve gerçek 180p/maksimum 360p sesli HLS dosya çıktısını doğrular. Görünür kontrole geçiş, sabit inceleme kimliği, doğrulama oturumunun tekrar gösterimde korunması, çerçeve kökeni, DRM aktarımı ve kaynak başlıklarının kapsamı çevrimdışı testlerle kapsanır.

Bu doğrulama bütün sitelere, bütün bölümlere veya tam bölümün sonuna kadar indirilebilmesine garanti vermez. Bazı oynatıcılar kullanıcıdan oynat düğmesine basmasını isteyebilir. DRM çözülmez, CAPTCHA otomatik tamamlanmaz.

## Çalıştırma

```powershell
python -m unittest discover -s tests -p test_webview_frames.py
python tests/verify_generic_native.py
python tests/probe_site_native.py https://aniwatch.co.at/one-piece-episode-1-english-subbed/ --metadata --sample --continue-in-browser --output build/site-probe.json
```

Son komut geçici bir tanı penceresi açar ve gerekirse devam akışını dener; kayıtta başlık değerleri, çerez değerleri veya medya URL'leri bulunmaz. `--sample` yalnızca `--metadata` ile kullanılır ve ilk medya parçasından en fazla 16 KiB okur.
