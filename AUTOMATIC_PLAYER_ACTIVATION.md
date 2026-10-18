# Otomatik oynatıcı hazırlama — yayımlanmamış kaynak değişikliği

Önce yt-dlp ve mevcut kaynak çözümleyicileri denenir. Gerekirse gizli WebView2 penceresi, gerçek üst sayfasını koruyan iç çerçeveleri inceler. Tanınan tek ana oynatıcı bulunduğunda sessiz oynatma denenerek gerçek medya isteğinin oluşması beklenir. Kaynak ve gerekli istek bağlamı elde edilince yardımcı pencere kapatılır.

## Kapsam

- HTML5 video, JW Player ve Video.js kendi oynatma API'leriyle başlatılır. Genel sayfa düğmelerine veya reklamlara tıklanmaz.
- `aria-label` ile açıkça oynat olarak etiketlenen büyük bir kapak, yakınında tek bir henüz başlatılmamış `iframe[data-src]` varsa lazy oynatıcı kapısı olarak algılanır. Normal sayfa kontrolleri, bağlantılar, formlar, gönder düğmeleri, birden fazla iframe/kapak ve aşırı büyük ilgisiz kapsayıcılar bu yolun dışında tutulur. Her kapak en fazla bir kez tıklanır; sonrasında mevcut çerçeve keşfi ve sessiz oynatıcı API'leri kullanılır. Film/site adresine bağlı kural bulunmaz.
- Belirsiz benzer büyüklükte oynatıcılar ve küçük reklamın önündeki büyük iframe durumunda otomasyon bekler. Çerçevelerin gerçek DOM ataları ve alan sınırları korunur.
- Aynı belge için en fazla iki, inceleme başına toplam dört başlatma denemesi; aynı belgenin denemeleri arasında en az beş saniye vardır. Mevcut 18 saniyelik inceleme ve 180 saniyelik yardımcı pencere ömrü korunur.
- Görünen doğrulama/giriş kontrolleri ve bilinen doğrulama sayfası başlıkları otomatik başlatmayı durdurur. Bu algılama sezgiseldir, bütün doğrulama ekranlarını tanıma garantisi değildir. CAPTCHA çözülmez, DRM kaldırılmaz, tarayıcı görünürlük veya güvenlik kısıtlamaları değiştirilmez.
- Kullanıcı “Tarayıcıda devam et” seçerse kaynak iki dakika boyunca otomatik kontrol edilir. Kontroller çakışmaz; başarı, iptal, farklı bağlantı veya süre sonu izlemeyi durdurur. Kontrol işlemi zaman aldığı için dört saniyelik bekleme, bir önceki isteğin tamamlanmasından sonra başlar. Manuel tekrar kontrol düğmesi korunur.
- Gömülü tarayıcı görünür olmadan oynatmayı reddeden veya özel bir oynatma düğmesi gerektiren sitelerde kullanıcı müdahalesi gerekir. Yerel LLM veya CAPTCHA çözücü eklenmedi.

## Doğrulama

```powershell
python -m unittest discover -s tests -p test_player_activation.py
node tests/test_player_activation_ui.cjs
node tests/test_site_inspection_ui.cjs
python tests/verify_generic_native.py
```

Native sentetik test, iki çapraz kökenli iframe içindeki kaynağı **yalnızca sessiz play çağrısından sonra** veren JW Player fixture'ını kullanır. Gizli pencerede otomatik başlatma, medya başlıkları, kalite seçimi, gerçek 180p/360p sesli HLS çıktısı ve temizlik doğrulanmıştır. Bu test gerçek sitelerin başarı yüzdesini ölçmez. %90 başarı iddiası için farklı oynatıcıları temsil eden bir saha testi gerekir.

API kaynakları: [JW Player oynatma](https://docs.jwplayer.com/players/reference/playback), [JW Player sessiz mod](https://docs.jwplayer.com/players/reference/setmute_state_), [Video.js Player](https://docs.videojs.com/player).
