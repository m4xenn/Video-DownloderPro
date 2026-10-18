# Genel kaynak keşfi — 1.2.11 test sürümü

## Akış

1. Mevcut yt-dlp desteği çalışır; başarılı olduğunda yardımcı tarayıcı açılmaz.
2. Desteklenmeyen bağlantı veya video kaynağı bulunamaması gibi ayrıştırma hatalarında genel keşif devreye girer. Ağ zaman aşımı, giriş zorunluluğu ve DRM hataları otomatik olarak bu yola aktarılmaz.
3. Gizli WebView2, HTML5 video, JW Player ve Video.js kaynaklarını okur. Aynı kökendeki çerçeveler DOM üzerinden; farklı kökendeki oynatıcılar ayrı, sınırlandırılmış incelemelerle takip edilir.
4. Rapidvid adaptörü artık herhangi bir üst siteye gömülü olduğunda da kullanılabilir. Diğer oynatıcılarda standart DOM ve medya istekleri gözlemlenir.
5. HLS, DASH ve doğrudan video adresleri mevcut yt-dlp kalite seçimi/indirme akışına aktarılır. Kuyruk ve geçmişte asıl sayfanın kimliği tutulur. Önizlemeden hemen sonra başlayan indirme, kullanıcı etkileşimini tekrar gerektirmemek için son 60 saniyede bulunan kaynağı kullanabilir; eski kuyruk girdileri tekrar çözümlenir. Metadata önbelleği 120 saniyedir.
6. Video kaynağına özgü Referer, Origin ve User-Agent bilgileri kullanılır. Yakalanan çerezler global Cookie başlığına yazılmaz; yalnızca medya sunucusu ve dizini için bellek içi çerez deposuna eklenir. İstek başlığı asıl çerez kapsamını göstermediğinden daha dar bir kapsam uygulanır; bazı oturumlu kaynaklar bu nedenle ek destek gerektirebilir.
7. Oynat veya doğrulama etkileşimi gerektiğinde mevcut “Tarayıcıda devam et / Tekrar kontrol et / İptal” alanı kullanılır. Yardımcı pencere normalde gizlidir; inceleme tamamlandığında kapatılır.

## Sınırlar

- En fazla 6 belge, 3 çerçeve derinliği ve belge başına 3 çerçeve adayı incelenir. İncelemeler 18 saniyelik tarayıcı bütçesi ve yaklaşık 60 saniyelik toplam keşif bütçesiyle sınırlıdır; etkileşim oturumu 180 saniyede sona erer.
- Ana oynatıcı, ekran alanı ve kaynak ilişkisiyle seçilir. Benzer büyüklükte ilgisiz videolar tek indirmede birleştirilmez. Ağdaki tek başına bir m3u8/mpd adresi yeterli kabul edilmez; blob video ve aynı belge Referer ilişkisi gerekir. Bu sezgisel bir ayrımdır; her reklam türünü kesin ayırdığı iddia edilmez.
- Başlangıç, çerçeve, nihai belge ve medya adreslerinde genel HTTP/HTTPS adresi ve DNS kontrolleri yapılır. Bu, tarayıcının tüm alt isteklerini filtreleyen bir ağ güvenlik duvarı değildir.
- DRM çözülmez; CAPTCHA otomatik aşılmaz. Her site veya özel oynatıcı için başarı garantisi yoktur. Oynatıcı yalnızca kullanıcı tıklamasından sonra kaynak yükleyebilir.
- Tarayıcı keşfi için masaüstü uygulaması ve WebView2 gerekir. Tamamlanmamış inceleme, çerezler ve geçici kaynak adresleri diske kaydedilmez.
- Bu özellik 1.2.11 kaynak/test paketindedir; yayımlanmış 1.2.8 kurulumunda bulunmaz.

## Doğrulama

- `test_generic_discovery.py`: genel adres/DNS kontrolü, yerel adreslerin reddi, yerel yt-dlp önceliği, DRM/giriş sınırı, ana video/reklam belirsizliği, çerezlerin başka sunucuya veya alt alana taşınmaması, iç içe çerçeveler, döngü/bütçe, devam etme, önbellek ve normal indirmelerin tarayıcı beklememesi.
- `python tests/verify_generic_native.py`: gerçek Windows WebView2 ile yerel, sentetik medya. yt-dlp’nin okuyamadığı dinamik sayfa → farklı kökenli iç içe çerçeveler → JW Player → kalite listesi. HTML5, Video.js ve DASH kaynakları da doğrulanır. Gerçek HLS indirmesinde seçilen 180p ve otomatik maksimum 360p, FFprobe ile ses/video kontrolünden geçer. Teste özel yerel adres izni yalnızca bu fixture içinde uygulanır.
- Mevcut site çözümleyicisi, yerel HLS kuyruk testi ve uygulamanın çevrimdışı Python/JavaScript kontrolleri yeniden çalıştırılır.
- Ticari bir filmin tamamı indirilmez. Sentetik testlerin geçmesi bütün internet sitelerinin desteklendiği anlamına gelmez.
