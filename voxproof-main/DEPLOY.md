# VoxProof Docker Deploy

## Local Docker smoke test

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8765/health
curl -X POST http://localhost:8765/api/run/finance_voice_agent
docker compose logs -f voxproof
```

Open `http://localhost:8765`.

## Oracle ARM server setup

The Oracle Free Tier VM is `aarch64`, so use multi-arch base images only. The current
`Dockerfile` uses official `node:22-alpine` and `python:3.12-slim`, both available
for ARM64.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl ufw docker.io docker-compose-v2
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu
```

Log out and back in after `usermod`.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8765
sudo ufw --force enable
```

## Deploy app

```bash
mkdir -p ~/apps
cd ~/apps
git clone <YOUR_REPO_URL> voxproof
cd voxproof
cp .env.example .env
nano .env
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8765/health
```

For a quick IP-based demo, open:

```text
http://92.5.42.26:8765
```

For a polished demo, put Caddy/Nginx in front and keep the app bound to `8765`.

## Update

```bash
cd ~/apps/voxproof
git pull
docker compose up -d --build
docker image prune -f
```

## Logs

```bash
docker compose logs -f voxproof
docker compose exec voxproof python -m app.cli run finance_voice_agent
```
