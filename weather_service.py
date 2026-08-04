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
        self.last_valid_weather: Optional[Tuple[float, str, int, float, float]] = None

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
            with urllib.request.urlopen(req, timeout=8) as response:
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

    def get_solar_position(self, dt: Optional[datetime.datetime] = None) -> Tuple[float, float, bool]:
        """
        Calcule l'élévation (°) et l'azimut (°) du soleil ainsi que l'exposition directe des baies vitrées.
        Fenêtre d'exposition avec marge de sécurité : Azimut entre 85° et 240°, élévation >= 10°.
        Retourne (elevation: float, azimuth: float, is_exposed: bool).
        """
        now = dt or datetime.datetime.now()
        day_of_year = now.timetuple().tm_yday

        # Déclinaison solaire en degrés
        declination = 23.45 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))

        # Équation du temps (minutes)
        b = math.radians((360 / 364) * (day_of_year - 81))
        eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

        # Heure solaire locale
        local_time_hours = now.hour + now.minute / 60.0 + now.second / 3600.0
        tz_offset = now.astimezone().utcoffset().total_seconds() / 3600.0 if now.tzinfo else 2.0
        utc_time_hours = local_time_hours - tz_offset

        solar_time = utc_time_hours + (self.longitude / 15.0) + (eot / 60.0)
        hour_angle = (solar_time - 12.0) * 15.0 # degrés

        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(declination)
        ha_rad = math.radians(hour_angle)

        # Élévation solaire
        sin_elevation = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
        elevation = math.degrees(math.asin(max(-1.0, min(1.0, sin_elevation))))

        # Azimut solaire (0°=Nord, 90°=Est, 180°=Sud, 270°=Ouest)
        cos_azimuth = (math.sin(dec_rad) * math.cos(lat_rad) - math.cos(dec_rad) * math.sin(lat_rad) * math.cos(ha_rad)) / math.cos(math.radians(elevation))
        azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_azimuth))))
        if hour_angle > 0:
            azimuth = 360.0 - azimuth

        # Fenêtre d'exposition directe avec marge de sécurité : Azimut dans [85°, 240°] et élévation >= 10°
        is_exposed = (elevation >= 10.0) and (85.0 <= azimuth <= 240.0)

        return round(elevation, 1), round(azimuth, 1), is_exposed

    def get_solar_radiation_factor(self) -> Tuple[float, str, int, float, float, Optional[float]]:
        """
        Calcule le facteur de rayonnement solaire direct non-linéaire et récupère le vent (km/h), le DNI (W/m²) et la T° max prévue.
        Returns (factor: float, description: str, cloud_cover: int, wind_speed: float, solar_dni: float, max_temp_today: float|None).
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.latitude}&longitude={self.longitude}&current=temperature_2m,cloud_cover,weather_code,wind_speed_10m,direct_normal_irradiance&daily=temperature_2m_max&timezone=auto&forecast_days=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
                current = data.get("current", {})
                daily = data.get("daily", {})
                
                cloud_cover = int(current.get("cloud_cover", 0))
                wind_speed = float(current.get("wind_speed_10m", 0.0))
                solar_dni = float(current.get("direct_normal_irradiance", 0.0))
                
                temps_max = daily.get("temperature_2m_max", [])
                max_temp_today = float(temps_max[0]) if temps_max and temps_max[0] is not None else None
                
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

                description = f"{desc_texte} (Nuages: {cloud_cover}%, DNI: {round(solar_dni, 1)} W/m², Vent: {round(wind_speed, 1)} km/h)"
                res = (factor, description, cloud_cover, round(wind_speed, 1), round(solar_dni, 1), max_temp_today)
                self.last_valid_weather = res
                return res
        except Exception as e:
            print(f"ℹ️ API Open-Meteo temporairement indisponible ({e})")
            if self.last_valid_weather is not None:
                f, desc, c, w, dni, mt = self.last_valid_weather
                return f, f"{desc} (Dernière valeur connue)", c, w, dni, mt
            return 1.0, "Indisponible (défaut 100%)", None, None, None, None

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
