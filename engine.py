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
from db_logger import HistoryDatabase

class ShutterAutomationEngine:
    def __init__(
        self,
        nibe_client: Optional[NibeClient] = None,
        weather_service: Optional[WeatherService] = None,
        tydom_client: Optional[TydomMqttClient] = None,
        state_store: Optional[StateStore] = None,
        db_logger: Optional[HistoryDatabase] = None,
        temp_ext_high: float = 25.0,
        temp_int_high: float = 23.5,
        temp_ext_low: float = 21.0,
        heat_protection_shutters: Optional[List[str]] = None,
        canicule_protection_shutters: Optional[List[str]] = None,
        min_motor_interval_minutes: int = 30,
        dni_seuil: float = 400.0,
        dni_hyst: float = 50.0,
        dni_temp_int_seuil: float = 22.0
    ):
        self.nibe = nibe_client or NibeClient()
        self.weather = weather_service or WeatherService()
        self.tydom = tydom_client or TydomMqttClient()
        self.state_store = state_store or StateStore()
        self.db_logger = db_logger or HistoryDatabase()
        
        self.temp_ext_high = temp_ext_high
        self.temp_int_high = temp_int_high
        self.temp_ext_low = temp_ext_low
        self.heat_protection_shutters = heat_protection_shutters or ["salon", "bureau"]
        self.canicule_protection_shutters = canicule_protection_shutters or ["salon", "bureau", "chambre"]
        self.min_motor_interval_seconds = min_motor_interval_minutes * 60
        self.dni_seuil = dni_seuil
        self.dni_hyst = dni_hyst
        self.dni_temp_int_seuil = dni_temp_int_seuil

    def run(self) -> None:
        """Exécute une itération de régulation."""
        maintenant = datetime.datetime.now()
        heure_actuelle = maintenant.strftime('%H:%M')
        date_actuelle = maintenant.strftime('%Y-%m-%d')
        print(f"\n--- [{maintenant.strftime('%Y-%m-%d %H:%M:%S')}] Régulation Nibe & Tydom ---")

        # 1. Lecture des températures, du statut de présence Nibe et de la météo
        t_ext, t_int = self.nibe.get_temperatures()
        est_absent, val_presence = self.nibe.get_presence_status()
        facteur_soleil, description_ciel, cloud_cover, wind_speed, solar_dni = self.weather.get_solar_radiation_factor()

        if cloud_cover is None or wind_speed is None or solar_dni is None:
            last_state = self.db_logger.get_live_state()
            if cloud_cover is None: cloud_cover = last_state.get("cloud_cover", 0) if last_state.get("cloud_cover") is not None else 0
            if wind_speed is None: wind_speed = last_state.get("wind_speed", 0.0) if last_state.get("wind_speed") is not None else 0.0
            if solar_dni is None: solar_dni = last_state.get("solar_dni", 0.0) if last_state.get("solar_dni") is not None else 0.0
            
            # Recalculate solar factor based on recovered cloud cover
            facteur_soleil = max(0.0, min(1.0, (1.0 - (cloud_cover / 100.0)) ** 2))

        # 2. Calcul des heures de soleil (+5 min)
        heure_lever_5m, heure_coucher_5m = self.weather.get_sun_times()
        print(f"🌅 Lever du soleil (+5 min)  : {heure_lever_5m}")
        print(f"🌇 Coucher du soleil (+5 min) : {heure_coucher_5m}")

        etat_memoire = self.state_store.load()
        shutters_state = etat_memoire.get("shutters", {})
        commandes_a_passer = {}
        is_sun_event = False

        # 3. Règle du Coucher du Soleil (+5 min) -> Fermeture uniquement si Mode Absent Nibe (Reg 137 > 0)
        if heure_actuelle >= heure_coucher_5m and etat_memoire.get("last_sunset_trigger_date") != date_actuelle:
            if est_absent:
                print(f"🌇 Coucher du soleil (+5 min: {heure_coucher_5m}) en Mode Absent : Fermeture automatique de tous les volets.")
                for nom in self.tydom.devices.keys():
                    commandes_a_passer[nom] = "CLOSE"
                is_sun_event = True
            else:
                print(f"🌇 Coucher du soleil (+5 min: {heure_coucher_5m}) en Mode Présent : Fermeture nocturne automatique ignorée.")
            etat_memoire["last_sunset_trigger_date"] = date_actuelle

        # 4. Règle du Lever du Soleil (+5 min) -> Ouverture de tous les volets (Mode Présent & Mode Absent)
        elif heure_actuelle >= heure_lever_5m and heure_actuelle < heure_coucher_5m and etat_memoire.get("last_sunrise_trigger_date") != date_actuelle:
            print(f"🌅 Lever du soleil (+5 min: {heure_lever_5m}) : Ouverture automatique de tous les volets.")
            for nom in self.tydom.devices.keys():
                commandes_a_passer[nom] = "OPEN"
            etat_memoire["last_sunrise_trigger_date"] = date_actuelle
            is_sun_event = True

        # 5. Régulation thermique de journée
        if t_ext is not None and t_int is not None:
            # Enregistrement de l'échantillon toutes les 5 min dans l'historique glissant (12 échantillons = 1h)
            etat_memoire = self.state_store.add_sample(etat_memoire, t_ext, t_int, cloud_cover)
            samples = etat_memoire.get("samples", [])

            # Calcul des moyennes lissées sur la dernière heure d'échantillonnage
            t_ext_lisse = sum(s["t_ext"] for s in samples) / len(samples)
            cloud_lisse = sum(s["cloud_cover"] for s in samples) / len(samples)
            facteur_soleil_lisse = max(0.0, min(1.0, (1.0 - (cloud_lisse / 100.0)) ** 2))

            str_presence = f"🏠 Mode Présent (Reg 137 = {val_presence})" if not est_absent else f"✈️ Mode Absent / Vacances (Reg 137 = {val_presence})"
            print(f"🌡️  T° Ext instantanée (BT1) : {t_ext} °C | Intérieure (BT50) : {t_int} °C | {str_presence}")
            print(f"🌤️  Nuages : {cloud_cover}% | ☀️ DNI : {solar_dni} W/m² | 💨 Vent : {wind_speed} km/h | Lissé 1h : {int(cloud_lisse)}%")

            # Calcul de la position astronomique du soleil (Azimut & Élévation)
            elev_soleil, azim_soleil, facade_exposee = self.weather.get_solar_position()
            str_exposition = "Façade Exposée au Soleil Direct" if facade_exposee else "Façade à l'Ombre (Soleil Hors Fenêtre)"
            print(f"🧭 Position Solaire -> Élévation: {elev_soleil}° | Azimut: {azim_soleil}° ({str_exposition})")

            # La température utilise la mesure réelle instantanée (pas de retard), seul l'ensoleillement est lissé sur 1h
            t_decision = t_ext
            # Si le soleil est hors de la fenêtre d'exposition directe (Azimut [85°, 240°] et Élévation >= 10°), l'impact direct est nul
            facteur_soleil_decision = facteur_soleil_lisse if facade_exposee else 0.0

            # 1. Progression dans l'intervalle de température [temp_ext_low, temp_ext_high]
            if t_decision <= self.temp_ext_low:
                progress = 0.0
            elif t_decision >= self.temp_ext_high:
                progress = 1.0
            else:
                progress = (t_decision - self.temp_ext_low) / (self.temp_ext_high - self.temp_ext_low)

            # 2. Besoins thermiques doux (courbe quadratique progress^2)
            besoin_thermique = progress ** 2

            # 3. Taux de fermeture solaire effectif
            taux_fermeture_solaire = besoin_thermique * facteur_soleil_decision

            # 4. Protection conductive canicule (T° ext > 28°C)
            # Au-dessus de 28°C, la conduction de l'air chaud impose une fermeture progressive même à l'ombre
            if t_decision > 28.0:
                prog_canicule = min(1.0, (t_decision - 28.0) / (33.0 - 28.0))
                taux_canicule = prog_canicule ** 2
                print(f"🔥 Mode Canicule Actif (T° ext = {t_decision}°C > 28°C) -> Fermeture conductive de protection : {int(taux_canicule * 100)}%")
            else:
                taux_canicule = 0.0

            # Taux de fermeture final pour les volets de protection (max entre solaire et canicule)
            taux_fermeture_solaire_canicule = max(taux_fermeture_solaire, taux_canicule)

            # 3b. Régulation par cible DNI (Transmittance Proportionnelle)
            #     Active si : façade exposée + t_int dépasse le seuil + DNI dépasse la cible+hystérésis
            if facade_exposee and t_int > self.dni_temp_int_seuil and solar_dni > (self.dni_seuil + self.dni_hyst):
                taux_dni = max(0.0, 1.0 - self.dni_seuil / solar_dni)
                print(f"☀️ Régulation DNI : {solar_dni} W/m² > seuil {self.dni_seuil + self.dni_hyst} W/m², T° int {t_int}°C > {self.dni_temp_int_seuil}°C → fermeture DNI : {int(taux_dni * 100)}%")
            elif facade_exposee and solar_dni > self.dni_seuil:
                # Zone d'hystérésis : maintien du taux précédent pour éviter les oscillations
                taux_dni = etat_memoire.get("last_taux_dni", 0.0)
                print(f"☀️ Régulation DNI : dans la bande d'hystérésis ({solar_dni} W/m²), maintien à {int(taux_dni * 100)}%")
            else:
                taux_dni = 0.0
            etat_memoire["last_taux_dni"] = taux_dni

            taux_fermeture_final = max(taux_fermeture_solaire_canicule, taux_dni)
            ratio_pct = int(taux_fermeture_final * 100)

            # Position d'ouverture cible pour les volets ciblés (pas de 5%)
            pos_ouvert = round((1.0 - taux_fermeture_final) * 100 / 5.0) * 5
            if pos_ouvert >= 95:
                pos_target_str = "OPEN"
            elif pos_ouvert <= 5:
                pos_target_str = "CLOSE"
            else:
                pos_target_str = str(int(pos_ouvert))

            # Position d'ouverture canicule pour les autres volets
            pos_canicule_ouvert = round((1.0 - taux_canicule) * 100 / 5.0) * 5
            if pos_canicule_ouvert >= 95:
                pos_canicule_str = "OPEN"
            elif pos_canicule_ouvert <= 5:
                pos_canicule_str = "CLOSE"
            else:
                pos_canicule_str = str(int(pos_canicule_ouvert))

            # 5. Régulation thermique uniquement pendant la journée (entre le lever et le coucher du soleil)
            is_daytime = (heure_actuelle >= heure_lever_5m and heure_actuelle < heure_coucher_5m)

            if is_daytime:
                if t_decision > 28.0:
                    print(f"🔥 Canicule (>28°C) : Protection conductive appliquée aux volets canicule ({', '.join(self.canicule_protection_shutters)}). Les volets des plantes (ex: cuisine) restent ouverts.")
                    for nom in self.canicule_protection_shutters:
                        if nom in self.heat_protection_shutters:
                            commandes_a_passer[nom] = pos_target_str
                        else:
                            commandes_a_passer[nom] = pos_canicule_str
                elif t_decision > self.temp_ext_low:
                    print(f"☀️ Protection Solaire Lissée ({ratio_pct}% fermé, ouverture cible: {pos_target_str}) pour les volets ciblés ({', '.join(self.heat_protection_shutters)}).")
                    for nom in self.heat_protection_shutters:
                        commandes_a_passer[nom] = pos_target_str
                else:
                    print("🍃 Mode Rafraîchissement diurne actif (T° ext <= 21°C).")
                    for nom in self.tydom.devices.keys():
                        commandes_a_passer[nom] = "OPEN"
            else:
                print("🌙 Période nocturne (Régulation thermique diurne au repos).")
                elev_soleil, azim_soleil, facade_exposee = self.weather.get_solar_position()
                taux_fermeture_final = 0.0
        else:
            print("⚠️ Données Nibe indisponibles pour la régulation thermique.")
            elev_soleil, azim_soleil, facade_exposee = self.weather.get_solar_position()
            taux_fermeture_final = 0.0

        # 6. Filtrage d'activation temporisée des moteurs (Préservation des moteurs)
        import time
        now_ts = int(time.time())
        last_motor_action_time = etat_memoire.get("last_motor_action_time", 0)
        elapsed_since_motor = now_ts - last_motor_action_time

        # Seuls les événements exacts du coucher/lever du soleil autorisent l'activation hors fenêtre temporisée
        allow_motor_execution = (elapsed_since_motor >= self.min_motor_interval_seconds) or is_sun_event

        modifications = False
        if not allow_motor_execution and last_motor_action_time > 0:
            mins_restantes = max(1, int((self.min_motor_interval_seconds - elapsed_since_motor) / 60))
            print(f"⏳ Moteurs au repos (dernier déclenchement il y a {int(elapsed_since_motor/60)} min). Échantillon 5 min enregistré. Prochain mouvement autorisé dans ~{mins_restantes} min.")
            self.state_store.save(etat_memoire)
        else:
            for nom, action_voulue in commandes_a_passer.items():
                derniere_action = shutters_state.get(nom)

                # Ne jamais envoyer un ordre physique si le volet est déjà à la position voulue,
                # même pour un événement lever/coucher du soleil (évite les clics relais inutiles).
                if derniere_action == action_voulue:
                    reason_str = " (événement solaire, position déjà atteinte)" if is_sun_event else ""
                    print(f"  ℹ️ Volet {nom.capitalize()} : Déjà en '{action_voulue}'{reason_str} -> Aucun mouvement physique requis.")
                else:
                    print(f"  ⚡ Volet {nom.capitalize()} : Nouvel ordre '{action_voulue}' (précédent: '{derniere_action}')")
                    if self.tydom.send_command(nom, action_voulue):
                        shutters_state[nom] = action_voulue
                        modifications = True
                        self.db_logger.log_action(
                            shutter_name=nom,
                            action=action_voulue,
                            previous_state=str(derniere_action or ""),
                            reason="Lever/Coucher Soleil" if is_sun_event else "Régulation thermique"
                        )

            if modifications:
                etat_memoire["shutters"] = shutters_state
                etat_memoire["last_motor_action_time"] = now_ts
                self.state_store.save(etat_memoire)
                print("💾 Nouvel état et horodatage moteur enregistrés.")
            else:
                # Remettre à jour le timer même sans commande physique : sans ça, la fenêtre
                # de 30 min reste ouverte à chaque itération cron de 5 min et peut déclencher
                # des ordres répétés si les conditions varient légèrement.
                if allow_motor_execution:
                    etat_memoire["last_motor_action_time"] = now_ts
                self.state_store.save(etat_memoire)
                print("✅ Échantillon enregistré. Aucun changement d'ordre nécessaire.")

        # 7. Historisation SQLite
        try:
            elev_s = elev_soleil if 'elev_soleil' in locals() else 0.0
            azim_s = azim_soleil if 'azim_soleil' in locals() else 0.0
            facade_exp = facade_exposee if 'facade_exposee' in locals() else False
            taux_f = taux_fermeture_final if 'taux_fermeture_final' in locals() else 0.0
            c_cover = cloud_cover if 'cloud_cover' in locals() else 0
            f_soleil = facteur_soleil if 'facteur_soleil' in locals() else 0.0
            w_speed = wind_speed if 'wind_speed' in locals() else 0.0
            s_dni = solar_dni if 'solar_dni' in locals() else 0.0
            is_canicule = (t_ext is not None) and (t_ext > 28.0)
            event_lbl = "SUNSET" if (is_sun_event and "CLOSE" in commandes_a_passer.values()) else ("SUNRISE" if is_sun_event else ("CANICULE" if is_canicule else "REGULAR"))

            self.db_logger.log_run(
                t_ext=t_ext,
                t_int=t_int,
                cloud_cover=c_cover,
                facteur_soleil=f_soleil,
                elev_soleil=elev_s,
                azim_soleil=azim_s,
                facade_exposee=facade_exp,
                est_absent=est_absent,
                mode_canicule=is_canicule,
                taux_fermeture=taux_f,
                shutters=shutters_state,
                event_type=event_lbl,
                action_summary=f"Moteurs: {'Actifs' if modifications else 'Repos'}",
                wind_speed=w_speed,
                solar_dni=s_dni
            )
        except Exception as e:
            print(f"⚠️ Erreur lors de l'enregistrement de l'historique SQLite : {e}")

