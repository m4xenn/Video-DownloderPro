# İndirme performansı ve sınırlar — 17 Ekim 2026

Sonraki çalışma notu: bu incelemenin ardından ortak kuyruk ve toplam hız sınırı v1.1.4 ile uygulandı. Güncel davranış ve doğrulamalar AUTOMATIC_DOWNLOADS.md içindedir; aşağıdaki metin önceki sürümün incelemesidir.

Bu turda üst menü hizası düzeltildi. Performans/kuyruk kodu incelendi ve davranış testleri yapıldı; aşağıda saptanan backend sorunları bu UI değişikliğinde düzeltilmedi. İnternet hız artışı ölçümü yapılmadı.

## Doğrulanan davranış

Gerçek ThreadPoolExecutor ile çalıştırılan, indirme işçisinin ağ yerine senkronizasyon olaylarıyla taklit edildiği kontrolde:

| Aynı anda başlatılan kuyruk | Kuyruk başına ayar | Gözlenen en yüksek işçi sayısı |
|---|---|---|
| 1 | 1 | 1 |
| 1 | 3 | 3 |
| 2 | 3 | 6 |

Sonuç: `src/core/queue_manager.py` içindeki havuz tek çağrı içinde sınırı uyguluyor. Ancak her /download çağrısı ayrı havuz açıyor; uygulama genelinde ortak sınır yok. Devam et isteği de ayrı çağrı yapıyor ve global durum listesini yeniden oluşturabiliyor. Bu yüzden mevcut özellik temel olarak çalışsa da tamamlanmış, güvenilir bir kuyruk yöneticisi sayılmamalı.

`/save-settings` uç noktasına eşzamanlılık 0 veya 999 gönderildiğinde HTTP 200 alındı (gerçek ayar dosyasına yazma taklit edilerek). `/download` testinde 999 işçi ve negatif hız sınırı, thread başlatma taklit edilerek kontrol edildi; istek 200 aldı ve bu değerler işçiye aktarıldı. HTML min/max alanları sunucuda doğrulama yerine geçmiyor.

## Hız sınırı

Arayüz Kbps giriyor; `Kbps × 125` dönüşümü doğru. Örneğin 1000 Kbps = 125000 bayt/s = 125 kB/s. MB/s ve Mbps farklı birimlerdir; 8 Mbps yaklaşık 1 MB/s eder.

`get_ydl_opts` sonucu üç işçi için ayrı ayrı incelendi: her birinde `ratelimit=125000` vardı. Ortak bir hız sınırlayıcı yok. Dolayısıyla 1000 Kbps girildiğinde tüm uygulamanın toplam 1000 Kbps ile sınırlı kalması garanti edilmiyor. Üç ayrı indirme aynı anda bu limiti kullanabilir. Parça indirme ve farklı protokoller ayrıca ölçülmeli; bu incelemede gerçek ağ üzerinden toplam sınır benchmark'ı yapılmadı.

Diğer eksikler:

- `resumeItem` hız sınırı ve altyazı seçeneklerini göndermiyor; devam isteğinde hız sınırı 0 olabiliyor.
- Kaydedilen ayarlar arayüz açıldığında /get-settings ile geri yüklenmiyor; ekrandaki hız/eşzamanlılık değerleri ile kaydedilmiş değerler ayrışabiliyor.
- /download, hız alanı gönderilmezse kaydedilmiş hızı kullanmıyor.
- Hız sınırı negatif/geçersiz değerler için backend doğrulaması içermiyor.
- Havuz tamamlanınca False sonuçlar ve Future exception'ları okunmadan `finished_all` yazılıyor; başarı bildirimi güvenilir değil.

## Hızı artırmak için öncelikler

1. **Gereksiz tekrarları azaltmak:** Arayüz /get-info ile bilgi alıyor. İndirme işçisi `extract_info(download=False)` çalıştırıyor; ardından `download([url])` yeniden çözümleme yapıyor. Bilgiyi kontrollü süreyle önbelleğe almak ve aynı işte tekrar çözümlemeyi azaltmak özellikle başlamadan önceki beklemeyi azaltabilir. Süresi dolan medya URL'leri için yeniden çözümleme yolu korunmalı.
2. **Ortak kuyruk yöneticisi:** Tek havuz, 1–10 arası doğrulanmış işçi sayısı, öğe bazlı durum ve gerçek duraklat/devam et. Bu, gereksiz fazla bağlantı ve birbirini ezen global durumları önler.
3. **Ölçerek paralellik ayarı:** Varsayılan zaten 3 video ve video başına 5 parça. Parça paralelliği yalnız desteklenen DASH/HLS indirmelerinde işe yarar. Sayıyı yükseltmek daha fazla hız garantisi vermez; kaynak sunucu, ağ ve disk sınırına göre denemek gerekir. Önce 1/2/3 video ve 1/3/5 parça ile aynı kaynağı karşılaştır.
4. **İndirme ve dönüştürmeyi ayrı göstermek:** MP3 çıkarma, kapak ekleme veya codec dönüştürme ağ hızından bağımsız CPU/disk işidir. Gereksiz video yeniden kodlamasından kaçınmak toplam bitiş süresini azaltabilir; format/oynatıcı uyumluluğu korunmalı.
5. **Toplam ve öğe başına limitleri ayırmak:** Kullanıcıya anlaşılır Mbps veya MB/s birimi ve açık kapsam gösterilmeli. Gerçek toplam limit, tüm işçiler/parçalar arasında ortak bir sınırlayıcı gerektirir; sadece aynı yt-dlp ratelimit değerini kopyalamak yeterli değil.

Resmi seçenek açıklamaları: https://github.com/yt-dlp/yt-dlp#download-options

## Önerilen yeni özellikler

Önce güvenilirlik: kalıcı kuyruk ve kapatıp açınca devam, öğe bazında hata/yeniden dene, toplam hız/kalan süre/dosya boyutu. Sonrasında playlist içinden öğe seçimi, yinelenen bağlantı/dosya tespiti ve önceden tanımlı format-kalite profilleri eklenebilir. Bunlar bu turda uygulanmadı.

## UI doğrulaması

Başlık ve araç çubuğu ayrı satırlara alındı. Dil seçici 76×36, ikon düğmeleri 36×36; hepsinin üst koordinatı eşit ölçüldü. Başlık satıra bölünmeden gösterildi. 26 uygulama güncelleme, 20 bileşen, 5 uygulama güncelleme UI ve 6 bileşen UI kontrolü geçti. Bu testler indirme sınırlarının yukarıda açıklanan eksiklerini ortadan kaldırmaz.
