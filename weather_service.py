#!/usr/bin/env python3
"""
Service Météo : Calcul du lever/coucher du soleil et détection de l'état du ciel via Open-Meteo.
"""

import math
import datetime
import urllib.request
import json
from typing import Tuple

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

    def is_sky_sunny(self) -> Tuple[bool, str]:
        """
        Interroge l'API Open-Meteo pour vérifier si le ciel est ensoleillé (soleil direct).
        Retourne (is_sunny: bool, description: str).
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current_weather=true"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                weather = data.get("current_weather", {})
                w_code = weather.get("weathercode", 0)
                
                # Codes WMO: 0 = Dégagé, 1 & 2 = Peu nuageux (soleil direct présent)
                is_sunny = w_code <= 2
                description = "Ensoleillé / Dégagé" if w_code == 0 else (
                    "Peu nuageux" if w_code in [1, 2] else (
                        "Très couvert" if w_code == 3 else f"Nuageux/Pluie (code {w_code})"
                    )
                )
                return is_sunny, description
        except Exception as e:
            print(f"ℹ️ API Open-Meteo indisponible ({e}) -> Par défaut: Ciel ensoleillé supposé.")
            return True, "Indisponible (défaut ensoleillé)"
