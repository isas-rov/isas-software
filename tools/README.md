# ArduSub SITL Parkur Araçları

Bu klasördeki ArduSub araçları, İSAS sualtı aracı hareket parkurunu Windows,
WSL Ubuntu, ArduPilot SITL ve Mission Planner üzerinde geliştirmek ve prova etmek
için kullanılır.

> **Önemli:** Bu yazılımlar yalnızca SITL simülasyonu için hazırlanmıştır.
> Gerçek araçta motorlar, ESC'ler, gövde düzeni, basınç sensörü, konum geri
> bildirimi ve failsafe davranışları doğrulanmadan kullanılmamalıdır.

## Dosyalar

- `sitl_kumanda_kayit.py`: Önerilen etkileşimli kumanda, kayıt ve otonom parkur
  aracı.
- `sitl_gorev_20sn.py`: SITL bağlantısı ve ortak MAVLink yardımcıları. Eski
  süre/RC tabanlı görev denemelerini de içerir.
- `kayitlar/*.json`: Elle oluşturulup `kaydet` komutuyla saklanan hareket
  listeleri.

## Gereksinimler

- Windows 10/11
- WSL 2 ve Ubuntu
- Ubuntu içinde `~/ardupilot` konumuna kurulmuş ArduPilot
- `~/venv-ardupilot` Python sanal ortamı
- Sanal ortamda `pymavlink`
- Mission Planner

Mevcut kurulum için temel Python bağımlılığı:

```bash
source ~/venv-ardupilot/bin/activate
python -m pip install pymavlink
```

## 1. ArduSub SITL'yi Başlatma

Windows PowerShell'de Ubuntu'yu açın:

```powershell
wsl -d Ubuntu
```

Ubuntu terminalinde:

```bash
cd ~/ardupilot
source ~/venv-ardupilot/bin/activate
sim_vehicle.py -v ArduSub --console --map -w
```

Terminalde `MANUAL>` istemi ve ayrı ArduSub, Console ve Map pencereleri
göründüğünde SITL hazırdır. Bu terminal açık tutulmalıdır.

`-w` seçeneği SITL parametrelerini varsayılanlara sıfırlar. Her çalıştırmada
parametreleri korumak isteniyorsa sonraki başlatmalarda `-w` kaldırılmalıdır.

## 2. Mission Planner Bağlantısı

Mission Planner'da bağlantı türü olarak `UDP` seçin ve `CONNECT` düğmesine
basın. Port sorulduğunda:

```text
14550
```

Bağlantı tamamlandığında araç türü `SUBMARINE` görünmelidir.

## 3. Kumanda Programını Başlatma

SITL açık kalırken ayrı bir Windows PowerShell penceresinde:

```powershell
wsl -d Ubuntu -- bash -lc "source ~/venv-ardupilot/bin/activate && python '/mnt/c/Users/kolay/Desktop/İSAS/GitHub-Organization/isas-software/tools/sitl_kumanda_kayit.py'"
```

Başarılı bağlantıda aşağıdaki çıktılar görülür:

```text
Baglandi
Mod: GUIDED
Sanal arac ARMED
GUIDED kontrol hazir
KUMANDA>
```

Komutlar yalnızca `KUMANDA>` istemine yazılmalıdır. PowerShell istemine veya
MAVProxy'nin `MANUAL>` istemine yazılmamalıdır.

## Otonom Parkur

Tam parkuru tek seferde başlatmak için:

```text
otonom
```

Program başlangıçtaki SITL yerel konumunu ve yönünü kaydeder. Ardından:

1. En az 20 saniye düz ilerler.
2. Sağa 90 derece döner.
3. En az 20 saniye düz ilerler.
4. Yaklaşık 1 metre çaplı tam daire yapar.
5. Daireyi kapatıp sağa 90 derece hizalanır.
6. En az 20 saniye düz ilerler.
7. Sağa 90 derece döner.
8. En az 20 saniyelik son bölümle kayıtlı başlangıç konumuna döner.

Başarılı tamamlanma çıktısı:

```text
Otonom parkuru tamamlandi; baslangic hatasi 0.xx m
```

