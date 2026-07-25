#!/usr/bin/env python3
"""
Script d'automatisation : Régulation des volets Tydom en fonction de la température Nibe S735
-----------------------------------------------------------------------------------------
Interroge la PAC Nibe S735 en Modbus TCP et commande la fermeture/ouverture des volets via MQTT.
"""

import os
import time
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt

# Inversion du câblage des volets (défaut: True)
INVERT_COVER_WIRING = os.getenv("INVERT_COVER_WIRING", "true").lower() in ["true", "1", "yes"]

# Configuration Nibe S735 (Modbus TCP)
NIBE_IP = "192.168.1.11"
NIBE_PORT = 502
REG_TEMP_EXT = 1    # Sonde extérieure BT1
REG_TEMP_INT = 116  # Sonde d'ambiance intérieure BT50

# Configuration MQTT Local
MQTT_HOST = "localhost"
MQTT_PORT = 1883

# Liste des volets Tydom avec leurs identifiants
VOLETS = {
    "salon": "1762458154_1762458154",
    "bureau": "1762458846_1762458846",
    "cuisine": "1762459305_1762459305",
    "chambre": "1762459622_1762459622",
}

# Seuils de température (en °C) pour la protection solaire / confort
SEUIL_TEMP_EXT_HAUTE = 25.0  # Si T° extérieure > 25°C -> Protection solaire (fermer volets)
SEUIL_TEMP_INT_HAUTE = 23.5  # Si T° intérieure > 23.5°C -> Fermer volets exposés
SEUIL_TEMP_EXT_BASSE = 21.0  # Si T° extérieure < 21°C -> Réouvrir les volets

import json

# Fichier de persistance des états des volets
STATE_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "shutter_state.json")

def charger_etat():
    """Charge l'état précédent enregistré par le script."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erreur de lecture du fichier d'état : {e}")
    return {"shutters": {}, "last_chambre_trigger_date": ""}

def sauvegarder_etat(etat):
    """Sauvegarde l'état actuel dans le fichier JSON."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(etat, f, indent=2)
    except Exception as e:
        print(f"⚠️ Erreur de sauvegarde du fichier d'état : {e}")

def lire_temp_nibe():
    """Lit les températures Extérieure (BT1) et Intérieure (BT50) de la Nibe S735."""
    client = ModbusTcpClient(NIBE_IP, port=NIBE_PORT)
    if not client.connect():
        print("❌ Impossible de se connecter à la pompe à chaleur Nibe.")
        return None, None

    try:
        res_ext = client.read_input_registers(address=REG_TEMP_EXT, count=1)
        res_int = client.read_input_registers(address=REG_TEMP_INT, count=1)

        t_ext = res_ext.registers[0] / 10.0 if not res_ext.isError() else None
        t_int = res_int.registers[0] / 10.0 if not res_int.isError() else None

        return t_ext, t_int
    finally:
        client.close()

def envoyer_commande_volet(nom_volet, action):
    """Envoie la commande MQTT exacte (UP/DOWN/0-100) pour un volet."""
    if nom_volet not in VOLETS:
        return

    device_id = VOLETS[nom_volet]
    act_str = str(action).upper()

    # Si le câblage électrique est inversé (UP provoque un DOWN), on inverse la commande
    if INVERT_COVER_WIRING:
        if act_str in ["DOWN", "CLOSE"]:
            act_str = "UP"
        elif act_str in ["UP", "OPEN"]:
            act_str = "DOWN"
        elif act_str.isdigit():
            act_str = str(max(0, min(100, 100 - int(act_str))))

    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)

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
        payload_pos = str(action)

    if topic_cmd:
        print(f"  ➜ Volet {nom_volet.capitalize()} -> Topic '{topic_cmd}' = '{payload_cmd}'")
        client.publish(topic_cmd, payload_cmd)
    if topic_pos:
        print(f"  ➜ Volet {nom_volet.capitalize()} -> Topic '{topic_pos}' = '{payload_pos}'")
        client.publish(topic_pos, payload_pos)

    client.disconnect()

import math
import datetime
import urllib.request
import json

