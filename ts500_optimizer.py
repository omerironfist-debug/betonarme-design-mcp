"""
TS 500 Betonarme Tasarım Optimizatörü
Türkiye Betonarme Tasarım Standardı (TS 500-2000)
"""

import numpy as np
from scipy.optimize import minimize
from dataclasses import dataclass
from typing import Optional, Dict, Tuple


@dataclass
class TS500Constants:
    """TS 500 sabitleri"""
    # Güvenlik katsayıları
    gamma_c: float = 1.5      # Beton
    gamma_s: float = 1.15     # Çelik
    gamma_g: float = 1.35     # Daimi yük
    gamma_q: float = 1.50     # Hareketli yük
    
    # Malzeme dayanımları (MPa)
    concrete_classes = {
        'C20': 20, 'C25': 25, 'C30': 30, 'C35': 35, 'C40': 40
    }
    steel_classes = {
        'B420C': 420, 'B500C': 500
    }
    
    # Donatı oranı sınırları (%)
    rho_min_beam = 0.15
    rho_min_column = 1.0
    rho_max = 4.0
    
    # Pas payı (mm)
    cover_exterior = 25
    cover_interior = 20


class TS500ConcreteDesigner:
    """TS 500 standardına uygun betonarme tasarımcı"""
    
    def __init__(self):
        self.const = TS500Constants()
        self.concrete_cost_per_m3 = 800  # TL
        self.steel_cost_per_kg = 35      # TL
    
    def calculate_moment_capacity(self, 
                                  b: float, 
                                  h: float, 
                                  As: float, 
                                  fck: str, 
                                  fy: str) -> Optional[float]:
        """
        Dikdörtgen kesit moment taşıma kapasitesini hesapla (TS 500)
        
        Args:
            b: Kiriş genişliği (mm)
            h: Kiriş yüksekliği (mm)
            As: Donatı alanı (mm²)
            fck: Beton karakteristik dayanımı ['C20', 'C25', ...]
            fy: Çelik akma dayanımı ['B420C', 'B500C']
        
        Returns:
            Moment kapasitesi (kN⋅m) veya None
        """
        fck_val = self.const.concrete_classes.get(fck)
        fy_val = self.const.steel_classes.get(fy)
        
        if not fck_val or not fy_val:
            return None
        
        # Tasarım dayanımları
        fcd = fck_val / self.const.gamma_c
        fyd = fy_val / self.const.gamma_s
        
        # Donatı oranı
        rho = (As / (b * h)) * 100  # %
        
        # Max donatı kontrolü
        if rho > self.const.rho_max:
            return None
        
        # Etkili yükseklik (pas payı + çap)
        d = h - 40
        
        # Moment kapasitesi (yaklaşık formül)
        # M = As * fyd * d * (1 - 0.59*rho*fyd/fcd)
        moment = As * fyd * d * (1 - 0.59 * rho * fyd / (100 * fcd)) / 1e6
        
        return max(0, moment)  # kN⋅m
    
    def calculate_shear_capacity(self, 
                                b: float, 
                                d: float, 
                                Asv: float, 
                                fck: str,
                                spacing: float = 100) -> float:
        """
        Kesme kapasitesi (TS 500 Tablo 3.5)
        
        Args:
            b: Kesit genişliği (mm)
            d: Etkili yükseklik (mm)
            Asv: Etriye toplam alanı (mm²)
            fck: Beton sınıfı
            spacing: Etriye aralığı (mm)
        
        Returns:
            Kesme kapasitesi (kN)
        """
        fck_val = self.const.concrete_classes.get(fck, 25)
        fcd = fck_val / self.const.gamma_c
        
        # TS 500 Tablo 3.5 - Beton kesme dayanımı
        tau_c = 0.25 * np.sqrt(fck_val)
        
        # Beton tarafından karşılanan kesme
        V_c = tau_c * b * d / 1e3  # kN
        
        # Etriye tarafından karşılanan kesme
        if Asv > 0 and spacing > 0:
            fyw = 420  # Etriye çeliği dayanımı (MPa)
            V_s = (Asv * fyw * d) / (spacing * self.const.gamma_s * 1e3)
        else:
            V_s = 0
        
        return V_c + V_s
    
    def check_minimum_reinforcement(self, 
                                   b: float, 
                                   h: float, 
                                   As: float,
                                   element_type: str = 'beam') -> Tuple[bool, float]:
        """
        Minimum donatı kontrolü
        
        Args:
            b, h: Kesit boyutları (mm)
            As: Donatı alanı (mm²)
            element_type: 'beam' veya 'column'
        
        Returns:
            (pass: bool, minimum_As: float)
        """
        rho_min = self.const.rho_min_beam if element_type == 'beam' else self.const.rho_min_column
        
        As_min = (rho_min / 100) * b * h
        
        return As >= As_min, As_min
    
    def optimize_beam_section(self, 
                             Md: float, 
                             Vd: float,
                             fck: str = 'C25',
                             fy: str = 'B500C') -> Optional[Dict]:
        """
        Kiriş kesitini maliyeti minimize ederek optimize et
        
        Args:
            Md: Tasarım momenti (kN⋅m)
            Vd: Tasarım kesme kuvveti (kN)
            fck: Beton sınıfı
            fy: Çelik sınıfı
        
        Returns:
            Optimum tasarım: {'b': mm, 'h': mm, 'As': mm², 'cost': TL/m, ...}
        """
        fck_val = self.const.concrete_classes.get(fck, 25)
        fy_val = self.const.steel_classes.get(fy, 500)
        
        def cost_function(x):
            b, h, As = x
            
            # Geometri kısıtlamaları
            if b < 200 or h < 250 or b > 500 or h > 800:
                return 1e10
            
            # Minimum donatı
            ok, As_min = self.check_minimum_reinforcement(b, h, As, 'beam')
            if not ok:
                return 1e10
            
            # Maximum donatı
            if (As / (b * h)) * 100 > self.const.rho_max:
                return 1e10
            
            # Moment kapasitesi kontrol
            M_cap = self.calculate_moment_capacity(b, h, As, fck, fy)
            if M_cap is None or M_cap < Md:
                return 1e10
            
            # Kesme kapasitesi kontrol
            d = h - 40
            # Tahmini etriye: Ø10 @ 150mm
            Asv = 2 * np.pi * (10/2)**2 / 150  # mm²/mm
            V_cap = self.calculate_shear_capacity(b, d, Asv * 1000, fck)
            if V_cap < Vd:
                return 1e10
            
            # Maliyet hesabı
            volume = (b * h * 1000) / 1e9  # m³/m
            weight = (As * 7850) / 1e9  # ton/m
            
            cost = (volume * self.concrete_cost_per_m3 + 
                   weight * self.steel_cost_per_kg * 1000)
            
            return cost
        
        # Optimizasyon
        x0 = [300, 400, 1500]  # İlk tahmin
        bounds = [(200, 500), (250, 800), (500, 10000)]
        
        result = minimize(cost_function, x0, method='L-BFGS-B', bounds=bounds)
        
        if result.success and result.fun < 1e9:
            b, h, As = result.x
            M_cap = self.calculate_moment_capacity(b, h, As, fck, fy)
            d = h - 40
            Asv = 2 * np.pi * (10/2)**2 / 150
            V_cap = self.calculate_shear_capacity(b, d, Asv * 1000, fck)
            
            return {
                'b': int(np.round(b / 50) * 50),  # 50mm katı
                'h': int(np.round(h / 50) * 50),
                'As': int(As),
                'M_cap': M_cap,
                'V_cap': V_cap,
                'cost': result.fun,
                'status': 'OK'
            }
        
        return None
    
    def optimize_column_section(self, 
                               N: float,
                               M: float,
                               fck: str = 'C25',
                               fy: str = 'B500C') -> Optional[Dict]:
        """
        Kolon kesitini optimize et
        
        Args:
            N: Eksenel yük (kN)
            M: Eğilme momenti (kN⋅m)
            fck, fy: Malzeme sınıfları
        
        Returns:
            Optimum kolon tasarımı
        """
        def cost_function(x):
            b, h, As_ratio = x
            
            # Kısıtlamalar
            if b < 200 or h < 200:
                return 1e10
            
            As = (As_ratio / 100) * b * h
            
            # Min-max donatı
            if As_ratio < self.const.rho_min_column or As_ratio > self.const.rho_max:
                return 1e10
            
            # Maliyet
            volume = (b * h * 1000) / 1e9
            weight = (As * 7850) / 1e9
            cost = (volume * self.concrete_cost_per_m3 + 
                   weight * self.steel_cost_per_kg * 1000)
            
            return cost
        
        x0 = [300, 300, 2.0]
        bounds = [(200, 500), (200, 500), (1.0, 4.0)]
        
        result = minimize(cost_function, x0, method='L-BFGS-B', bounds=bounds)
        
        if result.success:
            b, h, As_ratio = result.x
            As = (As_ratio / 100) * b * h
            
            return {
                'b': int(np.round(b / 50) * 50),
                'h': int(np.round(h / 50) * 50),
                'As_ratio': As_ratio,
                'As': int(As),
                'cost': result.fun,
                'status': 'OK'
            }
        
        return None
