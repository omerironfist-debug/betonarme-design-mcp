"""
Betonarme Tasarım MCP Sunucusu
Claude ile entegrasyonu sağlar
"""

from typing import Any, Dict
from ts500_optimizer import TS500ConcreteDesigner
from tbdy_2018_rules import TBDY2018SeismicDesigner


class ConcreteDesignMCPServer:
    """MCP Sunucu Tarafı (Claude ile iletişim)"""
    
    def __init__(self):
        self.ts500 = TS500ConcreteDesigner()
        self.seismic = None
    
    # ============ TS 500 TOOLS ============
    
    def tool_optimize_beam(self, 
                          moment_kNm: float,
                          shear_kN: float,
                          concrete: str = "C25",
                          steel: str = "B500C") -> Dict[str, Any]:
        """
        Tool: Kiriş kesitini optimize et
        """
        result = self.ts500.optimize_beam_section(moment_kNm, shear_kN, concrete, steel)
        
        if result:
            return {
                "status": "success",
                "design": result,
                "recommendation": f"Önerilen kiriş: {result['b']}x{result['h']} mm, Donatı: {result['As']} mm²"
            }
        else:
            return {"status": "error", "message": "Tasarım bulunamadı"}
    
    def tool_calculate_moment_capacity(self,
                                      width_mm: float,
                                      height_mm: float,
                                      reinforcement_mm2: float,
                                      concrete: str,
                                      steel: str) -> Dict[str, Any]:
        """
        Tool: Moment kapasitesini hesapla
        """
        capacity = self.ts500.calculate_moment_capacity(
            width_mm, height_mm, reinforcement_mm2, concrete, steel
        )
        
        if capacity:
            return {
                "status": "success",
                "moment_capacity_kNm": round(capacity, 2),
                "section": f"{width_mm}x{height_mm} mm"
            }
        else:
            return {"status": "error", "message": "Hesaplama başarısız"}
    
    def tool_check_reinforcement(self,
                                width_mm: float,
                                height_mm: float,
                                reinforcement_mm2: float,
                                element: str = "beam") -> Dict[str, Any]:
        """
        Tool: Donatı kontrolü (min/max)
        """
        ok, As_min = self.ts500.check_minimum_reinforcement(
            width_mm, height_mm, reinforcement_mm2, element
        )
        
        ratio = (reinforcement_mm2 / (width_mm * height_mm)) * 100
        
        return {
            "status": "success" if ok else "warning",
            "reinforcement_ratio": round(ratio, 2),
            "minimum_required_mm2": round(As_min, 0),
            "actual_mm2": reinforcement_mm2,
            "check": "✓ PASS" if ok else "✗ FAIL",
            "message": f"Donatı oranı: {ratio:.2f}% ({As_min:.0f}-{self.ts500.const.rho_max}%)"
        }
    
    # ============ TBDY 2018 TOOLS ============
    
    def tool_seismic_spectrum(self,
                             period_s: float,
                             soil_class: str = "Z2",
                             risk_category: str = "HIGH",
                             ductility: str = "OLS") -> Dict[str, Any]:
        """
        Tool: Deprem tasarım spektrumunu hesapla
        """
        self.seismic = TBDY2018SeismicDesigner(
            risk_category=risk_category,
            soil_class=soil_class,
            ductility_level=ductility
        )
        
        Sa = self.seismic.calculate_design_spectrum(period_s)
        
        return {
            "status": "success",
            "period_s": period_s,
            "design_acceleration_g": round(Sa, 4),
            "soil_class": soil_class,
            "ductility_level": ductility
        }
    
    def tool_seismic_force(self,
                          weight_kN: float,
                          period_s: float,
                          system: str = "frame",
                          soil_class: str = "Z2",
                          risk_category: str = "HIGH",
                          ductility: str = "OLS") -> Dict[str, Any]:
        """
        Tool: Tasarım deprem kuvvetini hesapla
        """
        seismic = TBDY2018SeismicDesigner(
            risk_category=risk_category,
            soil_class=soil_class,
            ductility_level=ductility
        )
        
        V = seismic.calculate_seismic_force(weight_kN, period_s, system)
        
        return {
            "status": "success",
            "seismic_force_kN": round(V, 1),
            "building_weight_kN": weight_kN,
            "force_ratio": round(V / weight_kN, 3),
            "message": f"Tasarım deprem kuvveti: {V:.1f} kN"
        }
    
    def tool_column_confinement(self,
                               diameter_mm: float,
                               steel_fy_MPa: float,
                               concrete_fck_MPa: float,
                               critical_region: bool = True,
                               soil_class: str = "Z2",
                               ductility: str = "OLS") -> Dict[str, Any]:
        """
        Tool: Kolon konfinmanı tasarla
        """
        seismic = TBDY2018SeismicDesigner(
            soil_class=soil_class,
            ductility_level=ductility
        )
        
        confinement = seismic.design_column_confinement(
            diameter_mm, steel_fy_MPa, concrete_fck_MPa, critical_region
        )
        
        return {
            "status": "success",
            "confinement": confinement,
            "recommendation": f"Ø{confinement['bar_diameter']} @ {confinement['spacing']} mm {confinement['type']}",
            "region": "Kritik Bölge" if critical_region else "Normal Bölge"
        }
    
    def tool_minimum_dimensions(self,
                               element_type: str = "column",
                               soil_class: str = "Z2",
                               ductility: str = "OLS") -> Dict[str, Any]:
        """
        Tool: Minimum eleman boyutları
        """
        seismic = TBDY2018SeismicDesigner(
            soil_class=soil_class,
            ductility_level=ductility
        )
        
        if element_type == "column":
            min_dim = seismic.get_minimum_column_dimension()
            elem_name = "Kolon"
        else:
            min_dim = seismic.get_minimum_beam_dimension()
            elem_name = "Kiriş"
        
        return {
            "status": "success",
            "element": elem_name,
            "minimum_dimension_mm": min_dim,
            "ductility_level": ductility,
            "message": f"{elem_name} minimum boyutu: {min_dim} mm ({ductility})"
        }
    
    # ============ RAPOR OLUŞTURMA ============
    
    def tool_generate_report(self,
                            building_name: str,
                            num_stories: int,
                            height_m: float,
                            soil_class: str = "Z2",
                            ductility: str = "OLS") -> Dict[str, Any]:
        """
        Tool: Tasarım raporu oluştur
        """
        seismic = TBDY2018SeismicDesigner(
            soil_class=soil_class,
            ductility_level=ductility
        )
        
        report = seismic.generate_design_report(building_name, num_stories, height_m)
        
        return {
            "status": "success",
            "report": report,
            "building": building_name
        }
    
    # ============ KOMBİNASYON: TASARIM VE DEPREM ============
    
    def tool_combined_design(self,
                            moment_kNm: float,
                            shear_kN: float,
                            seismic_force_kN: float = 0,
                            concrete: str = "C25",
                            steel: str = "B500C",
                            is_seismic: bool = True) -> Dict[str, Any]:
        """
        Tool: TS 500 + TBDY 2018 kombinasyon tasarımı
        """
        # Deprem yükünü moment/kesmeye ekle
        if is_seismic and seismic_force_kN > 0:
            # Deprem kuvvetini moment olarak hesapla (tipik 3m kol)
            seismic_moment = seismic_force_kN * 3  # kN⋅m
            total_moment = moment_kNm + seismic_moment * 1.25  # Katsayı ile
            total_shear = shear_kN + seismic_force_kN * 0.8
        else:
            total_moment = moment_kNm
            total_shear = shear_kN
        
        # Tasarım
        design = self.ts500.optimize_beam_section(total_moment, total_shear, concrete, steel)
        
        if design:
            return {
                "status": "success",
                "design": design,
                "moments": {
                    "original_kNm": moment_kNm,
                    "seismic_kNm": seismic_force_kN * 3 if is_seismic else 0,
                    "total_kNm": total_moment
                },
                "recommendation": f"Deprem+Statik Tasarım: {design['b']}x{design['h']} mm"
            }
        else:
            return {"status": "error", "message": "Kombinasyon tasarımı başarısız"}


