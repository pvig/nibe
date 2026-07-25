# 🛠️ Guide d'Installation Spécifique

Ce guide rassemble la procédure technique pour déployer la régulation **Nibe S735 <-> Tydom Delta Dore** sur un Raspberry Pi déjà opérationnel (accès SSH actif).

---

## 📋 Informations à rassembler

* **IP Nibe S735** : Ex. `192.168.1.11` (Modbus TCP sur le port `502`).
* **IP Tydom** : Ex. `192.168.1.12`.
* **MAC Tydom** : Ex. `001A25XXXXXX` (format sans les deux-points).
* **Identifiants Cloud Delta Dore** : Email et mot de passe de l'application Tydom.

---

## 1. Dépendances système (Raspberry Pi)

Installez Docker, le broker MQTT local et les dépendances Python :

```bash
sudo apt update && sudo apt install -y docker.io docker-compose mosquitto mosquitto-clients python3-pip python3-pymodbus python3-paho-mqtt
sudo usermod -aG docker $USER
```

---

## 2. Configuration du broker Mosquitto local

Pour autoriser le conteneur Docker `tydom2mqtt` à communiquer avec le Mosquitto de l'hôte via la passerelle `172.17.0.1` :

```bash
sudo bash -c 'cat <<EOF > /etc/mosquitto/conf.d/local.conf
listener 1883
allow_anonymous true
EOF'

sudo systemctl restart mosquitto
```

---

## 3. Déploiement du conteneur `tydom2mqtt`

Créez le dossier du projet et instanciez le fichier `docker-compose.yml` :

```bash
mkdir -p ~/nibe && cd ~/nibe
cp docker-compose.yml.example docker-compose.yml
```

Renseignez vos identifiants dans `docker-compose.yml` puis lancez le conteneur :

```bash
docker-compose up -d
docker-compose logs -f
```

*(Assurez-vous d'avoir l'indication `Connected to tydom` et la détection de vos volets).*

---

## 4. Transfert & Test des Scripts Python

Depuis votre PC de développement, copiez le projet sur le Pi :

```bash
scp *.py pi@raspberrypi.local:~/nibe/
```

Sur le Raspberry Pi :

```bash
# 1. Découvrir automatiquement vos volets et générer le dictionnaire VOLETS
python3 test_volet.py discover
```

Copiez le dictionnaire `VOLETS = { ... }` généré à l'écran et collez-le dans vos fichiers `test_volet.py` et `nibe_shutter_control.py`.

```bash
# 2. Tester le contrôle individuel d'un volet
python3 test_volet.py bureau close

# 3. Exécuter un premier cycle de régulation Nibe -> Tydom
python3 nibe_shutter_control.py
```

---

## 5. Automatisation Cron

Ajoutez le script dans le `crontab` du Raspberry Pi pour une vérification automatique (ex. toutes les 5 minutes) :

```crontab
*/5 * * * * python3 /home/pi/nibe/nibe_shutter_control.py > /dev/null 2>&1
```

---

## ⚙️ Notes importantes de configuration

* **Fuseau horaire du Pi** : Assurez-vous que le Pi est réglé sur l'heure française (`sudo timedatectl set-timezone Europe/Paris`) pour le calcul exact des heures de soleil (+5 min).
* **Une seule connexion WebSocket Tydom 1.0** : Ne lancez pas `tydom2mqtt` simultanément sur votre PC et le Pi, la Tydom rejettera la seconde connexion avec une erreur 401.
* **Câblage inversé** : Si vos volets s'ouvrent au lieu de se fermer, l'option `INVERT_COVER_WIRING` est déjà active par défaut à `true` dans le script.
