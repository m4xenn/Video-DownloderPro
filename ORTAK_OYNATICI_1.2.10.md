# 1.2.10 — Ortak oynatıcı çözümleme

## Sorun
1.2.9 yalnız Rapidvid.net /vod/ iframe türünü kabul ediyor ve sabit bir kaynak yapılandırmasını ayrıştırıyordu. Aile Planı gibi başka filmlerde Rapidvid.org /vx/ ve tarayıcıda hazırlanan farklı yapılandırmalar kullanılıyor. Film kimliği kodda sabit değildi; desteklenen oynatıcı ailesi gereğinden dardı.

## Düzeltme
- Rapidvid.net ve Rapidvid.org üzerindeki /vod/, /vx/ ve /embed/ yolları ortak adaptörde tanınır.
- Bilinen statik yapı çözülemezse çalışan oynatıcının getPlaylist API'sinden ve video öğelerinden kaynak okunur; HLS/DASH yanıtları da yardımcı olarak gözlemlenir. Her film için kural eklenmez, yeni sayfa JavaScript'i Python içinde eval edilmez.
- CDN adı artık belirli cdnimages sayılarıyla sınırlandırılmaz. HTTPS kaynak biçimi kontrol edilir; yerel adresler, localhost ve kullanıcı/parola içeren adresler reddedilir.
- Birden çok oynatıcı varsa başarısız olanın ardından sıradaki denenir. Birden çok kaynak varsa formatlar birleştirilir ve kullanıcı kalitesi birleşik listeden yeniden seçilir.
- Kullanıcı doğrulaması sırasında ana sayfa/oynatıcı aşaması korunur; yeniden kontrol doğru aşamadan sürer.
- İlk oynatıcı gezinmesinde Referer eşzamanlı olarak uygulanır.

## Doğrulama
Batman dışındaki Aile Planı, Fünye ve Fırtına Geliyor sayfaları gerçek Windows arka plan WebView2 akışında başlık/süre/kalite bilgisi verdi. Bu örnekler uygulama koduna eklenmedi; yalnız test sırasında girildi. Tam filmler indirilmedi.

Yerel iki ayrı HLS kaynağı birleşik kalite listesinde test edildi. 180p seçimi sesli 180p MP4, otomatik en yüksek kalite ise 360p MP4 üretti; FFprobe ile kontrol edildi.

24 adaptör/tarayıcı testi ve mevcut regresyonlar çalıştırıldı. Sınırlamalar: Rapidvid ailesi kapsamındadır; sitedeki her alternatif sağlayıcı veya gelecekteki tüm değişiklikler için garanti değildir. DRM desteklenmez. Her farklı filmin tamamı indirilmedi.
