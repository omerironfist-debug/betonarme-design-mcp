"""
TBDY 2018 - Türkiye Bina Deprem Yönetmeliği
Deprem Tasarım Kuralları
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from enum import Enum


class RiskCategory(Enum):
    """Bina Önem Katsayısı (TBDY 2.1)"""
    LOW = 0.8      # IV. Kategori (Çiftçi evleri, vb.)
    MEDIUM = 1.0   # III. Kategori (Konutlar, ofisler)
    HIGH = 1.2     # II. Kategori (Hastaneler, itfaiyeler)
    CRITICAL = 1.4 # I. Kategori (Kritik yapılar)


class SoilClass(Enum):
    """Zemin Sınıfı (TBDY 3.1)"""
    Z1 = 'Z1'  # Vs,30 > 1500 m/s
    Z2 = 'Z2'  # 700 < Vs,30 ≤ 1500 m/s
    Z3 = 'Z3'  # 350 < Vs,30 ≤ 700 m/s
    Z4 = 'Z4'  # Vs,30 ≤ 350 m/s


class DuctilityLevel(Enum):
    """Süneklik Düzeyi (TBDY 8.1)"""
    DLS = 'DLS'  # Düşük Süneklik Düzeyi
    OLS = 'OLS'  # Orta Süneklik Düzeyi
    HLS = 'HLS'  # Yüksek Süneklik Düzeyi


@dataclass
class TBDYDesignSpectrum:
    """TBDY Tasarım Spektrumu Parametreleri"""
    
    # Spektrum şekil faktörleri (Tablo 3.1-3.3)
    soil_params = {
        'Z1': {'TB': 0.15, 'TD': 2.5, 'DS': 0.40},
        'Z2': {'TB': 0.15, 'TD': 2.5, 'DS': 0.60},
        'Z3': {'TB': 0.20, 'TD': 3.0, 'DS': 0.80},
        'Z4': {'TB': 0.30, 'TD': 4.0, 'DS': 1.30},
    }
    
    # Süneklik düzeyine göre R faktörü (Tablo 8.1)
    R_factors = {
        'DLS': {'frame': 2.0, 'wall': 1.5},
        'OLS': {'frame': 6.0, 'wall': 4.5},
        'HLS': {'frame': 8.0, 'wall': 6.5},
    }


class TBDY2018SeismicDesigner:
    """TBDY 2018 deprem tasarım kuralları"""
    
    def __init__(self, 
                 risk_category: str = 'HIGH',
                 soil_class: str = 'Z2',
                 ductility_level: str = 'OLS',
                 Sds: float = 0.4):
        """
        Deprem tasarımcı başlat
        
        Args:
            risk_category: Önem kategorisi
            soil_class: Zemin sınıfı
            ductility_level: Süneklik düzeyi
            Sds: Tasarım spektrum ivmesi (g) - güvenlik analizi için
        """
        self.risk_cat = RiskCategory[risk_category].value
        self.soil_class = soil_class
        self.ductility_level = ductility_level
        self.Sds = Sds
        self.spectrum = TBDYDesignSpectrum()
    
    def calculate_design_spectrum(self, T: float) -> float:
        """
        TBDY Tasarım Spektrumunu hesapla (Bölüm 3)
        
        Args:
            T: Yapı periyodu (sn)
        
        Returns:
            Tasarım hızlandırması Sa (g)
        """
        soil = self.spectrum.soil_params[self.soil_class]
        TB = soil['TB']
        TD = soil['TD']
        SDS = soil['DS'] * self.Sds / 0.4  # Normalize
        SDI = SDS / 2.5  # Tasarım deplaşmanı ivmesi
        
        # Spektrum bölgeleri
        if T < TB:
            # 0 < T < TB
            Sa = SDS * (0.4 + 0.6 * T / TB)
        elif TB <= T <= TD:
            # TB ≤ T ≤ TD
            Sa = SDS
        else:
            # T > TD
            Sa = SDS * (TD / T)
        
        return Sa
    
    def calculate_seismic_force(self,
                               W: float,
                               T: float,
                               system_type: str = 'frame') -> float:
        """
        Tasarım deprem kuvvetini hesapla (TBDY 4.2)
        
        Args:
            W: Bina ağırlığı (kN)
            T: Periyot (sn)
            system_type: Taşıyıcı sistem tipi ['frame', 'wall']
        
        Returns:
            Tasarım deprem kuvveti (kN)
        """
        Sa = self.calculate_design_spectrum(T)
        R = self.spectrum.R_factors[self.ductility_level][system_type]
        
        # Tasarım deprem kuvveti
        V = (Sa / R) * W * self.risk_cat
        
        return V
    
    def design_column_confinement(self,
                                 D: float,
                                 fy: float,
                                 fck: float,
                                 critical_region: bool = True) -> Dict:
        """
        Kolon konfinman etriyeleri tasarla (TBDY 8.5)
        
        Args:
            D: Kolon çapı (mm)
            fy: Çelik akma dayanımı (MPa)
            fck: Beton dayanımı (MPa)
            critical_region: Kritik bölgede mi
        
        Returns:
            Konfinman tasarımı: {'diameter': mm, 'spacing': mm, 'type': str, ...}
        """
        
        # TBDY 8.5.5: Konfinman etriyeleri
        if self.ductility_level == 'DLS':
            # Düşük süneklik
            min_diameter = 10
            max_spacing = D / 2  # 150 mm max
            
        elif self.ductility_level == 'OLS':
            # Orta süneklik
            min_diameter = 10
            if critical_region:
                max_spacing = min(D / 3, 100)  # Kritik bölgede sıkı
            else:
                max_spacing = D / 2
            
        else:  # HLS
            # Yüksek süneklik
            min_diameter = 12
            if critical_region:
                max_spacing = min(D / 4, 80)
            else:
                max_spacing = D / 3
        
        # Etriye çevresi yüzde oranı
        if critical_region:
            # TBDY 8.5.5 - Kritik bölgede spiral etriye
            rho_s = 0.12 * (fck / fy)
        else:
            rho_s = 0.08 * (fck / fy)
        
        # Spiral çeliğin toplam alanı: As = rho_s * Ac / 4
        # Ac = π * (D/2)² = π * D² / 4
        # As = rho_s * π * D² / 16
        
        # Periyot kontrolü
        Ac = np.pi * (D / 2) ** 2
        As_required = rho_s * Ac / 4
        
        # Etriye: Ø10, Ø12, Ø14
        bar_diameters = [10, 12, 14]
        for bar_d in bar_diameters:
            bar_area = np.pi * (bar_d / 2) ** 2
            spacing = bar_area * Ac / (As_required * 4)  # Spiralde periyot
            
            if spacing <= max_spacing:
                return {
                    'bar_diameter': bar_d,
                    'spacing': int(np.round(spacing / 5) * 5),  # 5mm katı
                    'type': 'Spiral' if critical_region else 'Rectangular',
                    'ratio': rho_s * 100,
                    'region': 'Critical' if critical_region else 'Normal',
                    'ductility': self.ductility_level
                }
        
        # Fallback
        return {
            'bar_diameter': min_diameter,
            'spacing': int(max_spacing),
            'type': 'Spiral',
            'ratio': rho_s * 100,
            'region': 'Critical' if critical_region else 'Normal',
            'ductility': self.ductility_level
        }
    
    def check_column_moment_ratio(self,
                                  M: float,
                                  V: float,
                                  fck: float,
                                  fy: float) -> Tuple[bool, str]:
        """
        Kolon moment/kesme oranı kontrolü (TBDY 8.5.5)
        
        Args:
            M: Moment (kN⋅m)
            V: Kesme kuvveti (kN)
            fck: Beton dayanımı (MPa)
            fy: Çelik dayanımı (MPa)
        
        Returns:
            (ok: bool, message: str)
        """
        if V <= 0:
            return False, "Kesme kuvveti > 0 olmalı"
        
        ratio = M / V  # mm
        
        # TBDY 8.5.5: Moment/Kesme oranı ≥ h (kolon yüksekliği)
        # Burada yaklaşık kontrol: ratio ≥ 500 mm (tipik kolon yüksekliği)
        
        min_ratio = 500  # mm (tipik)
        
        if ratio >= min_ratio:
            return True, f"✓ M/V = {ratio:.0f} mm ≥ {min_ratio} mm (OK)"
        else:
            return False, f"✗ M/V = {ratio:.0f} mm < {min_ratio} mm (FAIL)"
    
    def calculate_critical_region_length(self, h_col: float) -> float:
        """
        Kritik bölge uzunluğu (TBDY 8.5.1)
        
        Args:
            h_col: Kolon yüksekliği (mm)
        
        Returns:
            Kritik bölge uzunluğu (mm)
        """
        # TBDY 8.5.1: Lc = max(h_col, 600 mm)
        return max(h_col, 600)
    
    def get_minimum_column_dimension(self) -> float:
        """
        Minimum kolon boyutu (TBDY 8.5.2)
        
        Returns:
            Minimum boyut (mm)
        """
        if self.ductility_level == 'DLS':
            return 250
        elif self.ductility_level == 'OLS':
            return 300
        else:  # HLS
            return 350
    
    def get_minimum_beam_dimension(self) -> float:
        """
        Minimum kiriş boyutu (TBDY 8.4)
        
        Returns:
            Minimum boyut (mm)
        """
        if self.ductility_level == 'DLS':
            return 250
        elif self.ductility_level == 'OLS':
            return 300
        else:  # HLS
            return 350
    
    def generate_design_report(self,
                              building_name: str,
                              num_stories: int,
                              height: float) -> str:
        """
        Tasarım raporu oluştur
        
        Args:
            building_name: Bina adı
            num_stories: Kat sayısı
            height: Toplam yükseklik (m)
        
        Returns:
            Rapor metni
        """
        report = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║     TBDY 2018 DEPREM TASARIM RAPORU                                      ║
╚═══════════════════════════════════════════════════════════════════════════╝

Bina Adı: {building_name}
Kat Sayısı: {num_stories}
Yükseklik: {height} m

─────── TASARIM PARAMETRELERI ───────

Önem Kategorisi: {self.risk_cat}
Zemin Sınıfı: {self.soil_class}
Süneklik Düzeyi: {self.ductility_level}
Tasarım Spektrum İvmesi (SDS): {self.Sds:.3f}g

─────── KURALLAR ───────

• Minimum Kolon Boyutu: {self.get_minimum_column_dimension()} mm
• Minimum Kiriş Boyutu: {self.get_minimum_beam_dimension()} mm
• Kritik Bölge Uzunluğu: {self.calculate_critical_region_length(3000 * num_stories / 1000):.0f} mm

─────── KONFINMAN ETRİYESİ ───────

Kritik Bölge (Kolon Başı/Ayağı):
"""
        confinement = self.design_column_confinement(D=400, fy=420, fck=25, critical_region=True)
        report += f"  • Çap: Ø{confinement['bar_diameter']} mm\n"
        report += f"  • Aralık: {confinement['spacing']} mm\n"
        report += f"  • Tip: {confinement['type']}\n"
        
        report += "\nNormal Bölge (Kolon Gövdesi):\n"
        confinement_normal = self.design_column_confinement(D=400, fy=420, fck=25, critical_region=False)
        report += f"  • Çap: Ø{confinement_normal['bar_diameter']} mm\n"
        report += f"  • Aralık: {confinement_normal['spacing']} mm\n"
        
        report += "\n" + "="*70 + "\n"
        
        return report
