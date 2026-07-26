#!/usr/bin/env python3
"""
Script CLI de test et découverte des volets roulants via TydomMqttClient.
"""

import sys
import os
from tydom_client import TydomMqttClient

# Configuration MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
INVERT_COVER_WIRING = os.getenv("INVERT_COVER_WIRING", "true").lower() in ["true", "1", "yes"]

# IDs des volets détectés dans les logs Tydom
VOLETS = {
    "salon": "1762458154_1762458154",
    "bureau": "1762458846_1762458846",
    "cuisine": "1762459305_1762459305",
    "chambre": "1762459622_1762459622",
}

def print_usage():
    print("Usage: python3 test_volet.py [discover | nom_volet] [commande/position]")
    print("Exemples :")
    print("  python3 test_volet.py discover         # Découvrir les volets et générer le dictionnaire VOLETS")
    print("  python3 test_volet.py bureau close     # Fermer le volet du bureau")
    print("  python3 test_volet.py bureau open      # Ouvrir le volet du bureau")
    print("  python3 test_volet.py bureau 50        # Régler la position à 50%")

def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1].lower()
    client = TydomMqttClient(host=MQTT_HOST, port=MQTT_PORT, devices=VOLETS, invert_wiring=INVERT_COVER_WIRING)

    if cmd == "discover":
        discovered = client.discover_devices()
        print("\n✅ Recherche terminée ! Voici le dictionnaire VOLETS à copier-coller dans vos scripts :")
        print("\nVOLETS = {")
        for k, v in discovered.items():
            print(f'    "{k}": "{v}",')
        print("}\n")

    elif len(sys.argv) >= 3:
        action = sys.argv[2]
        if client.send_command(cmd, action):
            print(f"✨ Commande envoyée au volet {cmd.capitalize()} !")
    else:
        print_usage()

if __name__ == "__main__":
    main()
