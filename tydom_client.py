#!/usr/bin/env python3
"""
Client MQTT Tydom pour la gestion des commandes de volets et de la découverte.
"""

import time
import json
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None
from typing import Dict, Optional, List, Tuple

class TydomMqttClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        devices: Optional[Dict[str, str]] = None,
        invert_wiring: bool = True
    ):
        self.host = host
        self.port = port
        self.devices = devices or {
            "salon": "1762458154_1762458154",
            "bureau": "1762458846_1762458846",
            "cuisine": "1762459305_1762459305",
            "chambre": "1762459622_1762459622",
        }
        self.invert_wiring = invert_wiring

    def send_command(self, device_name: str, action: str) -> bool:
        """
        Envoie une commande MQTT (OPEN / CLOSE / STOP / 0-100) pour un volet donné.
        Gère l'inversion de câblage si active.
        """
        if device_name not in self.devices:
            print(f"❌ Volet inconnu: '{device_name}'. Choisir parmi: {list(self.devices.keys())}")
            return False

        device_id = self.devices[device_name]
        act_str = str(action).upper()

        # Si le câblage électrique est inversé (UP provoque un DOWN), on inverse la commande
        if self.invert_wiring:
            if act_str in ["DOWN", "CLOSE"]:
                act_str = "UP"
            elif act_str in ["UP", "OPEN"]:
                act_str = "DOWN"
            elif act_str.isdigit():
                act_str = str(max(0, min(100, 100 - int(act_str))))

        if mqtt is None:
            print("⚠️ Module paho-mqtt non disponible.")
            return False

        client = mqtt.Client()
        try:
            client.connect(self.host, self.port, 60)
        except Exception as e:
            print(f"⚠️ Échec de connexion au broker MQTT {self.host}:{self.port} ({e})")
            return False

        if act_str in ["CLOSE", "DOWN"]:
            topic_cmd = f"cover/tydom/{device_id}/set_positionCmd"
            payload_cmd = "DOWN"
            topic_pos = f"cover/tydom/{device_id}/set_position"
            payload_pos = "0"
        elif act_str in ["OPEN", "UP"]:
            topic_cmd = f"cover/tydom/{device_id}/set_positionCmd"
            payload_cmd = "UP"
            topic_pos = f"cover/tydom/{device_id}/set_position"
            payload_pos = "100"
        elif act_str == "STOP":
            topic_cmd = f"cover/tydom/{device_id}/set_positionCmd"
            payload_cmd = "STOP"
            topic_pos = None
        else:
            topic_cmd = None
            topic_pos = f"cover/tydom/{device_id}/set_position"
            payload_pos = str(act_str)

        if topic_cmd:
            print(f"  ➜ Volet {device_name.capitalize()} -> Topic '{topic_cmd}' = '{payload_cmd}'")
            client.publish(topic_cmd, payload_cmd)
        if topic_pos:
            print(f"  ➜ Volet {device_name.capitalize()} -> Topic '{topic_pos}' = '{payload_pos}'")
            client.publish(topic_pos, payload_pos)

        client.disconnect()
        return True

    def discover_devices(self, scan_duration: int = 5) -> Dict[str, str]:
        """
        Écoute les messages de découverte Home Assistant / Tydom et retourne les volets trouvés.
        """
        discovered = {}

        def on_msg(client, userdata, msg):
            topic = msg.topic
            payload = msg.payload.decode('utf-8', errors='ignore')
            if topic.startswith("homeassistant/cover/") and topic.endswith("/config"):
                try:
                    data = json.loads(payload)
                    unique_id = data.get("unique_id")
                    device_info = data.get("device", {})
                    name = device_info.get("name") or unique_id
                    
                    cle = name.lower().replace("volet", "").strip().replace(" ", "_")
                    if not cle:
                        cle = str(unique_id)
                    
                    discovered[cle] = unique_id
                    print(f"  ✔ Découvert : '{name}' -> ID: '{unique_id}' (Clé: '{cle}')")
                except Exception:
                    pass

        client = mqtt.Client()
        client.on_message = on_msg
        client.connect(self.host, self.port, 60)
        client.subscribe("homeassistant/cover/#")

        print(f"🔍 Recherche des volets sur le broker MQTT ({scan_duration} secondes)...")
        client.loop_start()
        time.sleep(scan_duration)
        client.loop_stop()
        client.disconnect()
        return discovered
