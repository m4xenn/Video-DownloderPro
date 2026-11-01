# Video Downloader Pro 1.2.0 — Studio arayüzü ve debug

17 Ekim 2026. Bu sürüm, mevcut indirme özelliklerini koruyan kapsamlı görünüm yenilemesidir. Yeni indirme özelliği eklenmedi.

## Tasarım

Apple'ın Liquid Glass yaklaşımındaki katman, yarı saydamlık, ışık yansıması ve içerik hiyerarşisinden esinlenildi. Bu, Windows/WebView2 üzerinde CSS ile hazırlanmış bir yorumdur; Apple'ın yerel Liquid Glass API'si değildir.

Referans: [Apple — Meet Liquid Glass](https://developer.apple.com/videos/play/wwdc2025/219/).

- Ana ekran bağlantı/çıktı tercihleri ve kuyruk olarak iki bölüme ayrıldı. Küçük pencerede bölümler alt alta geçer.
- Araçlar tek bir cam kapsülde toplandı; uygulama işareti, boş kuyruk durumu, sayaç ve tipografi yeniden tasarlandı.
- Koyu lacivert ve açık buz mavisi temalar aynı renk sistemini kullanır. Cam katmanlarında sabit gradyanlar, ince kenar yansımaları ve kontrollü blur vardır. Sürekli animasyon/arka plan çizim döngüsü yoktur.
- Ayarlar, playlist, geçmiş, tekrarlanan indirme, format bilgisi ve güncelleme pencereleri ortak yüzey/buton düzenine geçirildi.
- Font Awesome ve kullanılan 10 bayrak yerel dosyalara alındı; lisansları `src/static/vendor` içindedir. Google Fonts isteği kaldırıldı, Windows sistem yazı tipi kullanılır. Arayüzün çizilmesi artık CDN erişimine bağlı değildir.
- Klavye odağı, özel menülerde Enter/ok tuşları/Escape, pencerelerde Tab döngüsü/Escape/önceki odağa dönüş eklendi. Azaltılmış hareket ve yüksek kontrast tercihleri için stiller vardır.

## Bulunan ve düzeltilen hatalar

1. Dil değişimi seçilen kaliteyi ilk seçeneğe döndürüyordu. Geçerli kalite artık korunur; format değişimi gerekiyorsa ilgili ilk seçeneğe geçer.
2. Otomatik sistem teması ilk açılışta kullanıcı tercihi gibi kaydediliyordu. Yalnız kullanıcının tema düğmesine basması kalıcı tercih oluşturur. Koyu modda güneş, açık modda ay simgesi gösterilir.
3. Ana ekran mevcut hedef klasörü göstermek yerine her yenilemede klasör seçilmesini istiyordu. Oturumdaki hedef artık gösterilir. Bu, uygulama kapatıldıktan sonra hedef seçimini kalıcılaştıran yeni bir özellik değildir.
4. Son kuyruk öğesi kaldırıldığında geri yükleme bildirimi ve özet eski halde kalabiliyordu. Kaldırma sonrası durum yeniden okunur; sayaç ve boş kuyruk ekranı güncellenir.
5. Aktif/duraklatılmış/hatalı bir bağlantı tekrar eklenerek aynı satırın geçici olarak değiştirilmesi önlendi; mevcut devam/tekrar dene düğmeleri kullanılabilir.
6. `max` kalite kodu geçmişte ham olarak görünüyordu. “En yüksek kalite” olarak gösterilir.
7. Kapak görseli bulunmadığında veya yüklenemediğinde yerel video simgesi gösterilir.
8. Bildirim mesajları HTML olarak işleniyordu. Artık metin olarak yazılır; hata/başlık içeriği HTML çalıştıramaz.
9. `/get-info` bozuk JSON, yanlış veri türleri ve geçersiz bağlantılarda 400 JSON yanıtı verir; HTTP/HTTPS dışındaki bağlantılar çıkarıcıya gönderilmez. Metadata ağ isteğine 15 saniyelik soket zaman aşımı ve sınırlı extractor denemeleri eklendi; sertifika doğrulamasını kapatan eski seçenek kaldırıldı.
10. Küçük pencerelerde diyalog içerikleri ve alt düğmeler taşabiliyordu. İçerik kaydırılır; pencereler ekran sınırında kalır.
11. İç içe checkbox etiketleri düzeltildi; araç ve satır düğmelerine erişilebilir isimler verildi. Sayfayı bloke eden geliştirme hata alert'i kaldırıldı; hatalar konsolda kalır.
12. Ayarlardaki “otomatik sıkıştırma” kontrolünün indirme kodunda karşılığı yoktu. Çalışmayan kontrol görünümden çıkarıldı; sıkıştırma eklenmedi. Kaydedilen yeni ayarlar bu eski bayrağı kapalı tutar.

## Manuel test kapsamı

Uygulamanın gerçek Flask arayüzü Chromium tabanlı tarayıcıda açıldı. `tests/preview_library.py` geçici SQLite, hedef klasör ve ayar dosyaları kullanır; kullanıcının gerçek kuyruk/geçmiş/ayarları değiştirilmedi. Playlist satırları ve kayıp dosya örneği sentetiktir; aşağıdaki MP4 indirmesi gerçek yt-dlp/FFmpeg işlemi kullanır.

| Senaryo | Gözlenen sonuç |
| --- | --- |
| Boş kuyruk | Sayaç 0, boş durum ve geçmiş bağlantısı doğru |
| Enter ile bağlantı ekleme | Yükleme durumu kapanıyor; başlık kuyruğa geliyor |
| Yerel 4 saniyelik test videosu | UI üzerinden MP4 indirildi, %100 tamamlandı; gerçek çıktı yaklaşık 409,7 KB |
| İndirme geçmişi | Yeni başarı gerçek dosya yolu/boyutu ile kaydoldu |
| Tekrar indir | Mevcut dosya uyarısı açıldı; Escape indirmeden geri döndü |
| İç içe pencereler | Üst pencere kapanınca önceki düğmeye odak döndü |
| Tab ile gezinme | Geçmiş penceresinin son düğmesinden ilk düğmeye döndü |
| Kalite ve dil | 720p seçildi; İngilizceye ve Türkçeye geçişte korundu |
| Koyu/açık tema | Ana ekran ve pencereler iki temada incelendi |
| Ayar kaydetme | Yalıtılmış dosyada manuel 2 ve 8 Mbps kaydedildi; yeniden yüklemede korundu |
| Geçersiz ayar | -1 Mbps reddedildi; ayar penceresi açık kaldı ve hata gösterildi |
| Önceki oturumdan iş | Duraklatılmış örnek iş, yüzde ve geri yükleme bildirimi gösterildi |
| Taslak ve duraklatılmış işi kaldırma | Sayaç 2→1→0; geri yükleme bildirimi ve özet kapandı |
| Playlist seçimi | 3 kullanılabilir, 1 kapalı öğe; seçim temizleme/arama/sonuç seçme ile 1/3 seçili |
| Kayıp geçmiş dosyası | Aç/klasör düğmeleri kapalı, tekrar indir açık |
| Geçersiz URL | Hata bildirimi; giriş ve ekleme düğmesi yeniden kullanılabilir |
| 900×710 içerik alanı | İki sütun, ana düğme ve alt bilgi incelendi |
| 600×460 içerik alanı | Tek sütun ve kaydırılabilir ayar/playlist pencereleri incelendi |
| Bileşen güncelleme | Kontrol penceresi açıldı; boş/undefined başlık oluşmadı |

Görseller `tests/studio-dark.png`, `studio-light.png`, `studio-playlist.png`, `studio-history.png` içindedir.

## Otomatik doğrulama

- Önceki 120 Python testi yeniden geçti: 30 scheduler, 25 kuyruk/geçmiş, 15 audit, 26 uygulama güncelleme, 20 bileşen, 1 gerçek MP4/MP3 ve 3 HTTP/HLS testi.
- Metadata hata sınırları ve yerel arayüz dosyaları için 4 yeni Python testi geçti: toplam **124**.
- Önceki 27 JavaScript kontrolüne kalite, tema, güvenli bildirim ve düğme sıfırlama için 7 kontrol eklendi: toplam **34**.
- Gerçek yerel MP4/MP3 çıktıları FFprobe ile doğrulandı. Aynı içeriği ikinci kez indirirken `(1)` adının ve geçmişin korunduğu kontrol edildi.
- İki HTTP aktarımı toplam 400000 baytı ortak 100000 bayt/s sınırıyla yaklaşık 4,5 saniyede tamamladı. HLS'nin 5 parçası 3 parça paralelliğiyle yaklaşık 6,4 saniyede işlendi. Duraklat/devam testi geçti.

Yeni hedefli kontroller:

```powershell
python -m unittest discover -s tests -p test_studio.py -v
node tests/test_studio_ui.cjs
python tests/preview_library.py --empty
```

## Kullanıcının son kabul kontrolü

Eski uygulamayı kapatıp `releases/v1.2.0/VideoDownloaderPro_Setup.exe` ile yükselt. Önce kısa ve izinli bir içerik indir. Ardından playlist, duraklat/devam, uygulamayı kapatıp yeniden açma, geçmiş ve aynı videoyu tekrar indirme akışlarını dene. Ayarlardan 8 Mbps sınırını kontrol edebilirsin; 0 sınırsızdır.

Windows kurulum sihirbazı, işletim sisteminin klasör seçicisi/dosya açma pencereleri ve masaüstü bildirimleri bu tarayıcı üzerinden manuel olarak sürülmedi. Kurulum paketi derlendi; paket içindeki sürüm, yeni statik dosyalar ve SHA256 doğrulanır. Native WebView2, ekran ölçeklendirmesi ve dış platformların güncel davranışı için kurulu uygulamada son kabul testi gerekir. Canlı internetten uygulama/bileşen kurulumu yapılmadı, GitHub'a sürüm yayınlanmadı.
