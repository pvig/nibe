#!/usr/bin/env python3
"""
Gestionnaire d'historisation SQLite pour l'automatisation Nibe & Tydom.
"""

import os
import sqlite3
import time
import json
import datetime
from typing import Dict, Any, List, Optional


class HistoryDatabase:
    def __init__(self, db_filename: str = "history.db"):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.db_path = os.path.join(base_dir, db_filename)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialise les tables de la base de données SQLite si elles n'existent pas."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Table d'historique des mesures et régulations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    datetime_iso TEXT NOT NULL,
                    t_ext REAL,
                    t_int REAL,
                    cloud_cover INTEGER,
                    facteur_soleil REAL,
                    elev_soleil REAL,
                    azim_soleil REAL,
                    facade_exposee INTEGER,
                    est_absent INTEGER,
                    mode_canicule INTEGER,
                    taux_fermeture REAL,
                    shutters_json TEXT,
                    event_type TEXT,
                    action_summary TEXT
                )
            """)

            # Table du journal d'ordres moteurs exécutés
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    datetime_iso TEXT NOT NULL,
                    shutter_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    previous_state TEXT,
                    reason TEXT
                )
            """)

            # Index pour accélérer les requêtes d'historique par date
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp)")
            conn.commit()

    def log_run(
        self,
        t_ext: Optional[float],
        t_int: Optional[float],
        cloud_cover: int,
        facteur_soleil: float,
        elev_soleil: float,
        azim_soleil: float,
        facade_exposee: bool,
        est_absent: bool,
        mode_canicule: bool,
        taux_fermeture: float,
        shutters: Dict[str, str],
        event_type: str = "REGULAR",
        action_summary: str = ""
    ) -> None:
        """Enregistre un point de mesure et l'état des volets."""
        now = datetime.datetime.now()
        timestamp = int(now.timestamp())
        datetime_iso = now.strftime("%Y-%m-%d %H:%M:%S")

        try:
            with self._get_connection() as conn:
                conn.cursor().execute(
                    """
                    INSERT INTO history (
                        timestamp, datetime_iso, t_ext, t_int, cloud_cover,
                        facteur_soleil, elev_soleil, azim_soleil, facade_exposee,
                        est_absent, mode_canicule, taux_fermeture, shutters_json,
                        event_type, action_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        datetime_iso,
                        t_ext,
                        t_int,
                        cloud_cover,
                        round(facteur_soleil, 3),
                        round(elev_soleil, 1),
                        round(azim_soleil, 1),
                        1 if facade_exposee else 0,
                        1 if est_absent else 0,
                        1 if mode_canicule else 0,
                        round(taux_fermeture, 3),
                        json.dumps(shutters),
                        event_type,
                        action_summary
                    )
                )
                conn.commit()
        except Exception as e:
            print(f"⚠️ Erreur lors de l'enregistrement de l'historique SQLite : {e}")

    def log_action(
        self,
        shutter_name: str,
        action: str,
        previous_state: str = "",
        reason: str = ""
    ) -> None:
        """Enregistre une action physique envoyée à un volet."""
        now = datetime.datetime.now()
        timestamp = int(now.timestamp())
        datetime_iso = now.strftime("%Y-%m-%d %H:%M:%S")

        try:
            with self._get_connection() as conn:
                conn.cursor().execute(
                    """
                    INSERT INTO actions (
                        timestamp, datetime_iso, shutter_name, action, previous_state, reason
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, datetime_iso, shutter_name, action, previous_state, reason)
                )
                conn.commit()
        except Exception as e:
            print(f"⚠️ Erreur lors de l'enregistrement de l'action SQLite : {e}")

    def get_live_state(self) -> Dict[str, Any]:
        """Retourne la dernière entrée enregistrée et l'état des volets."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM history ORDER BY timestamp DESC LIMIT 1")
                row = cursor.fetchone()
                if not row:
                    return {}

                data = dict(row)
                data["shutters"] = json.loads(data.get("shutters_json") or "{}")
                return data
        except Exception as e:
            print(f"⚠️ Erreur de lecture du statut live SQLite : {e}")
            return {}

    def get_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Retourne l'historique des points de mesure des N dernières heures.
        Si hours <= 0, retourne tout l'historique disponible.
        Effectue un sous-échantillonnage fluide si le nombre de points est élevé (> 500 points).
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if hours > 0:
                    limit_timestamp = int(time.time()) - (hours * 3600)
                    cursor.execute(
                        "SELECT * FROM history WHERE timestamp >= ? ORDER BY timestamp ASC",
                        (limit_timestamp,)
                    )
                else:
                    cursor.execute("SELECT * FROM history ORDER BY timestamp ASC")
                
                rows = cursor.fetchall()
                total_rows = len(rows)

                # Sous-échantillonnage intelligent pour garder au maximum ~500 points
                step = max(1, total_rows // 500)
                selected_rows = rows[::step] if step > 1 else rows

                result = []
                for r in selected_rows:
                    item = dict(r)
                    item["shutters"] = json.loads(item.get("shutters_json") or "{}")
                    result.append(item)
                return result
        except Exception as e:
            print(f"⚠️ Erreur de lecture de l'historique SQLite : {e}")
            return []

    def get_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retourne le journal des N dernières actions moteurs."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM actions ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"⚠️ Erreur de lecture du journal des actions SQLite : {e}")
            return []
