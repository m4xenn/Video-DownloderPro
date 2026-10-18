# Ağ öncelikli gömülü medya keşfi — yayımlanmamış kaynak değişikliği

## Akış

Gizli tarayıcıda başarılı medya yanıtları sınıflandırılır. WebView2'nin uygulama içi `Network.responseReceived` gözlemleri, mevcut kaynak olaylarını tamamlar; ana sayfa, iç çerçeveler ve yakalanabilen worker oturumları aynı sınırlandırılmış aday havuzuna veri sağlar. HLS, DASH ve doğrudan video kapsayıcıları adres uzantısı veya MIME türünden tanınır. Bu nedenle uzantısız bir manifest de bulunabilir. Yanıt gövdeleri bu keşif sırasında diske alınmaz.

`network_media.py` önce ağ yanıtlarını görünür oynatıcı kanıtıyla ilişkilendirir. Oynatıcı API'si/HTML5 kaynağı ile gerçek isteğin eşleşmesi güçlü kanıttır. Böyle bir eşleşme yoksa aynı belgeye bağlı tek, belirsiz olmayan manifest veya doğrudan video aranır. Canvas tabanlı oynatıcı alanları da aday kanıtı verebilir; yalnızca sayfada bir video isteği görülmesi kendi başına yeterli değildir. Uygun ağ adayı yoksa mevcut DOM/oynatıcı çözümlemesi ve hızlı adaptör yolu korunur.

## Seçim sınırları

- Yalnız başarılı 200/206 yanıtları kabul edilir; HTML/JSON hata yanıtları, HLS/DASH parça dosyaları ve tanınan başlatma dosyaları aday olmaz.
- Normal isteklerde gerçek belge adresi esas alınır. Referer geri dönüşü, belge bilgisi bulunmayan eski kaynak olaylarında veya doğrulanmış worker oturumlarında kullanılır. İlişkisi kurulamayacak bir worker isteği otomatik atanmaz.
- İki benzer büyüklükte bağımsız oynatıcı birleştirilmez. Büyük ana oynatıcı henüz hazır değilken küçük reklam kaynağı seçilmez.
- Aynı oyuncuya ait olduğu ortak URL üzerinden doğrulanan kalite varyantları korunur. Birbirinden bağımsız manifestler aynı video kabul edilmez. DOM kanıtı bulunmayan bir master ve alt varyant manifesti arasındaki ilişki henüz gövde analiziyle çıkarılmadığından bazı çoklu-manifest durumları manuel devam gerektirebilir.
- Belirsiz ağ adayları varsa kullanıcı etkileşimi yoluna dönülür. Aday havuzu 40 yanıt, istek/belge eşleştirmesi 256 kayıt ile sınırlıdır; pencere kapanınca temizlenir.
- Başlıklar yalnız seçilen tam medya URL'si için, mevcut dar kapsamlı çerez aktarımıyla kullanılır. Authorization gibi bilinmeyen özel kimlik bilgileri kopyalanmaz. Tanılama raporuna ham adresler veya çerezler yazılmaz.
- CAPTCHA, giriş ve DRM kuralları korunur. Reklam/ana video ayrımı mutlak bir garanti değildir; çözülemeyen belirsizlikte otomatik seçim yapılmaması tercih edilir.

## Doğrulama

```powershell
python -m unittest discover -s tests -p test_network_media.py
python tests/verify_generic_native.py
python scripts/site_matrix.py --all --sample --timeout 90
```

Yeni yerel native fixture'da `video/src` veya bilinen bir oynatıcı API'sinde kaynak adresi bulunmadan, uzantısız bir HLS manifesti ağdan yüklenir. Canvas alanı ile ilişkili bu yanıt üzerinden gerçek 180p/360p metadata'sı alınır. Aynı senaryo farklı kökendeki iframe içinde de sınanır. Çevrimdışı kontroller; belge ilişkisi, worker geri dönüş sınırı, başarısız/HTML yanıtları, segmentlerin dışlanması, iki oyuncu belirsizliği, reklamın ana oynatıcı yerine seçilmemesi, kalite koruması, kimlik bilgisi kapsamı ve temizlik davranışını kapsar.

Dört gerçek sayfanın son ölçümü `tests/site_matrix_after_network.json` içindedir. Rapor `discovery_method` alanıyla ağ, DOM veya adaptör yolunu ayırır. Her bağlantıda en fazla 16 KiB HLS örneği okunur. Bu, bütün sitelerde çalıştığı veya videonun sonuna kadar indirildiği anlamına gelmez; saha örnek sayısı dört kalmaktadır.
