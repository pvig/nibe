#!/usr/bin/env python3
"""
Moteur principal d'automatisation des volets Nibe & Tydom.
"""

import datetime
from typing import List, Optional
from nibe_client import NibeClient
from weather_service import WeatherService
from tydom_client import TydomMqttClient
from state_store import StateStore

class ShutterAutomationEngine:
    def __init__(
        self,
        nibe_client: Optional[NibeClient] = None,
        weather_service: Optional[WeatherService] = None,
        tydom_client: Optional[TydomMqttClient] = None,
        state_store: Optional[StateStore] = None,
        temp_ext_high: float = 25.0,
        temp_int_high: float = 23.5,
        temp_ext_low: float = 21.0,
        heat_protection_shutters: Optional[List[str]] = None
    ):
        self.nibe = nibe_client or NibeClient()
        self.weather = weather_service or WeatherService()
        self.tydom = tydom_client or TydomMqttClient()
        self.state_store = state_store or StateStore()
        
        self.temp_ext_high = temp_ext_high
        self.temp_int_high = temp_int_high
        self.temp_ext_low = temp_ext_low
        self.heat_protection_shutters = heat_protection_shutters or ["salon", "bureau"]

    def run(self) -> None:
        """Exécute une itération de régulation."""
        maintenant = datetime.datetime.now()
        heure_actuelle = maintenant.strftime('%H:%M')
        date_actuelle = maintenant.strftime('%Y-%m-%d')
        print(f"\n--- [{maintenant.strftime('%Y-%m-%d %H:%M:%S')}] Régulation Nibe & Tydom ---")

        # 1. Calcul des heures de soleil (+5 min)
        heure_lever_5m, heure_coucher_5m = self.weather.get_sun_times()
        print(f"🌅 Lever du soleil (+5 min)  : {heure_lever_5m}")
        print(f"🌇 Coucher du soleil (+5 min) : {heure_coucher_5m}")

        etat_memoire = self.state_store.load()
        shutters_state = etat_memoire.get("shutters", {})
        commandes_a_passer = {}

        # 2. Règle du Coucher du Soleil (+5 min) -> Fermeture de tous les volets (1 fois par jour)
        if heure_actuelle >= heure_coucher_5m and etat_memoire.get("last_sunset_trigger_date") != date_actuelle:
            print(f"🌇 Coucher du soleil atteint (+5 min: {heure_coucher_5m}) : Fermeture automatique de tous les volets.")
            for nom in self.tydom.devices.keys():
                commandes_a_passer[nom] = "CLOSE"
            etat_memoire["last_sunset_trigger_date"] = date_actuelle

        # 3. Règle du Lever du Soleil (+5 min) -> Ouverture de tous les volets (1 fois par jour)
        elif heure_actuelle >= heure_lever_5m and heure_actuelle < heure_coucher_5m and etat_memoire.get("last_sunrise_trigger_date") != date_actuelle:
            print(f"🌅 Lever du soleil atteint (+5 min: {heure_lever_5m}) : Ouverture automatique de tous les volets.")
            for nom in self.tydom.devices.keys():
                commandes_a_passer[nom] = "OPEN"
            etat_memoire["last_sunrise_trigger_date"] = date_actuelle

        # 4. Lecture des températures et météo (pendant la journée)
        t_ext, t_int = self.nibe.get_temperatures()
        ciel_ensoleille, description_ciel = self.weather.is_sky_sunny()

        if t_ext is not None and t_int is not None:
            print(f"🌡️  Température Extérieure (BT1) : {t_ext} °C | Intérieure (BT50) : {t_int} °C")
            print(f"🌤️  État du ciel : {description_ciel}")

            # Règle thermique : Protection Forte Chaleur uniquement si le ciel est ensoleillé (rayonnement direct)
            if t_ext >= self.temp_ext_high or t_int >= self.temp_int_high:
                if ciel_ensoleille:
                    print(f"☀️ Mode Protection Chaleur & Soleil direct actif -> Fermeture des volets ciblés ({', '.join(self.heat_protection_shutters)})...")
                    for nom in self.heat_protection_shutters:
                        commandes_a_passer[nom] = "CLOSE"
                else:
                    print("☁️ Forte chaleur détectée mais ciel couvert -> Pas de rayonnement solaire direct, volets maintenus pour la lumière naturelle.")

            # Règle thermique : Rafraîchissement
            elif t_ext <= self.temp_ext_low and heure_actuelle < heure_coucher_5m:
                print("🍃 Mode Rafraîchissement actif.")
                for nom in self.tydom.devices.keys():
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
                if self.tydom.send_command(nom, action_voulue):
                    shutters_state[nom] = action_voulue
                    modifications = True

        if modifications:
            etat_memoire["shutters"] = shutters_state
            self.state_store.save(etat_memoire)
            print("💾 Nouvel état mémorisé dans 'shutter_state.json'.")
        else:
            print("✅ Aucun changement d'ordre nécessaire.")
