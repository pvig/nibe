#!/usr/bin/env python3
"""
Gestion de la persistance de l'état des volets dans un fichier JSON local.
"""

import os
import json
from typing import Dict, Any

class StateStore:
    def __init__(self, filename: str = "shutter_state.json"):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.filepath = os.path.join(base_dir, filename)

    def load(self) -> Dict[str, Any]:
        """Charge l'état précédent enregistré par l'application."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Erreur de lecture du fichier d'état ({self.filepath}) : {e}")
        return {"shutters": {}, "last_sunset_trigger_date": "", "last_sunrise_trigger_date": ""}

    def save(self, state: Dict[str, Any]) -> None:
        """Sauvegarde l'état actuel dans le fichier JSON."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur de sauvegarde du fichier d'état : {e}")
