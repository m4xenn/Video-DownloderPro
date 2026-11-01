# Video Downloader Pro 1.2.1

İndirme profili eklenmedi. Bu sürüm toplu bağlantı ekleme, kaynağa özel kalite seçimi ve FFmpeg doğrulama açıklamasını içerir.

## Toplu bağlantılar

Bağlantı alanına birden fazla HTTP/HTTPS bağlantısını satır satır veya boşlukla ayırarak yapıştır. Enter veya + düğmesi bunları kuyruğa ekler. Shift+Enter yeni satır açar. Alan içeriğe göre büyür.

Bir seferde ve bekleyen bağlantı kuyruğunda en fazla 500 bağlantı desteklenir. Metadata istekleri en fazla üçlü gruplarla yürütülür; bu, medya indirmelerinin otomatik eşzamanlılık yönetiminden ayrıdır. Kontrol sırasında yeni ekleme ve indirmeyi başlatma bekletilir. Bir bağlantının hatası diğerlerini durdurmaz.

İşlem bitince eklenen/tekrar olduğu için atlanan/eklenemeyen sayıları görünür. Geçersiz veya incelenemeyen bağlantılar girişte bırakılır. Aynı yapıştırmadaki tekrarlar ile kuyrukta bekleyen/çalışan/duraklatılmış/hatalı aynı URL atlanır. Daha önce tamamlanmış içeriklerin tekrar indirme uyarısı geçmiş üzerinden çalışmaya devam eder.

## Kalite

- Varsayılan **Otomatik · En yüksek kalite**. Ortak 1080p sınırı yoktur. Her video kendi kaynağından yeniden incelenip en yüksek çözünürlük/FPS önceliğiyle seçilir; uygun ses akışı ayrıca alınabilir ve FFmpeg ile birleştirilir. Kaynakta bulunmayan kalite üretilmez/yükseltilmez.
- Birden fazla bağlantı veya playlist seçildiğinde video kalite menüsü otomatik en yüksek seçeneğini sunar. Farklı videoların çözünürlükleri birbirinden bağımsızdır.
- Kuyrukta indirilmeyi bekleyen tek video varsa, kaynağın gerçekten sunduğu çözünürlük/FPS seçenekleri gösterilir. Aynı çözünürlük/FPS'deki kodek varyantları tek seçenekte birleştirilir. DRM ve storyboard/görüntü formatları listeye alınmaz.
- Kaynak ayrıntılı format bilgisi vermiyorsa yalnız otomatik seçenek gösterilir. Genel listeden tahmini 4K/8K seçeneği sunulmaz.
- Boyut yalnız kaynak tam sesli/video akışının boyutunu bildirdiğinde tahmini olarak seçeneğe eklenir. Video-only akış boyutu, ses eklenmiş nihai dosya boyutu gibi gösterilmez. MP4 dönüşümü gerçek çıktı boyutunu değiştirebilir.
- Yenile simgesi kaynak seçeneklerini tekrar alır. Önbellek yaklaşık 15 dakika geçerlidir; süresi geçmiş bir özel seçimde sunucu yenileme ister. Açılışta geri yüklenen tek bekleyen bağlantının seçenekleri yeniden sorgulanır.
- Özel kalite yalnız incelenen tek video için kabul edilir; istemci keyfi yt-dlp format ifadesi gönderemez. Kalite seçimi kuyruk/yeniden deneme/geçmişte saklanır. Seçilen çözünürlük kaynaktan kalkarsa daha yüksek bir kaliteye sessiz geçmek yerine hata alınabilir.
- Ses indirme menüsündeki MP3/WAV/M4A/Opus, kaynak sesinin dönüştürüleceği çıktı biçimleridir.

Format filtreleri için birincil kaynak: [yt-dlp format selection](https://github.com/yt-dlp/yt-dlp#format-selection).

## FFmpeg açıklaması

Mevcut EXE çalışıyor, FFprobe da var ancak yönetilen dağıtımın SHA-256 kaydı yoksa:

- “Güncelleme mevcut” yerine **Kurulum doğrulanamadı** gösterilir.
- Daha yeni FFmpeg bulunduğu iddia edilmez.
- Aynı derlemenin tekrar indirilebileceği ve doğrulanmış paketi yeniden kurmanın isteğe bağlı olduğu açıklanır.
- Yalnız bu durum varsa düğme **Doğrulanmış paketi yeniden kur** olur.

Kayıtlı dağıtım hash'i değiştiğinde veya bileşen eksik olduğunda gerçek dağıtım güncelleme/kurulum akışı korunur. Kullanıcının mevcut FFmpeg dosyaları bu çalışma sırasında değiştirilmedi.

## Doğrulama

Toplam 133 hedefli Python testi ve 44 JavaScript kontrolü geçti. Yeni testler; gerçek yt-dlp format seçicisiyle 4K/720p kaynakların bağımsız maksimum seçimi, 1080p 30/60 FPS ayrımı, kesirli FPS, sahte kalite ifadesi, tek videoya ait seçimin toplu/playlist isteklerinde reddi, üç metadata isteği sınırı, kısmi hata, tekrarlar ve FFmpeg doğrulama ayrımını kapsar.

Manuel arayüz testi kişisel ayarlardan/geçmişten ayrı yerel test sunucusunda yapıldı:

1. FFmpeg ile iki çözünürlüklü gerçek HLS kaynak üretildi. Menüde 360p/24 FPS ve 180p/24 FPS göründü.
2. 180p seçilip UI üzerinden indirildi. FFprobe çıktısı **320×180, 24 FPS** olarak doğrulandı.
3. Aynı HLS ve doğrudan MP4 bağlantısı, tekrar eden bağlantı ve geçersiz metinle toplu yapıştırıldı. Sonuç **2 eklendi / 1 tekrar atlandı / 1 eklenemedi**; hatalı metin girişte kaldı.
4. Toplu kalite menüsü yalnız otomatik en yüksek seçeneğini gösterdi. İki dosya indirildi; HLS bu kez **640×360, 24 FPS**, MP4 de **640×360, 24 FPS** çıktı. Önceki 180p dosya korundu.
5. Gerçek bileşen kontrolünde kurulu FFmpeg için yeni doğrulama açıklaması ve isteğe bağlı yeniden kur düğmesi görüldü. FFmpeg paketi indirilmedi.
6. Önceki gerçek MP4/MP3 çıktı, HTTP/HLS toplam hız sınırı ve duraklat/devam testleri tekrar geçti.

Yeni test komutları:

```powershell
python -m unittest discover -s tests -p test_source_quality.py -v
python -m unittest discover -s tests -p test_components.py -v
node tests/test_bulk_quality_ui.cjs
```

Kurulu Windows uygulamasında ve yetkili dış platform içeriklerinde son kabul testi ayrıca yapılmalı. Kaynakların erişim, çerez, bölge ve platform kısıtları kaldırılmaz. Yeni paket `releases/v1.2.1/VideoDownloaderPro_Setup.exe`; GitHub'a otomatik yayımlanmadı.
