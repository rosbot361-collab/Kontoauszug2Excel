# 🚀 Deployment-Guide

Schritt-für-Schritt-Anleitung zum Deployen von Kontoauszug2Excel auf Hetzner Cloud.

---

## 📋 Voraussetzungen

- Hetzner Cloud Account (oder andere VPS-Anbieter)
- Domain (optional, aber empfohlen)
- SSH-Zugang zum Server

---

## 🖥️ Server-Setup

### 1. Server erstellen

```bash
# Hetzner Cloud Console
- Server-Typ: CX21 (2 vCPU, 4 GB RAM)
- OS: Ubuntu 22.04
- Location: Nürnberg (DSGVO-konform)
- SSH-Key hinzufügen
```

**Kosten:** ~5€/Monat

### 2. Server-Verbindung

```bash
ssh root@<SERVER_IP>
```

### 3. System-Updates

```bash
apt update && apt upgrade -y
apt install -y git curl wget vim
```

---

## 🐳 Docker installieren

```bash
# Docker installieren
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose installieren
apt install -y docker-compose

# Docker-Service starten
systemctl enable docker
systemctl start docker

# Testen
docker --version
docker-compose --version
```

---

## 📦 Projekt deployen

### 1. Repository klonen

```bash
cd /opt
git clone https://github.com/rosbot361-collab/Kontoauszug2Excel.git
cd Kontoauszug2Excel
```

### 2. Umgebungsvariablen

```bash
# .env Datei erstellen
cat > .env << EOF
DATABASE_URL=sqlite:///jobs.db
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EOF
```

### 3. Docker Compose starten

```bash
docker-compose up -d

# Logs prüfen
docker-compose logs -f

# Status prüfen
docker-compose ps
```

---

## 🌐 Nginx als Reverse Proxy

### 1. Nginx installieren

```bash
apt install -y nginx
```

### 2. Nginx-Konfiguration

```bash
# Konfiguration erstellen
cat > /etc/nginx/sites-available/kontoauszug2excel << 'EOF'
server {
    listen 80;
    server_name <DEINE_DOMAIN>;

    client_max_body_size 20M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Symlink erstellen
ln -s /etc/nginx/sites-available/kontoauszug2excel /etc/nginx/sites-enabled/

# Nginx testen und neustarten
nginx -t
systemctl restart nginx
```

---

## 🔒 SSL mit Let's Encrypt

```bash
# Certbot installieren
apt install -y certbot python3-certbot-nginx

# SSL-Zertifikat erstellen
certbot --nginx -d <DEINE_DOMAIN>

# Auto-Renewal testen
certbot renew --dry-run
```

**Fertig!** Deine App ist jetzt unter `https://<DEINE_DOMAIN>` erreichbar.

---

## 🔄 Updates deployen

```bash
cd /opt/Kontoauszug2Excel

# Änderungen pullen
git pull

# Container neu bauen und starten
docker-compose down
docker-compose build
docker-compose up -d
```

---

## 📊 Monitoring

### Logs anzeigen

```bash
# Alle Logs
docker-compose logs -f

# Nur API
docker-compose logs -f api

# Nur Celery Worker
docker-compose logs -f celery_worker
```

### Container-Status

```bash
# Status prüfen
docker-compose ps

# Ressourcen-Nutzung
docker stats
```

---

## 🛡️ Firewall einrichten

```bash
# UFW aktivieren
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw enable

# Status prüfen
ufw status
```

---

## 🔧 Troubleshooting

### Container startet nicht

```bash
# Logs prüfen
docker-compose logs api

# Container neu starten
docker-compose restart api
```

### Redis-Verbindung fehlgeschlagen

```bash
# Redis-Container prüfen
docker-compose ps redis

# Redis neu starten
docker-compose restart redis
```

### Disk-Space voll

```bash
# Docker aufräumen
docker system prune -a

# Alte Logs löschen
docker-compose logs --tail=1000 > /dev/null
```

---

## 📈 Skalierung

### Mehr Celery Worker

```yaml
# docker-compose.yml anpassen
celery_worker:
  deploy:
    replicas: 3  # 3 Worker statt 1
```

### Größerer Server

```bash
# Hetzner Cloud Console
- Server-Typ wechseln auf CX31 (2 vCPU, 8 GB RAM)
```

---

## 💾 Backup

```bash
# Datenbank-Backup
cp /opt/Kontoauszug2Excel/jobs.db /backup/jobs_$(date +%Y%m%d).db

# Automatisches Backup (Cronjob)
crontab -e

# Täglich um 3 Uhr
0 3 * * * cp /opt/Kontoauszug2Excel/jobs.db /backup/jobs_$(date +\%Y\%m\%d).db
```

---

## ✅ Checkliste

- [ ] Server erstellt (Hetzner CX21)
- [ ] Docker installiert
- [ ] Projekt geklont
- [ ] Docker Compose gestartet
- [ ] Nginx konfiguriert
- [ ] SSL-Zertifikat erstellt
- [ ] Firewall aktiviert
- [ ] Backup eingerichtet
- [ ] Domain konfiguriert
- [ ] Tests durchgeführt

---

**🎉 Deployment abgeschlossen!**
