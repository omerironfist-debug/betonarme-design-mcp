# 🏗️ Betonarme Tasarım MCP Sunucusu

**TS 500** (Betonarme Yapıların Tasarım ve Yapım Kuralları) ve **TBDY 2018** (Türkiye Bina Deprem Yönetmeliği) uyumlu betonarme tasarım optimizasyonu için Claude MCP sunucusu.

## ✅ Özellikler

### ✓ TS 500 Desteği
- Dikdörtgen kesit moment kapasitesi hesabı
- Kesme kuvveti ve donatı tasarımı
- Minimum/maksimum donatı oranı kontrolü
- Beton örtü kalınlığı (pas payı) kontrolleri
- Etriye aralığı ve detaylandırma kuralları

### ⚡ TBDY 2018 Desteği
- Deprem tasarım kuvveti hesabı (Sa, Sd, SDS)
- Süneklik düzeyi seçimi (DLS, OLS, HLS)
- Kolon konfinman etriyeleri
- Kritik bölge tanımlaması
- Minimum kolon/kiriş boyutları
- Moment/kesme oranı kontrolleri

### 💰 Optimizasyon
- Maliyeti minimize eden kesit geometrisi
- Güvenlik ve ekonomi dengesi
- Üretim kodlarına uygun standart ölçüler

### 🤖 Claude MCP Entegrasyonu
- Doğal dil komutları ile tasarım
- Otomatik kontrol ve raporlama
- Çok seçenekli tasarımlar arasında karşılaştırma

---

## 📋 Kurulum

### Gereksinimler
- Python 3.8+
- OpenSeesPy (isteğe bağlı, gelişmiş analiz için)

### Adımlar

```bash
# Repository'i klonla
git clone https://github.com/omerironfist-debug/betonarme-design-mcp.git
cd betonarme-design-mcp

# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\\Scripts\\activate  # Windows

# Dependency'leri yükle
pip install -r requirements.txt
```

---

## 🚀 Hızlı Başlangıç

### 1. TS 500 ile Kiriş Tasarımı

```python
from ts500_optimizer import TS500ConcreteDesigner

designer = TS500ConcreteDesigner()

# Tasarım yükleri (kN⋅m, kN)
Md = 200  # Moment
Vd = 80   # Kesme kuvveti

# Optimum kesit
result = designer.optimize_beam_section(Md, Vd, fck='C25', fy='B500C')

print(f"✓ Genişlik: {result['b']} mm")
print(f"✓ Yükseklik: {result['h']} mm")
print(f"✓ Donatı: {result['As']} mm²")
print(f"✓ Moment Kapasitesi: {result['M_cap']:.1f} kN⋅m")
```

### 2. TBDY 2018 ile Deprem Tasarımı

```python
from tbdy_2018_rules import TBDY2018SeismicDesigner

seismic = TBDY2018SeismicDesigner(
    risk_category='Yüksek',
    soil_class='Z2',
    ductility_level='OLS'  # Orta Süneklik
)

# Tasarım spektrumu
T = 0.5  # Periyot (sn)
Sa = seismic.calculate_design_spectrum(T)
print(f"Design Acceleration: {Sa:.3f}g")

# Kolon konfinmanı
column_config = seismic.design_column_confinement(
    D=400,  # mm
    fy=420,  # MPa
    fck=25,  # MPa
    critical_region=True
)
print(f"Etriye: Ø{column_config['bar_diameter']}/{column_config['spacing']}")
```

### 3. MCP Sunucusunu Başlat

```bash
python mcp_server.py
```

Claude'da kullan:
```
@betonarme-mcp tasarla: 200 kN⋅m moment, C25 beton, B500C çelik
@betonarme-mcp deprem: Z2 zemininde 4-katlı okul binası
```

---

## 📚 TS 500 Parametreleri

