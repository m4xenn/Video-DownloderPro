# Tanılama ve site test matrisi

Bu kaynak değişikliği henüz yayımlanmadı. Önceden oluşturulmuş 1.2.12 kurulum dosyasını değiştirmez.

## Uygulamada kullanım

Uygulamayı `python src/main.py` ile yeniden başlatın. Sorun yaşandıktan sonra **Ayarlar → Sorun giderme kayıtları → Kayıtları göster → Raporu kopyala** yolunu kullanın. Pano erişimi çalışmazsa seçili rapor Ctrl+C ile kopyalanabilir.

Son 300 olay `%APPDATA%/YoutubePro/diagnostics.sqlite3` içinde korunur. Arka arkaya aynı kaynak/aşama/kod olayları tek satırda tekrar sayısıyla tutulur. Saatler UTC'dir. `VIDEO_DOWNLOADER_DATA_DIR` tanımlıysa kayıt bu klasöre yazılır. Yazma hatası indirmeyi durdurmaz; rapor arayüzünde erişim sorunu belirtilir.

Rapor; uygulama/Python/yt-dlp sürümü, aşama, alan adı, opak kaynak kimliği, sabit hata kodu ve olay sayısı içerir. Bu sayı yeniden deneme sayısı değil, aynı kodun art arda kaç kez kaydedildiğidir. Ham hata mesajı, video başlığı, URL yolu/sorgusu, çerez, istek başlığı ve yerel dosya yolu kaydedilmez. Kaynak çözümleme, tarayıcı keşfi, otomatik oynatma denemesi, indirme ve işleme hataları izlenir. Otomatik yeniden denemede veya uygulama kapatıldığında önceki olay kaybolmaz.

Bu bir tam konsol dökümü değildir. Bilinmeyen hatalar `unexpected` koduna indirgenir; gerektiğinde özel bir sınıflandırma eklenir. İndirme kuyruğu/geçmişi ayrı veri depolarıdır; tanılama raporu bunların ham içeriğini dışa aktarmaz. Kayıtlar otomatik olarak bir sunucuya gönderilmez.

## Gerçek site testi

```powershell
python scripts/site_matrix.py --all
python scripts/site_matrix.py --case aniwatch-nested --timeout 75
```

Liste `tests/site_matrix.json` içinde genişletilir. Testler sırayla çalışır; her sayfanın süre sınırı vardır. Yardımcı tarayıcı gizlidir, CAPTCHA çözülmez ve manuel devam edilmez. Metadata kontrolü yapılır, tam video indirilmez. Sonuç `build/site-matrix-latest.json` dosyasına yazılır. Paylaşılabilir sonuç yalnız izin verilen alanlardan oluşturulur; ham alt süreç çıktısı ve geçici probe dosyaları rapora taşınmaz.

Sonuçların anlamı:

- `automatic`: gizli tarayıcı ile kaynak çözüldü ve metadata okunabildi.
- `interaction_required`: kullanıcının görünür tarayıcıda devam etmesi gerekiyor.
- `failed`: süre sınırı, desteklenmeyen oynatıcı veya erişim/metadata hatası.
- `full_download: not_tested`: videonun sonuna kadar eksiksiz indirilebildiği bu testte doğrulanmadı.

## İlk ölçüm — 18 Ekim 2026

| Örnek | Sonuç | Süre | Okunan kalite |
|---|---|---|---|
| Aniwatch, iç içe bölüm oynatıcısı | Otomatik | 12,8 sn | 1080p |
| FullHDFilmizlesene, film oynatıcısı | Otomatik | 25,0 sn | 360p–2160p |
| HDFilmcehennemi, film oynatıcısı | Başarısız: kaynak bulunamadı | 22,0 sn | — |

Tarih ve yapılandırılmış sonuçlar `tests/site_matrix_baseline.json` içindedir. Bu üç örnek, 20–30 farklı sayfalık saha matrisinin **başlangıç kümesidir**; genel başarı yüzdesi veya %90 destek iddiası değildir. Daha fazla farklı oynatıcı/site ve aynı sitede farklı içerikler eklenmelidir. HDFilm örneğinin ilk başarısız sonucu karşılaştırma için korunmuştur.

### Sonraki ölçüm: lazy iframe desteği

Sonradan iframe yükleyen oynatma kapağı desteğiyle önceki HDFilm bağlantısı ve yeni Esaretin Bedeli bağlantısı da otomatik çözülmüştür. Güncel dört sayfanın tamamında metadata ve bir HLS parçasından 16 KiB veri okunabilmiştir. Bu sonuçların tam indirme anlamına gelmediği raporda ayrıca belirtilir. Ayrıntılar [LAZY_PLAYERS_AND_SOURCE_VALIDATION.md](../architecture/LAZY_PLAYERS_AND_SOURCE_VALIDATION.md), yapılandırılmış sonuçlar `tests/site_matrix_after_lazy.json` içindedir.

Yerel sentetik testler; HTML5/JW Player/Video.js, çapraz kökenli iç çerçeveler, HLS/DASH/blob, doğrulama ve DRM'de otomasyonun durması, belirsiz oynatıcı seçimi, 429 sonrası eksiksiz devam, gerçek çözünürlük/ses çıktısı ve pencere temizliğini ayrıca kapsar. Bunlar saha örnek sayısını yapay olarak artırmak için kullanılmaz.

## Kontroller

```powershell
python -m unittest discover -s tests -p test_diagnostics.py
node tests/test_diagnostics_ui.cjs
python tests/test_fragment_recovery.py
python -m unittest discover -s tests -p test_site_local_download.py
python tests/verify_generic_native.py
```