# ============ MCP ARAÇ KAYDI ============

MCP_TOOLS = {
    # TS 500
    "optimize_beam": {
        "description": "Kiriş kesitini moment ve kesmeye göre optimize et",
        "parameters": {
            "moment_kNm": "float",
            "shear_kN": "float",
            "concrete": "str (C20-C40)",
            "steel": "str (B420C, B500C)"
        }
    },
    "calculate_moment_capacity": {
        "description": "Dikdörtgen kesit moment kapasitesini hesapla",
        "parameters": {
            "width_mm": "float",
            "height_mm": "float",
            "reinforcement_mm2": "float",
            "concrete": "str",
            "steel": "str"
        }
    },
    "check_reinforcement": {
        "description": "Donatı oranını min/max kontrol et",
        "parameters": {
            "width_mm": "float",
            "height_mm": "float",
            "reinforcement_mm2": "float",
            "element": "str (beam, column)"
        }
    },
    # TBDY 2018
    "seismic_spectrum": {
        "description": "TBDY 2018 tasarım spektrumunu hesapla",
        "parameters": {
            "period_s": "float",
            "soil_class": "str (Z1-Z4)",
            "risk_category": "str (LOW, MEDIUM, HIGH, CRITICAL)",
            "ductility": "str (DLS, OLS, HLS)"
        }
    },
    "seismic_force": {
        "description": "Tasarım deprem kuvvetini hesapla",
        "parameters": {
            "weight_kN": "float",
            "period_s": "float",
            "system": "str (frame, wall)"
        }
    },
    "column_confinement": {
        "description": "Kolon konfinman etriyeleri tasarla",
        "parameters": {
            "diameter_mm": "float",
            "steel_fy_MPa": "float",
            "concrete_fck_MPa": "float",
            "critical_region": "bool"
        }
    },
    "minimum_dimensions": {
        "description": "Minimum eleman boyutlarını getir",
        "parameters": {
            "element_type": "str (column, beam)",
            "ductility": "str (DLS, OLS, HLS)"
        }
    },
    "generate_report": {
        "description": "TBDY tasarım raporu oluştur",
        "parameters": {
            "building_name": "str",
            "num_stories": "int",
            "height_m": "float",
            "soil_class": "str",
            "ductility": "str"
        }
    },
    "combined_design": {
        "description": "TS 500 + TBDY 2018 kombinasyon tasarımı",
        "parameters": {
            "moment_kNm": "float",
            "shear_kN": "float",
            "seismic_force_kN": "float",
            "concrete": "str",
            "steel": "str",
            "is_seismic": "bool"
        }
    }
}
