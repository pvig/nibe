#!/usr/bin/env python3
"""
Gestion de la persistance de l'état des volets et de l'historique d'échantillonnage.
"""

import os
import time
import json
from typing import Dict, Any, List

class StateStore:
    def __init__(self, filename: str = "shutter_state.json"):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.filepath = os.path.join(base_dir, filename)

    def load(self) -> Dict[str, Any]:
        """Charge l'état précédent et l'historique d'échantillonnage."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    data.setdefault("shutters", {})
                    data.setdefault("last_sunset_trigger_date", "")
                    data.setdefault("last_sunrise_trigger_date", "")
                    data.setdefault("last_motor_action_time", 0)
                    data.setdefault("last_taux_dni", 0.0)
                    data.setdefault("samples", [])
                    return data
            except Exception as e:
                print(f"⚠️ Erreur de lecture du fichier d'état ({self.filepath}) : {e}")
        return {
            "shutters": {},
            "last_sunset_trigger_date": "",
            "last_sunrise_trigger_date": "",
            "last_motor_action_time": 0,
            "last_taux_dni": 0.0,
            "samples": []
        }

    def save(self, state: Dict[str, Any]) -> None:
        """Sauvegarde l'état actuel dans le fichier JSON."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur de sauvegarde du fichier d'état : {e}")

    def add_sample(self, state: Dict[str, Any], t_ext: float, t_int: float, cloud_cover: int, max_samples: int = 12) -> Dict[str, Any]:
        """
        Ajoute une mesure dans l'historique glissant (12 échantillons = 1 heure de données à 5 min d'intervalle).
        """
        samples = state.get("samples", [])
        now_ts = int(time.time())
        samples.append({
            "timestamp": now_ts,
            "t_ext": t_ext,
            "t_int": t_int,
            "cloud_cover": cloud_cover
        })
        state["samples"] = samples[-max_samples:]
        return state
