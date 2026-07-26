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