| Parametre | Min | Max | Birim | Not |
|-----------|-----|-----|-------|-----|
| Beton Sınıfı | C20 | C40 | MPa | Karakteristik dayanım |
| Çelik Sınıfı | B420C | B500C | MPa | Akma dayanımı |
| Donatı Oranı (Kiriş) | 0.15% | 4% | - | TS 500 Tablo |
| Donatı Oranı (Kolon) | 1% | 4% | - | Minimum %1 |
| Pas Payı | 20 | 50 | mm | Ortam sınıfına göre |
| Etriye Aralığı | - | 15d | mm | d = çap |

---

## ⚡ TBDY 2018 Parametreleri

| Parametre | Seçenekler | Not |
|-----------|-----------|-----|
| Risk Kategorisi | Düşük, Orta, Yüksek | Yapının tipi |
| Zemin Sınıfı | Z1, Z2, Z3, Z4 | SPT veya elastik hız |
| Süneklik Düzeyi | DLS, OLS, HLS | Tasarım felsefesi |
| Sahip Olduğu Periyot | T < 0.5s | Dikkat: süneklik azalır |

---

## 🔧 API Referans

### TS500ConcreteDesigner

#### `optimize_beam_section(Md, Vd, fck, fy)`
Kiriş kesitini optimize et

**Parametreler:**
- `Md` (float): Tasarım momenti [kN⋅m]
- `Vd` (float): Tasarım kesme kuvveti [kN]
- `fck` (str): Beton sınıfı ['C20', 'C25', ..., 'C40']
- `fy` (str): Çelik sınıfı ['B420C', 'B500C']

**Döndürür:**
```python
{
    'b': 300,              # Genişlik (mm)
    'h': 450,              # Yükseklik (mm)
    'As': 1500,            # Donatı alanı (mm²)
    'M_cap': 210.5,        # Moment kapasitesi (kN⋅m)
    'cost': 125.3          # Birim maliyet
}
```

#### `calculate_moment_capacity(b, h, As, fck, fy)`
Moment kapasitesini hesapla

#### `calculate_shear_capacity(b, d, Asv, fck)`
Kesme kapasitesini hesapla

### TBDY2018SeismicDesigner

#### `calculate_design_spectrum(T)`
Tasarım spektrumunu hesapla

**Parametreler:**
- `T` (float): Yapı periyodu [sn]

**Döndürür:**
- `Sa` (float): Tasarım hızlandırması [g]

#### `design_column_confinement(D, fy, fck, critical_region)`
Kolon konfinmanı tasarla

**Parametreler:**
- `D` (float): Kolon çapı [mm]
- `fy` (float): Çelik akma dayanımı [MPa]
- `fck` (float): Beton dayanımı [MPa]
- `critical_region` (bool): Kritik bölgede mi

**Döndürür:**
```python
{
    'bar_diameter': 10,    # Etriye çapı (mm)
    'spacing': 80,         # Etriye aralığı (mm)
    'type': 'Spiral'       # Spiral veya dikdörtgen
}
```

#### `check_column_moment_ratio(M, V, fck, fy)`
Moment/kesme oranı kontrolü (TBDY 8.5.5)

---

## 📊 Örnek Projeler

### Örnek 1: 3-Katlı Ofis Binası

Bkz. `examples/basic_beam_design.py`

```bash
python examples/basic_beam_design.py
```

### Örnek 2: Deprem Tasarımı (OLS)

Bkz. `examples/seismic_column_design.py`

```bash
python examples/seismic_column_design.py
```

---

## 🧪 Testler

```bash
pytest tests/
```

---

## 📖 Kaynaklar

- [TS 500-2000](https://www.tse.org.tr/)
- [TBDY 2018](https://tdybdeprem.gov.tr/)
- [OpenSees](https://opensees.berkeley.edu/)
- [Betonarme Tasarım Kodları](https://www.mimarlar.org/)

---

## 📄 Lisans

MIT License — Açık kaynak, akademik ve ticari kullanıma açık.

---

## 🤝 Katkı

Buglar, öneriler, PR'lar hoşgeldiniz!

```bash
git checkout -b feature/yeni-ozellik
git commit -am 'Add: Yeni özellik'
git push origin feature/yeni-ozellik
```

---

## 📞 İletişim

- GitHub Issues
- GitHub Discussions

---

**Made with ❤️ for Turkish Civil Engineers** 🇹🇷
