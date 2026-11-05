# Uzun kayıt incelemesi — 5 Kasım 2026

**Son durum: düzeltilmiş dört saatlik koşu geçti.** Yeni paket ve kurulum
yeniden üretildi, kabul kontrolleri geçti. Son aday ve kanıtlar
[güncel raporda](ENDURANCE_CANDIDATE_2026-11-05.md). Yayımlanmadı.
Önceki `candidate-final` aşağıdaki düzeltmeyi içermez. Aşağıdaki inceleme,
başarısız ilk koşu ve düzeltme sürecinin tarihsel kaydıdır.

## Eski koşuda doğrulananlar

- Sonuç `build/stability/four-hour/result.json`: yaklaşık 11.294,7 saniye çalışma,
  11.263,803 saniye medya (3 saat 7 dakika 43,8 saniye). Dört saat hedefi tutmadı.
- Dosyada hem video hem ses var. Sonradan yapılan tam decode çıkışı sıfır, ancak
  null muxer 1.462 adet tekrarlı/artan olmayan DTS uyarısı üretti. Dolayısıyla
  “tam kontrol tertemiz geçti” denemez. Kanıt: `full-decode-review.log/.exit`.
- Eski test, ses ve görüntü süreleri farklı kısa MP4'ü sürekli döndürüyordu.
  Bu, test kaynağına döngü sınırlarında zaman damgası sorunu katabilir. Yeni test
  sürekli lavfi ses/görüntü üretir; eski dosyayı yeni testte kullanmaz.
- Testte `public_url` için `MagicMock(return_value=True)` kullanılmıştı. Her
  çağrının geçmişini tutar; uzun koşuda bellek biriktirir. Eski süreç RSS artışı
  uygulamada bellek sızıntısı kanıtı değildir. Yerine çağrı kaydı tutmayan fonksiyon
  kullanıldı. Diğer fixture istisnaları da sadece sahip olduğumuz loopback kaynağa
  ait; üretim bağlantı doğrulaması gevşetilmedi.
- Eski koşu son FFmpeg hata kuyruğunu/bitme nedenini saklamıyordu. Erken bitişi
  başlatan kesin ağ/demuxer olayını geriye dönük kanıtlayamıyoruz.

## Kaynak düzeltmesi

`services/live_recording.py` daha önce FFmpeg'in sıfır çıkış kodunu, oynatılabilir
dosya varsa başarı sayabiliyordu. Oysa bir canlı okuyucu kaynak beklemekten
vazgeçip sıfır koduyla da çıkabilir. Artık süre/manuel bitiş dışında erken çıkışta
seçili HLS akışlarının ENDLIST'i veya DVR'nin doğrulanmış yayın sonu aranıyor.
Doğrulanmazsa kayıt tamamlandı sayılmıyor, `.live.mkv` korunuyor ve mevcut parça
kurtarma akışına aktarılıyor. Otomatik boşluk atlayarak yeni yayın eklenmiyor.

`services/live_completion.py` bitiş doğrulamasını kapsüllüyor. Bitiş bilgisi
alınamazsa başarı varsayılmıyor. FFmpeg hata sonu/çıkış kodu/süre tanılaması sınırlı
bir kuyrukta tutuluyor; kaynak URL'leri kullanıcı hata mesajına eklenmiyor.

## Test düzeltmesi ve tekrar

- Kaynak artık kısa dosya döngüsü yerine sürekli zaman damgalı H264/AAC üretir.
- Kaynak stderr'i sınırlı kuyrukla tüketilir; dolan borunun üreticiyi kilitlemesi
  önlenir. Kaynak çıkış kodu ve kayıt sonu tanılaması rapora yazılır.
- Son “finished” olayı kayıt süresini sıfırlamıyor; son ölçüm korunuyor.
- Gerçek üç dakikalık kayıt ve sıkı tam ses/görüntü decode'u geçti:
  `build/stability/corrected-smoke/result.json`, 179,954 saniye, boş stderr.
  Bu kısa koşu, sonradan eklenen yalnızca hata tanılaması alanından önceki motor
  hash'ini içerir; yeni dört saatlik koşu güncel motoru kullanır.
- Dört bitiş sözleşmesi testi ve gerçek FFmpeg'in beklenmedik sıfır çıkışında
  kısmi dosyanın korunması testi geçti. Gerçek süreç iki saniyede sonlandırılırken
  kayıt yöneticisi 60 saniye bekletilerek erken çıkış sınanır; sahte medya veya
  değiştirilmiş dönüş kodu kullanılmaz. Nihai **607 Python testi geçti**; sıfır
  hata/başarısızlık/atlama. Kanıt:
  `build/stability/endurance-review-regression.json` ve `.log`.
- Yeni dört saatlik koşu: `--minutes 240 --label four-hour-corrected`, oturum
  **32630**, durum `build/stability/four-hour-corrected/result.json`.
  Yedi kaynak hash'i korunmalı; `passed` olmadan dört saat doğrulandı denmemeli.

Yeni kaynak düzeltmesi yayımlanmadı. Eski üretim kurulumu, kullanıcı ayarları ve
eski test dosyaları değiştirilmedi/silinmedi.
