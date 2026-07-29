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


PORT = int(os.getenv("PORT", "8080"))
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multithreadé pour gérer plusieurs requêtes simultanées."""
    daemon_threads = True


class RequestHandler(BaseHTTPRequestHandler):
    db_logger = HistoryDatabase()
    weather = WeatherService()

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
        """Sert les fichiers statiques du dossier web/."""
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

    def send_json_response(self, data: Any):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
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
