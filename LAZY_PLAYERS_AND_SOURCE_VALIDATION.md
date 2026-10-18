# Lazy oynatıcı ve kaynak doğrulama — yayımlanmamış kaynak değişikliği

## Gerçek hata

HDFilmcehennemi sayfaları masaüstü WebView2'de yükleniyor, ancak ilk DOM'da kullanılabilir video yoktu. Büyük bir oynat kapağının arkasında `data-src` taşıyan gizli iframe vardı. İframe başlatılmadan hazır HTML5/JW/Video.js oynatıcılarını taramak bu akışı çözemiyordu. Ayrı bir düz HTTP isteğinin 403 alması, WebView2'de açılan gerçek sayfanın da doğrulamada takıldığı anlamına gelmiyordu.

## Ortak mekanizma

`player_controls.py` açıkça oynatma olarak etiketlenmiş bir kapağın, yakınındaki henüz başlatılmamış tek iframe ile ilişkisini DOM üzerinden kontrol eder. Genel gezinme/üyelik/indirme düğmelerine tıklanmaz. Belirsiz durumlar otomatik seçilmez. Başlatma bir kez yapılır; iframe gerçek sayfanın içinde yüklenir ve mevcut kaynak/istek bağlamı yakalama akışı devam eder. Film slug'ı, içerik kimliği veya site alan adı bu kurala yazılmamıştır.

CAPTCHA/giriş ve DRM durdurma kuralları korunur. Site görünür pencere veya özel bir kontrol gerektirirse kullanıcı devamı hâlâ gerekir. Küçük ikonlardan veya etiketsiz özel kontrollerden güvenle anlam çıkarılması bu değişikliğin kapsamına alınmamıştır.

## Kaynak doğrulama

Gömülü kaynakların metadata'sı kalite listesi verilmeden ve indirmede kullanılmadan önce kontrol edilir: tekil medya olmalı, en az bir açık HTTP(S) ses/video formatı bulunmalı, storyboard/görseller medya sayılmamalı, VOD süresi bildiriliyorsa pozitif ve sonlu olmalıdır. Süresi bilinmeyen yayınlar ve ses çıktıları desteklenir. Bu kontrol tek başına videonun ana içerik olduğunu, ses/görüntü kalitesini veya eksiksiz indirileceğini kanıtlamaz.

Test matrisine isteğe bağlı `--sample` eklendi. Bu modda bir HLS parçasından en fazla 16 KiB okunur, medya dosyası kaydedilmez. Boş yanıtlar, HTML/XML hata sayfaları ve JSON hata yanıtları başarılı medya örneği sayılmaz. Sunucu Range isteğini görmezden gelip HTTP 200 dönse de okuma 16 KiB'de kesilir. Bu küçük örnek kontrolü tüm videonun sonuna kadar denenmesi değildir; normal metadata akışına otomatik örnek indirme eklenmemiştir.

```powershell
python scripts/site_matrix.py --all --sample --timeout 90
python -m unittest discover -s tests -p test_source_validation.py
node tests/test_lazy_player_ui.cjs
python tests/verify_generic_native.py
```

Güncel dört gerçek sayfanın sonuçları `tests/site_matrix_after_lazy.json` içinde tutulur. İlk başarısız HDFilm sonucunu içeren `tests/site_matrix_baseline.json` karşılaştırma için korunur. Dört örnek genel site desteği yüzdesi değildir; 20–30 sayfalık saha hedefi henüz tamamlanmamıştır.

Yerel native fixture ayrıca gerçek iframe adresini yalnızca oynat kapağına tıklanınca yükler; ardından sessiz JW Player başlatma, metadata, kalite seçimi ve gerçek sentetik HLS ses/video çıktıları doğrulanır. Kontrol testleri üyelik/doğrulama düğmelerini, formları, JavaScript adreslerini, iki oynatıcı belirsizliğini ve tekrar tıklamayı dışlar.