# Coordonnées géographiques pour le lever/coucher du soleil (par défaut: France / Nantes)
LATITUDE = float(os.getenv("LATITUDE", "47.2183"))
LONGITUDE = float(os.getenv("LONGITUDE", "-1.5536"))
DELAI_SOLEIL_MINUTES = 5  # Décalage de 5 minutes après lever/coucher

def obtenir_heures_soleil(lat=LATITUDE, lng=LONGITUDE):
    """
    Obtient les heures locales de lever et coucher du soleil pour la date actuelle.
    Utilise l'API sunrise-sunset.org avec calcul de secours astronomique hors-ligne.
    """
    maintenant = datetime.datetime.now()
    date_jour = maintenant.strftime('%Y-%m-%d')
    
    # 1. Tentative via l'API en ligne
    try:
        url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&formatted=0"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("status") == "OK":
                res = data["results"]
                dt_sunrise = datetime.datetime.fromisoformat(res["sunrise"]).astimezone()
                dt_sunset = datetime.datetime.fromisoformat(res["sunset"]).astimezone()
                
                # Ajout du décalage de +5 minutes
                dt_sunrise += datetime.timedelta(minutes=DELAI_SOLEIL_MINUTES)
                dt_sunset += datetime.timedelta(minutes=DELAI_SOLEIL_MINUTES)

                return dt_sunrise.strftime('%H:%M'), dt_sunset.strftime('%H:%M')
    except Exception as e:
        print(f"ℹ️ API soleil indisponible, calcul astronomique hors-ligne : {e}")

    # 2. Calcul astronomique de secours (hors-ligne)
    day_of_year = maintenant.timetuple().tm_yday
    declination = 23.45 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))
    lat_rad = math.radians(lat)
    dec_rad = math.radians(declination)
    cos_h = -math.tan(lat_rad) * math.tan(dec_rad)
    cos_h = max(-1.0, min(1.0, cos_h))
    h = math.degrees(math.acos(cos_h))
    
    solar_noon_utc = 12.0 - (lng / 15.0)
    sunrise_utc = solar_noon_utc - (h / 15.0)
    sunset_utc = solar_noon_utc + (h / 15.0)
    
    tz_offset = maintenant.astimezone().utcoffset().total_seconds() / 3600.0
    sunrise_dt = maintenant.replace(hour=int(sunrise_utc + tz_offset), minute=int((((sunrise_utc + tz_offset) % 1) * 60))) + datetime.timedelta(minutes=DELAI_SOLEIL_MINUTES)
    sunset_dt = maintenant.replace(hour=int(sunset_utc + tz_offset), minute=int((((sunset_utc + tz_offset) % 1) * 60))) + datetime.timedelta(minutes=DELAI_SOLEIL_MINUTES)

    return sunrise_dt.strftime('%H:%M'), sunset_dt.strftime('%H:%M')

