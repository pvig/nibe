#!/usr/bin/env python3
"""
Serveur Web embarqué ultra-léger (Python standard http.server) pour l'automatisation Nibe & Tydom.
Permet d'accéder au Tableau de Bord et aux API d'historique en réseau local.
"""

import os
import json
import urllib.parse
from typing import Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from db_logger import HistoryDatabase
from weather_service import WeatherService
from tydom_client import TydomMqttClient
from state_store import StateStore


PORT = int(os.getenv("PORT", "8080"))
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web", "dist")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multithreadé pour gérer plusieurs requêtes simultanées."""
    daemon_threads = True


class RequestHandler(BaseHTTPRequestHandler):
    db_logger = HistoryDatabase()
    weather = WeatherService()
    tydom = TydomMqttClient()
    state_store = StateStore()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/live":
            self.handle_api_live()
        elif path == "/api/history":
            hours = int(query.get("hours", ["24"])[0])
            self.handle_api_history(hours)
        elif path == "/api/actions":
            limit = int(query.get("limit", ["50"])[0])
            self.handle_api_actions(limit)
        else:
            self.serve_static_file(path)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/shutter/command":
            self.handle_api_shutter_command()
        else:
            self.send_error(404, "Endpoint non trouvé")

    def handle_api_shutter_command(self):
        """Reçoit une commande d'action pour un ou tous les volets."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}

            name = str(data.get("name", "")).lower()
            action = str(data.get("action", "")).upper()

            if not name or not action:
                self.send_json_response({"success": False, "error": "Paramètres manquants ('name' et 'action')"}, status=400)
                return

            etat_memoire = self.state_store.load()
            shutters_state = etat_memoire.get("shutters", {})

            if name == "all":
                success_count = 0
                for device_name in self.tydom.devices.keys():
                    res = self.tydom.send_command(device_name, action)
                    shutters_state[device_name] = action
                    self.db_logger.log_action(
                        shutter_name=device_name,
                        action=action,
                        reason="Commande Manuelle Web (Global)"
                    )
                    if res:
                        success_count += 1
                
                etat_memoire["shutters"] = shutters_state
                self.state_store.save(etat_memoire)
                self.send_json_response({"success": True, "message": f"Ordre '{action}' envoyé aux volets"})
            else:
                res = self.tydom.send_command(name, action)
                shutters_state[name] = action
                etat_memoire["shutters"] = shutters_state
                self.state_store.save(etat_memoire)
                self.db_logger.log_action(
                    shutter_name=name,
                    action=action,
                    reason="Commande Manuelle Web"
                )
                self.send_json_response({"success": True, "message": f"Ordre '{action}' envoyé au volet {name}"})
        except Exception as e:
            print(f"⚠️ Erreur commande volet Web : {e}")
            self.send_json_response({"success": False, "error": str(e)}, status=500)

    def handle_api_live(self):
        """Retourne la dernière mesure enregistrée + prédictions solaires."""
        live_data = self.db_logger.get_live_state()
        sunrise, sunset = self.weather.get_sun_times()
        
        response = {
            "live": live_data,
            "sun": {
                "sunrise": sunrise,
                "sunset": sunset
            }
        }
        self.send_json_response(response)

    def handle_api_history(self, hours: int):
        """Retourne les points de mesure des N dernières heures."""
        history_data = self.db_logger.get_history(hours=hours)
        self.send_json_response(history_data)

    def handle_api_actions(self, limit: int):
        """Retourne le journal des N dernières actions moteurs."""
        actions_data = self.db_logger.get_actions(limit=limit)
        self.send_json_response(actions_data)

    def serve_static_file(self, path: str):
        """Sert les fichiers statiques du dossier web/dist/."""
        if path in ["/", "/index.html"]:
            file_path = os.path.join(WEB_DIR, "index.html")
            content_type = "text/html; charset=utf-8"
        else:
            # Sécurité pour éviter le directory traversal
            clean_path = os.path.normpath(path).lstrip("/")
            file_path = os.path.join(WEB_DIR, clean_path)
            
            if not file_path.startswith(WEB_DIR):
                self.send_error(403, "Accès refusé")
                return

            if clean_path.endswith(".css"):
                content_type = "text/css"
            elif clean_path.endswith(".js"):
                content_type = "application/javascript"
            elif clean_path.endswith(".json"):
                content_type = "application/json"
            elif clean_path.endswith(".ico"):
                content_type = "image/x-icon"
            elif clean_path.endswith(".svg"):
                content_type = "image/svg+xml"
            else:
                content_type = "text/plain"

        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Erreur serveur : {e}")
        else:
            self.send_error(404, "Fichier non trouvé")

    def send_json_response(self, data: Any, status: int = 200):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """Silencer les logs HTTP standards pour ne pas polluer stdout."""
        pass


def run_server(port: int = PORT):
    os.makedirs(WEB_DIR, exist_ok=True)
    server_address = ("0.0.0.0", port)
    httpd = ThreadedHTTPServer(server_address, RequestHandler)
    print(f"🚀 Serveur Web Nibe & Tydom démarré sur http://0.0.0.0:{port}")
    print(f"📱 Accessible sur votre réseau local via http://<IP_RASPBERRY>:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du serveur Web.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
