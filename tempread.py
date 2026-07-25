#!/usr/bin/env python3
from pymodbus.client import ModbusTcpClient

# Configuration
NIBE_IP = "192.168.1.11"
NIBE_PORT = 502

REG_TEMP_EXT = 1    # Sonde extérieure BT1
REG_TEMP_INT = 116  # Sonde d'ambiance intérieure BT50

def lire_sondes_nibe():
    """Lit les températures extérieure et intérieure sur la Nibe S735 via Modbus TCP."""
    client = ModbusTcpClient(NIBE_IP, port=NIBE_PORT)
    
    if not client.connect():
        print("❌ Impossible de se connecter à la Nibe.")
        return None, None

    try:
        # Lecture de la sonde extérieure (Registre 1)
        res_ext = client.read_input_registers(address=REG_TEMP_EXT, count=1)
        # Lecture de la sonde intérieure (Registre 116)
        res_int = client.read_input_registers(address=REG_TEMP_INT, count=1)

        temp_ext = None
        temp_int = None

        if not res_ext.isError():
            temp_ext = res_ext.registers[0] / 10.0

        if not res_int.isError():
            temp_int = res_int.registers[0] / 10.0

        return temp_ext, temp_int

    finally:
        client.close()

if __name__ == "__main__":
    t_ext, t_int = lire_sondes_nibe()
    
    print("--- Rapport Températures Nibe S735 ---")
    if t_ext is not None:
        print(f" Thermomètre Extérieur (BT1) : {t_ext} °C")
    if t_int is not None:
        print(f" Thermomètre Intérieur (BT50) : {t_int} °C")