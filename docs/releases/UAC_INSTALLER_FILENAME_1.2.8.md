# 1.2.8 — Güncelleme kurulum dosyasının adı

İndirilen kurulum paketi artık updates/<SHA-256>/VideoDownloaderPro_Setup.exe yolunda tutulur. Doğrulama kodu dosya adı yerine klasör adındadır. Her yayının önbelleği ayrı kalır; indirme sonu ve kurulum öncesi SHA-256 kontrolleri korunur. Kurulumun çalışma klasörü dosyanın bulunduğu klasördür.

26 Python güncelleyici testi ve 5 arayüz kontrolü geçti. Dosya adı, hash klasörü, bozuk dosyanın reddedilmesi ve ShellExecute çağrısı doğrulandı. Gerçek UAC penceresi etkileşimli olarak çalıştırılmadı.

Bu düzeltme 1.2.8 içindeki güncelleyiciye uygulanır. 1.2.7 ve öncesindeki güncelleyiciyle 1.2.8 indirilirse eski uzun ad bir kez daha görülebilir. 1.2.8 sonrasındaki indirmelerde sade dosya adı kullanılır. Güncel kurulumu elle indirmek de sade dosya adı sağlar.

Dijital imza eklenmedi; Yayıncı: Bilinmiyor bildirimi bu değişiklikten bağımsızdır.

Ek düzeltme: Windows indirme tamamlandı bildiriminde NIIF_USER ile paketlenmiş uygulama logosu kullanılır. Logonun Windows LoadImage ile 32x32 yüklenmesi ve 4 bildirim testi doğrulandı. Bildirim ömrü sonunda pencere sahibi iş parçacığına WM_CLOSE gönderilir; kaynaklar temizlenir. Gerçek bildirimin görünümü bu ortamda görsel olarak doğrulanmadı.
