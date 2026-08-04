#!/usr/bin/env python3
"""
Module de communication Modbus TCP avec la pompe à chaleur Nibe S735.
"""

from typing import Tuple, Optional
from pymodbus.client import ModbusTcpClient

class NibeClient:
    def __init__(self, ip: str = "192.168.1.11", port: int = 502):
        self.ip = ip
        self.port = port
        self.reg_temp_ext = 1   # Sonde extérieure BT1
        self.reg_temp_int = 116 # Sonde d'ambiance intérieure BT50
        self.reg_presence = 137 # Statut de présence / vacances Nibe
        self.reg_vmc_mode = 104 # Mode Ventilation (0=Normale, 1-4=Vitesses)

    def get_temperatures(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Lit les températures extérieure (BT1) et intérieure (BT50).
        Retourne (t_ext, t_int) en °C ou (None, None) en cas d'erreur.
        """
        client = ModbusTcpClient(self.ip, port=self.port)
        if not client.connect():
            print("❌ Impossible de se connecter à la pompe à chaleur Nibe.")
            return None, None

        try:
            res_ext = client.read_input_registers(address=self.reg_temp_ext, count=1)
            res_int = client.read_input_registers(address=self.reg_temp_int, count=1)

            t_ext = res_ext.registers[0] / 10.0 if not res_ext.isError() else None
            t_int = res_int.registers[0] / 10.0 if not res_int.isError() else None

            return t_ext, t_int
        finally:
            client.close()

    def get_presence_status(self) -> Tuple[bool, int]:
        """
        Lit le statut de présence/absence Nibe (Registre Input 137).
        Retourne (est_absent: bool, valeur_brute: int).
        - 0   : Présent (Home)
        - > 0 : Absent / Vacances (Away)
        """
        client = ModbusTcpClient(self.ip, port=self.port)
        if not client.connect():
            return False, 0

        try:
            res = client.read_input_registers(address=self.reg_presence, count=1)
            if not res.isError():
                raw_val = res.registers[0]
                is_away = (raw_val != 0)
                return is_away, raw_val
        except Exception as e:
            print(f"⚠️ Erreur de lecture de la présence Nibe (Reg {self.reg_presence}): {e}")
        finally:
            client.close()

        return False, 0

    def set_vmc_mode(self, mode: int) -> bool:
        """
        Définit le mode de ventilation (0=Normale, 1=Vitesse 1, 2=Vitesse 2, 3=Vitesse 3, 4=Vitesse 4).
        """
        client = ModbusTcpClient(self.ip, port=self.port)
        if not client.connect():
            print("❌ Impossible de se connecter à la pompe à chaleur Nibe (VMC).")
            return False
            
        try:
            # Mode Ventilation = Holding Register 104
            res = client.write_register(self.reg_vmc_mode, mode)
            if res.isError():
                print(f"⚠️ Erreur Modbus écriture VMC mode {mode}.")
                return False
            return True
        except Exception as e:
            print(f"⚠️ Exception écriture VMC Nibe: {e}")
            return False
        finally:
            client.close()
