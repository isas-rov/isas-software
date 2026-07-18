# Yazılım Mimarisi

## Süreç Sınırları

1. **Algılama:** Kamera ve sensör verisini zaman damgalı gözleme çevirir.
2. **Görev mantığı:** Görev durum makinesini ve hedefleri yönetir.
3. **Kontrol köprüsü:** Üst seviye hedefleri Pixhawk komutlarına dönüştürür.
4. **Telemetri:** Araç sağlığı, görev durumu ve alarmları su üstüne iletir.
5. **Güvenlik denetimi:** Timeout, sızıntı ve kritik sağlık koşullarında komutları sınırlar.

## Tasarım Kuralları

- Donanım I/O işlemleri `drivers` altında soyutlanır.
- Görev mantığı doğrudan GPIO, seri port veya kamera açmaz.
- Her dış mesajın sürümü ve doğrulaması bulunur.
- Saat ve ağ kesintileri normal hata senaryosu kabul edilir.
- Testlerde gerçek motor çıkışı varsayılan olarak kapalıdır.

## Açık Kararlar

- Ana araç içi süreçler arası iletişim yöntemi
- MAVLink mesaj seti ve heartbeat süreleri
- Görüntü aktarım protokolü ve hedef gecikme
- Konfigürasyon formatı ve cihaz kimliklendirme