Yerel geliştirme testinde yaklaşık `0.07 m` başlangıç hatası gözlenmiştir. Bu
değer yalnızca ilgili SITL koşuluna aittir ve gerçek araç performansı garantisi
değildir.

## Etkileşimli Komutlar

```text
ileri 20 1600       20 saniye düz ileri hareket
sag 90              Mevcut hedef yöne göre 90 derece sağa dönüş
daire 450 1575      Verilen ileri değerle 450 derece sağ daire
otonom               Konum geri bildirimli tam yarışma parkuru
liste                Bellekteki hareket listesini göster
geri                 Son hareketi listeden sil
temizle              Hareket listesini temizle
kaydet parkur1       Listeyi kayitlar/parkur1.json olarak kaydet
yukle parkur1        Kayıtlı hareket listesini yükle
oynat                Yüklenen/listeye eklenen hareketleri çalıştır
dur                   Araç beklerken GUIDED hız hedefini sıfırla
yardim               Komut listesini göster
cikis                 Nötrle, DISARM et ve programı kapat
```

`ileri` ve `daire` komutlarındaki 1000–2000 aralığı kullanıcıya tanıdık bir
kontrol ölçeğidir. GUIDED kullanımında değer doğrudan bir ESC'ye PWM olarak
gönderilmez; yazılım tarafından hız hedefine çevrilir ve ArduSub motor
karıştırıcısı sanal motor çıkışlarını hesaplar.

## Kayıt Dosyaları

Hareket listeleri şu klasöre JSON olarak yazılır:

```text
tools/kayitlar/
```

Örnek:

```text
kaydet parkur1
yukle parkur1
liste
oynat
```

`otonom` komutu kod içindeki konum geri bildirimli parkuru doğrudan çalıştırır;
otomatik olarak JSON kayıt oluşturmaz.

MAVProxy telemetri kaydı, SITL'nin `~/ardupilot` klasöründen başlatıldığı mevcut
kurulumda genellikle aşağıdaki dosyadadır:

```bash
~/ardupilot/mav.tlog
```

## Durdurma ve Yeniden Başlatma

Parkur bittikten sonra güvenli çıkış:

```text
cikis
```

Otonom hareket devam ederken acil kesme için kumanda terminalinde `Ctrl+C`
kullanılabilir. Program kapanırken GUIDED hız hedefini birkaç kez sıfırlar ve
DISARM komutu gönderir. SITL fiziğinde kalan çok küçük süzülme veya konum
gürültüsü görülebilir.

Temiz bir simülasyon için `MANUAL>` bulunan SITL terminalinde `Ctrl+C` ile
simülasyonu kapatıp ilk bölümdeki komutlarla yeniden başlatın.

## Gerçek Araca Geçiş Sınırları

SITL, sualtında bulunmayan sentetik yerel konum bilgisini sağlar. Bu nedenle
başlangıç noktasına hassas dönüş gerçek araçta aynı haliyle çalışmaz.

Gerçek altı motorlu araçta Raspberry Pi tek tek motor PWM değerleri üretmek
yerine Pixhawk'a ileri hız, yön, dönüş ve derinlik hedefleri göndermelidir.
ArduSub seçilen `FRAME_CONFIG` düzenine göre bu hedefleri Motor 1–6 çıkışlarına
karıştırır.

Gerçek araç denemesinden önce en az şu çalışmalar tamamlanmalıdır:

- Motorların fiziksel konumuna uygun ArduSub frame seçimi
- Pixhawk Motor 1–6 çıkış eşlemesi
- ESC nötr/minimum/maksimum değerlerinin doğrulanması
- Her motorun sıra ve dönüş yönü testi
- IMU ve pusula kalibrasyonu
- Sualtı basınç/derinlik sensörü kurulumu
- DVL, görüntü, akustik sistem veya başka uygun sualtı konum geri bildirimi
- Haberleşme kaybı, sızıntı ve motor acil durdurma failsafe testleri
- Pervaneler sökülüyken bench testi ve ardından bağlı/düşük güçlü su testi

Gerçek araca geçiş ayrı bir donanım yapılandırması ve doğrulama aşaması olarak
ele alınmalıdır.