def obtenir_etat_ciel(lat=LATITUDE, lng=LONGITUDE):
    """
    Interroge l'API gratuite Open-Meteo pour connaître l'état du ciel (ensoleillé vs très couvert/pluie).
    Returns (is_sunny: bool, description: str)
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode('utf-8'))
            weather = data.get("current_weather", {})
            w_code = weather.get("weathercode", 0)
            
            # Codes WMO : 0 = Dégagé, 1 & 2 = Peu nuageux (Soleil direct présent)
            is_sunny = w_code <= 2
            description = "Ensoleillé / Dégagé" if w_code == 0 else (
                "Peu nuageux" if w_code in [1, 2] else (
                    "Très couvert" if w_code == 3 else f"Nuageux/Pluie (code {w_code})"
                )
            )
            return is_sunny, description
    except Exception as e:
        print(f"ℹ️ API météo indisponible ({e}) -> Par défaut: Ciel ensoleillé supposé.")
        return True, "Indisponible (défaut ensoleillé)"

def reguler_volets():
    """Logique de décision basée sur le soleil, l'état du ciel, les températures Nibe et l'état mémorisé."""
    maintenant = datetime.datetime.now()
    heure_actuelle = maintenant.strftime('%H:%M')
    date_actuelle = maintenant.strftime('%Y-%m-%d')
    print(f"\n--- [{maintenant.strftime('%Y-%m-%d %H:%M:%S')}] Régulation Nibe & Tydom ---")

    # Calcul des heures de lever et coucher du soleil du jour (+5 min)
    heure_lever_5m, heure_coucher_5m = obtenir_heures_soleil()
    print(f"🌅 Lever du soleil (+5 min)  : {heure_lever_5m}")
    print(f"🌇 Coucher du soleil (+5 min) : {heure_coucher_5m}")

    etat_memoire = charger_etat()
    shutters_state = etat_memoire.get("shutters", {})
    commandes_a_passer = {}

    # 1. Règle du Coucher du Soleil (+ 5 min) -> Fermeture de tous les volets (1 fois par jour)
    if heure_actuelle >= heure_coucher_5m and etat_memoire.get("last_sunset_trigger_date") != date_actuelle:
        print(f"🌇 Coucher du soleil atteint (+5 min: {heure_coucher_5m}) : Fermeture automatique de tous les volets.")
        for nom in VOLETS.keys():
            commandes_a_passer[nom] = "CLOSE"
        etat_memoire["last_sunset_trigger_date"] = date_actuelle

    # 2. Règle du Lever du Soleil (+ 5 min) -> Ouverture de tous les volets (1 fois par jour)
    elif heure_actuelle >= heure_lever_5m and heure_actuelle < heure_coucher_5m and etat_memoire.get("last_sunrise_trigger_date") != date_actuelle:
        print(f"🌅 Lever du soleil atteint (+5 min: {heure_lever_5m}) : Ouverture automatique de tous les volets.")
        for nom in VOLETS.keys():
            commandes_a_passer[nom] = "OPEN"
        etat_memoire["last_sunrise_trigger_date"] = date_actuelle

    # 3. Lecture et régulation selon les températures Nibe & l'état du ciel
    t_ext, t_int = lire_temp_nibe()
    ciel_ensoleille, description_ciel = obtenir_etat_ciel()

    if t_ext is not None and t_int is not None:
        print(f"🌡️  Température Extérieure (BT1) : {t_ext} °C | Intérieure (BT50) : {t_int} °C")
        print(f"🌤️  État du ciel : {description_ciel}")

        # Règle thermique : Protection Forte Chaleur uniquement si le ciel est ensoleillé (rayonnement direct)
        if t_ext >= SEUIL_TEMP_EXT_HAUTE or t_int >= SEUIL_TEMP_INT_HAUTE:
            if ciel_ensoleille:
                print("☀️ Mode Protection Chaleur & Soleil direct actif -> Fermeture des volets pour éviter l'effet de serre.")
                for nom in ["salon", "bureau", "cuisine", "chambre"]:
                    commandes_a_passer[nom] = "CLOSE"
            else:
                print("☁️ Forte chaleur détectée mais ciel couvert -> Pas de rayonnement solaire direct, volets maintenus pour la lumière naturelle.")

        # Règle thermique : Rafraîchissement
        elif t_ext <= SEUIL_TEMP_EXT_BASSE and heure_actuelle < heure_coucher_5m:
            print("🍃 Mode Rafraîchissement actif.")
            for nom in ["salon", "bureau", "cuisine", "chambre"]:
                commandes_a_passer[nom] = "OPEN"
    else:
        print("⚠️ Données Nibe indisponibles pour la régulation thermique.")

    # 5. Application des commandes (Ignorer si identique à la précédente pour laisser le contrôle manuel)
    modifications = False
    for nom, action_voulue in commandes_a_passer.items():
        derniere_action = shutters_state.get(nom)

        if derniere_action == action_voulue:
            print(f"  ℹ️ Volet {nom.capitalize()} : Déjà commandé en '{action_voulue}' précédemment -> Ignoré pour laisser la main à l'utilisateur.")
        else:
            print(f"  ⚡ Volet {nom.capitalize()} : Nouvel ordre '{action_voulue}' (précédent: '{derniere_action}')")
            envoyer_commande_volet(nom, action_voulue)
            shutters_state[nom] = action_voulue
            modifications = True

    if modifications:
        etat_memoire["shutters"] = shutters_state
        sauvegarder_etat(etat_memoire)
        print("💾 Nouvel état mémorisé dans 'shutter_state.json'.")
    else:
        print("✅ Aucun changement d'ordre nécessaire.")

if __name__ == "__main__":
    reguler_volets()
