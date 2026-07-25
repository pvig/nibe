#!/usr/bin/env python3
import os
import sys
import time
import json
import paho.mqtt.client as mqtt

# Configuration MQTT Hôte
MQTT_HOST = "localhost"
MQTT_PORT = 1883

# IDs des volets détectés dans les logs Tydom
VOLETS = {
    "salon": "1762458154_1762458154",
    "bureau": "1762458846_1762458846",
    "cuisine": "1762459305_1762459305",
    "chambre": "1762459622_1762459622",
}

def print_usage():
    print("Usage: python3 test_volet.py [discover | listen | nom_volet] [commande/position]")
    print("Exemples :")
    print("  python3 test_volet.py discover         # Découvrir les topics MQTT enregistrés par tydom2mqtt")
    print("  python3 test_volet.py listen           # Écouter tous les messages MQTT Tydom en direct")
    print("  python3 test_volet.py bureau close     # Fermer le volet du bureau avec suivi des retours")
    print("  python3 test_volet.py bureau open      # Ouvrir le volet du bureau")
    print("  python3 test_volet.py bureau 50        # Régler la position à 50%")

def decouvrir_topics():
    """Écoute les messages de configuration Home Assistant / Tydom pour extraire les volets et générer le dictionnaire VOLETS."""
    volets_decouverts = {}
    
    def on_msg(client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        if topic.startswith("homeassistant/cover/") and topic.endswith("/config"):
            try:
                data = json.loads(payload)
                unique_id = data.get("unique_id")
                device_info = data.get("device", {})
                name = device_info.get("name") or unique_id
                
                # Normalisation du nom pour servir de clé (ex. "Volet salon" -> "salon")
                cle = name.lower().replace("volet", "").strip().replace(" ", "_")
                if not cle:
                    cle = str(unique_id)
                
                volets_decouverts[cle] = unique_id
                print(f"  ✔ Découvert : '{name}' -> ID: '{unique_id}' (Clé suggérée: '{cle}')")
            except Exception:
                pass

    client = mqtt.Client()
    client.on_message = on_msg
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.subscribe("homeassistant/cover/#")
    
    print("🔍 Recherche des volets sur le broker MQTT (5 secondes)...")
    client.loop_start()
    time.sleep(5)
    client.loop_stop()
    client.disconnect()
    
    print("\n✅ Recherche terminée ! Voici le dictionnaire VOLETS à copier-coller dans vos scripts :")
    print("\nVOLETS = {")
    for k, v in volets_decouverts.items():
        print(f'    "{k}": "{v}",')
    print("}\n")

def ecouter_topics():
    def on_msg(client, userdata, msg):
        print(f"📩 [{msg.topic}] -> {msg.payload.decode('utf-8', errors='ignore')}")

    client = mqtt.Client()
    client.on_message = on_msg
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.subscribe("tydom/#")
    client.subscribe("homeassistant/#")
    print("🎧 Écoute continue des retours Tydom & Home Assistant MQTT (Ctrl+C pour quitter)...")
    client.loop_forever()

# Variable d'environnement pour câblage inversé (défaut: True)
INVERT_COVER_WIRING = os.getenv("INVERT_COVER_WIRING", "true").lower() in ["true", "1", "yes"]

def envoyer_commande(nom_volet, action):
    if nom_volet not in VOLETS:
        print(f"❌ Volet inconnu: '{nom_volet}'. Choisir parmi: {list(VOLETS.keys())}")
        return

    device_id = VOLETS[nom_volet]
    act_str = str(action).upper()

    # Si le câblage électrique est inversé (UP provoque physiquement un DOWN), on inverse les commandes
    if INVERT_COVER_WIRING:
        if act_str in ["DOWN", "CLOSE"]:
            act_str = "UP"
        elif act_str in ["UP", "OPEN"]:
            act_str = "DOWN"
        elif act_str.isdigit():
            act_str = str(max(0, min(100, 100 - int(act_str))))

    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    # Topics exacts découverts depuis tydom2mqtt :
    # command_topic: "cover/tydom/<id>/set_positionCmd" (payloads: "UP", "DOWN", "STOP")
    # set_position_topic: "cover/tydom/<id>/set_position" (payloads: "0" à "100")

    if act_str in ["DOWN", "CLOSE"]:
        topic_cmd = f"cover/tydom/{device_id}/set_positionCmd"
        payload_cmd = "DOWN"
        topic_pos = f"cover/tydom/{device_id}/set_position"
        payload_pos = "0"
    elif act_str in ["UP", "OPEN"]:
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
        print(f"🚀 Envoi vers '{topic_cmd}' = '{payload_cmd}'")
        client.publish(topic_cmd, payload_cmd)
    if topic_pos:
        print(f"🚀 Envoi vers '{topic_pos}' = '{payload_pos}'")
        client.publish(topic_pos, payload_pos)

    client.disconnect()
    print(f"✨ Commande envoyée au volet {nom_volet.capitalize()} !")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "discover":
        decouvrir_topics()
    elif cmd == "listen":
        ecouter_topics()
    elif len(sys.argv) >= 3:
        envoyer_commande(cmd, sys.argv[2])
    else:
        print_usage()
