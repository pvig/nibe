#!/usr/bin/env python3
"""
Script utilitaire d'inspection des registres Modbus Nibe S735.
Permet d'explorer les registres de présence, mode d'exploitation et vacances.
"""

import os
import sys
from pymodbus.client import ModbusTcpClient

NIBE_IP = os.getenv("NIBE_IP", "192.168.1.11")
NIBE_PORT = int(os.getenv("NIBE_PORT", "502"))

def inspecter_registres():
    client = ModbusTcpClient(NIBE_IP, port=NIBE_PORT)
    if not client.connect():
        print(f"❌ Impossible de se connecter à la Nibe S735 sur {NIBE_IP}:{NIBE_PORT}")
        sys.exit(1)

    print(f"✅ Connecté à la Nibe S735 ({NIBE_IP}:{NIBE_PORT})\n")
    print("🔍 Inspection des registres candidats pour la présence et les modes d'exploitation :\n")

    # Liste des registres potentiels à vérifier (Holding Registers & Input Registers)
    candidats = [
        (1, "Input", "Sonde extérieure BT1"),
        (116, "Input", "Sonde d'ambiance BT50"),
        (102, "Holding", "Mode d'exploitation Nibe"),
        (104, "Holding", "Statut système"),
        (105, "Holding", "Consigne / Mode"),
        (119, "Holding", "Statut d'occupation"),
        (41264, "Holding", "Smart Home State"),
        (41265, "Holding", "Smart Home Away Mode (0: Home, 1: Away, 2: Vacation)"),
        (48053, "Holding", "Mode Vacances Eau Chaude"),
    ]

    for reg, reg_type, desc in candidats:
        try:
            if reg_type == "Input":
                res = client.read_input_registers(address=reg, count=1)
            else:
                res = client.read_holding_registers(address=reg, count=1)

            if not res.isError():
                valeur = res.registers[0]
                print(f"  • Registre {reg:<5} [{reg_type:<7}] : {valeur:<6} -> {desc}")
            else:
                print(f"  • Registre {reg:<5} [{reg_type:<7}] : [Non répondu/Erreur] -> {desc}")
        except Exception as e:
            print(f"  • Registre {reg:<5} [{reg_type:<7}] : Erreur ({e})")

    client.close()

if __name__ == "__main__":
    inspecter_registres()
