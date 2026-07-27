#!/usr/bin/env python3
"""
Service Météo : Calcul du lever/coucher du soleil et détection de l'état du ciel via Open-Meteo.
"""

import math
import datetime
import urllib.request
import json
from typing import Tuple, Optional

class WeatherService:
    def __init__(self, latitude: float = 48.549, longitude: float = -1.751, delay_minutes: int = 5):
        self.latitude = latitude
        self.longitude = longitude
        self.delay_minutes = delay_minutes

    def get_sun_times(self) -> Tuple[str, str]:
        """
        Calcule les heures de lever et coucher du soleil du jour avec le décalage configuré (+5 min).
        Retourne (heure_lever, heure_coucher) au format HH:MM.
        """
        maintenant = datetime.datetime.now()
        
        # 1. Tentative via l'API en ligne api.sunrise-sunset.org
        try:
            url = f"https://api.sunrise-sunset.org/json?lat={self.latitude}&lng={self.longitude}&formatted=0"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("status") == "OK":
                    res = data["results"]
                    dt_sunrise = datetime.datetime.fromisoformat(res["sunrise"]).astimezone()
                    dt_sunset = datetime.datetime.fromisoformat(res["sunset"]).astimezone()
                    
                    dt_sunrise += datetime.timedelta(minutes=self.delay_minutes)
                    dt_sunset += datetime.timedelta(minutes=self.delay_minutes)

                    return dt_sunrise.strftime('%H:%M'), dt_sunset.strftime('%H:%M')
        except Exception as e:
            print(f"ℹ️ API soleil en ligne indisponible ({e}), calcul astronomique de secours...")

        # 2. Calcul astronomique hors-ligne de secours
        day_of_year = maintenant.timetuple().tm_yday
        declination = 23.45 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))
        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(declination)
        cos_h = -math.tan(lat_rad) * math.tan(dec_rad)
        cos_h = max(-1.0, min(1.0, cos_h))
        h = math.degrees(math.acos(cos_h))
        
        solar_noon_utc = 12.0 - (self.longitude / 15.0)
        sunrise_utc = solar_noon_utc - (h / 15.0)
        sunset_utc = solar_noon_utc + (h / 15.0)
        
        tz_offset = maintenant.astimezone().utcoffset().total_seconds() / 3600.0
        sunrise_dt = maintenant.replace(
            hour=int((sunrise_utc + tz_offset) % 24),
            minute=int((((sunrise_utc + tz_offset) % 1) * 60))
        ) + datetime.timedelta(minutes=self.delay_minutes)

        sunset_dt = maintenant.replace(
            hour=int((sunset_utc + tz_offset) % 24),
            minute=int((((sunset_utc + tz_offset) % 1) * 60))
        ) + datetime.timedelta(minutes=self.delay_minutes)

        return sunrise_dt.strftime('%H:%M'), sunset_dt.strftime('%H:%M')

    def get_solar_radiation_factor(self) -> Tuple[float, str, int]:
        """
        Calcule le facteur de rayonnement solaire direct non-linéaire (Physique atmosphérique Kasten-Czeplak).
        Formule : S = (1 - cloud_cover / 100)^2
        Returns (factor: float, description: str, cloud_cover: int).
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current=temperature_2m,cloud_cover,weather_code"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                current = data.get("current", {})
                w_code = current.get("weather_code", 0)
                cloud_cover = int(current.get("cloud_cover", 0))
                
                # Modèle physique non-linéaire du rayonnement direct (atténuation quadratique)
                factor = max(0.0, min(1.0, (1.0 - (cloud_cover / 100.0)) ** 2))
                
                if cloud_cover < 20:
                    desc_texte = "Soleil direct fort"
                elif cloud_cover < 50:
                    desc_texte = "Soleil modéré / Éclaircies"
                elif cloud_cover < 80:
                    desc_texte = "Soleil très faible / Nuageux"
                else:
                    desc_texte = "Très couvert / Aucun rayonnement direct"

                description = f"{desc_texte} (Nuages: {cloud_cover}%, Rayonnement direct: {int(factor * 100)}%)"
                return factor, description, cloud_cover
        except Exception as e:
            print(f"ℹ️ API Open-Meteo indisponible ({e}) -> Par défaut: Rayonnement direct supposé (100%).")
            return 1.0, "Indisponible (défaut 100%)", 0

    def get_forecast_next_hours(self, hours: int = 3) -> Tuple[Optional[float], Optional[float], str]:
        """
        Récupère les prévisions météo horaires sur les prochaines `hours` heures.
        Retourne (max_temp_future: float, solar_factor_future: float, description: str).
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&hourly=temperature_2m,cloud_cover,weather_code&forecast_hours={hours + 1}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                hourly = data.get("hourly", {})
                temps = hourly.get("temperature_2m", [])
                clouds = hourly.get("cloud_cover", [])
                
                if temps and clouds:
                    max_temp = max(temps[:hours])
                    min_cloud = min(clouds[:hours])
                    solar_factor = max(0.0, min(1.0, (1.0 - (min_cloud / 100.0)) ** 2))
                    description = f"Prévision +{hours}h -> Max T°: {max_temp}°C, Nuages min: {min_cloud}% (Rayonnement max: {int(solar_factor * 100)}%)"
                    return max_temp, solar_factor, description
        except Exception as e:
            print(f"ℹ️ Impossible de récupérer les prévisions météo ({e})")
        
        return None, None, "Prévisions indisponibles"
