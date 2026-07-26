#!/usr/bin/env python3
"""
Point d'entrée principal : Régulation automatique Nibe S735 <-> Volets Tydom.
"""

import os
from nibe_client import NibeClient
from weather_service import WeatherService
from tydom_client import TydomMqttClient
from state_store import StateStore
from engine import ShutterAutomationEngine

# Configuration globale
NIBE_IP = os.getenv("NIBE_IP", "192.168.1.11")
NIBE_PORT = int(os.getenv("NIBE_PORT", "502"))

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

LATITUDE = float(os.getenv("LATITUDE", "48.549"))
LONGITUDE = float(os.getenv("LONGITUDE", "-1.751"))

INVERT_COVER_WIRING = os.getenv("INVERT_COVER_WIRING", "true").lower() in ["true", "1", "yes"]

# Identifiants de vos volets Tydom
VOLETS = {
    "salon": "1762458154_1762458154",
    "bureau": "1762458846_1762458846",
    "cuisine": "1762459305_1762459305",
    "chambre": "1762459622_1762459622",
}

# Volets spécifiques concernés par la fermeture anti-chaleur en journée
VOLETS_PROTECTION_CHALEUR = ["salon", "bureau"]

# Seuils thermiques (°C)
SEUIL_TEMP_EXT_HAUTE = 25.0
SEUIL_TEMP_INT_HAUTE = 23.5
SEUIL_TEMP_EXT_BASSE = 21.0

def main():
    nibe = NibeClient(ip=NIBE_IP, port=NIBE_PORT)
    weather = WeatherService(latitude=LATITUDE, longitude=LONGITUDE)
    tydom = TydomMqttClient(host=MQTT_HOST, port=MQTT_PORT, devices=VOLETS, invert_wiring=INVERT_COVER_WIRING)
    state_store = StateStore()

    engine = ShutterAutomationEngine(
        nibe_client=nibe,
        weather_service=weather,
        tydom_client=tydom,
        state_store=state_store,
        temp_ext_high=SEUIL_TEMP_EXT_HAUTE,
        temp_int_high=SEUIL_TEMP_INT_HAUTE,
        temp_ext_low=SEUIL_TEMP_EXT_BASSE,
        heat_protection_shutters=VOLETS_PROTECTION_CHALEUR
    )

    engine.run()

if __name__ == "__main__":
    main()
