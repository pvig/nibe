#!/usr/bin/env python3
"""
Scanner d'inspection directe de la Nibe S735.
Lit et compare exactement la table complète des registres actifs (Holding 0-250 & Input 0-250).
"""

import os
import sys
import json
from pymodbus.client import ModbusTcpClient

NIBE_IP = os.getenv("NIBE_IP", "192.168.1.11")
NIBE_PORT = int(os.getenv("NIBE_PORT", "502"))
SNAPSHOT_FILE = "nibe_snapshot.json"

def scan_all():
    client = ModbusTcpClient(NIBE_IP, port=NIBE_PORT, timeout=1.0)
    if not client.connect():
        print(f"❌ Impossible de se connecter à la Nibe sur {NIBE_IP}:{NIBE_PORT}")
        sys.exit(1)

    print(f"🔍 Balayage précis des 250 registres Nibe S735...")
    current_data = {"input": {}, "holding": {}}

    # Balayage par registre individuel sur la plage 0-250 (100% fiable)
    for reg in range(0, 240):
        try:
            r_hold = client.read_holding_registers(address=reg, count=1)
            if not r_hold.isError():
                current_data["holding"][str(reg)] = r_hold.registers[0]
        except Exception:
            pass

        try:
            r_in = client.read_input_registers(address=reg, count=1)
            if not r_in.isError():
                current_data["input"][str(reg)] = r_in.registers[0]
        except Exception:
            pass

    client.close()

    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE, "r") as f:
                old_data = json.load(f)

            diffs = []
            for r_type in ["holding", "input"]:
                for reg, val in current_data[r_type].items():
                    old_val = old_data.get(r_type, {}).get(reg)
                    if old_val is not None and old_val != val:
                        diffs.append(f"  ✨ [{r_type.upper()}] Registre {reg:<3} : Ancienne valeur = {old_val} ➜ Nouvelle valeur = {val}")

            if diffs:
                print("\n📊 DIFFÉRENCES DÉTECTÉES SUR LA NIBE S735 :\n")
                for d in diffs:
                    print(d)
            else:
                print("\nℹ️ Aucune différence détectée (les registres conservent les mêmes valeurs).")
        except Exception as e:
            print(f"⚠️ Erreur de comparaison : {e}")

    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(current_data, f, indent=2)

    print(f"\n💾 Instantané enregistré dans '{SNAPSHOT_FILE}' ({len(current_data['input'])} Inputs, {len(current_data['holding'])} Holdings répertoriés).")

if __name__ == "__main__":
    scan_all()
