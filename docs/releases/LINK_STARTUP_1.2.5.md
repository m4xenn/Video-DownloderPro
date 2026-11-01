# Video Downloader Pro 1.2.5

- İmleç hareketini takip eden radial ışık ve kontrol yansımaları kaldırıldı. Sabit yüzey dokusu ve normal hover geri bildirimi korundu.
- Tek bağlantı girişten 550 ms sonra otomatik incelenir. Kuyruğa eklenmeden başlık, süre, mevcut çözünürlük/FPS ve kaynak sağlıyorsa yaklaşık boyut görünür. Bilinmeyen boyut uydurulmaz.
- İncelenen bilgi kısa süreli bellekte tutulur; sıraya eklemede ikinci ağ sorgusu gerekmez. Değiştirilen bağlantıya ait eski yanıt ekrana uygulanmaz. Çoklu bağlantı/playlist en yüksek kalite davranışını korur.
- Paket tek dosya çalıştırma yerine kurulumda açılan bağımlılıklara geçti: her açılışta Python/bileşen dosyalarının geçici klasöre çıkarılması kaldırıldı. Kurulum hâlâ tek EXE olarak dağıtılır. Doğrudan taşınacaksa dist/YoutubePro klasörünün tamamı gerekir.
- multiprocessing.freeze_support uygulama ve webview yüklenmeden önce çalışır.

## Doğrulama
139 Python testi ve 56 JavaScript arayüz kontrolü geçti. Yerel gerçek HLS örneğinde bağlantı yapıştırma, kuyruk boşken 360p/180p listesinin açılması ve 180p seçip doğrudan indirme manuel doğrulandı. FFprobe indirilen dosyada 180p tespit etti. Paketlenmiş şablon, stil/JS kaynakları, sürüm ve Python DLL varlığı kontrol edildi.

Kurulumun gerçek Windows açılış süresi henüz ölçülmedi; kesin saniye veya oran iddiası yoktur. Bu tur TikTok/Instagram üzerinde canlı indirme testi yapılmadı.

## Kullanıcı testi
1. 1.2.5 kurulumunu çalıştırıp uygulamayı açın; imleci gezdirince ışık takip etmemeli.
2. Tek video bağlantısı yapıştırıp + düğmesine basmadan bekleyin. Başlık ve kalite seçeneklerini kontrol edin.
3. Bir çözünürlük seçip doğrudan indirin. İndirilen dosyanın çözünürlüğünü kontrol edin.
4. İki farklı bağlantı yapıştırın: otomatik en yüksek kalite seçeneği kullanılmalı.
5. Uygulamayı tamamen kapatıp yeniden açın; önceki sürümle aynı bilgisayarda açılış süresini karşılaştırın.
