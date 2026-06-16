# Production Deployment

This directory contains a production-style deployment blueprint for the Streamlit travel recommender. The setup keeps Streamlit bound to loopback, exposes it through nginx, and publishes it through Cloudflare Tunnel without opening inbound ports.

```text
internet -> Cloudflare edge -> cloudflared -> 127.0.0.1:8500 (nginx)
                                                  |-> 127.0.0.1:8501
                                                  |-> 127.0.0.1:8502
                                                  |-> 127.0.0.1:8503
                                                  |-> 127.0.0.1:8504
```

The systemd examples assume the project is installed at `/opt/travel-recommender` and runs as a dedicated `travel-rec` user. Change those values before installing if your server layout differs.

## 1. Install the App

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin travel-rec
sudo mkdir -p /opt/travel-recommender
sudo chown -R travel-rec:travel-rec /opt/travel-recommender
```

Copy the repository to `/opt/travel-recommender`, then install dependencies in a virtual environment:

```bash
cd /opt/travel-recommender
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 2. nginx

```bash
sudo apt-get install -y nginx
sudo cp deploy/nginx-upgrade-map.conf /etc/nginx/conf.d/travel-rec-upgrade.conf
sudo cp deploy/nginx-travel-rec.conf /etc/nginx/sites-available/travel-rec
sudo ln -sf /etc/nginx/sites-available/travel-rec /etc/nginx/sites-enabled/travel-rec
sudo nginx -t
sudo systemctl reload nginx
```

## 3. Streamlit Replicas

```bash
sudo cp deploy/travel-rec@.service /etc/systemd/system/
sudo systemctl daemon-reload
for p in 8501 8502 8503 8504; do
    sudo systemctl enable --now "travel-rec@$p.service"
done
```

Check local health:

```bash
systemctl status 'travel-rec@*' --no-pager
curl -s http://127.0.0.1:8500/_stcore/health
```

## 4. Cloudflare Tunnel

Copy the example config and replace placeholders:

```bash
sudo mkdir -p /etc/cloudflared
sudo cp deploy/cloudflared-config.example.yml /etc/cloudflared/config.yml
```

Set the real tunnel UUID, credentials path, and hostname, then install the service:

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

## 5. Firewall

Cloudflare Tunnel only needs outbound connectivity.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

## Local Multi-Replica Smoke Test

For a local replica test without systemd:

```bash
./scripts/start-replicas.sh
```

## Operations

- Restart one replica: `sudo systemctl restart travel-rec@8502`.
- Rolling restart: restart `8501` through `8504` one by one and wait for `/_stcore/health`.
- Logs: `journalctl -u 'travel-rec@*' -f` and `/var/log/nginx/access.log`.
- Session logs: `data/sessions.jsonl`; concurrent appends are protected by `model/file_lock.py`.

## Security Notes

- Keep Streamlit on `127.0.0.1`; nginx and cloudflared are the only front doors.
- Do not commit `.streamlit/secrets.toml`, `.env`, tunnel credentials, or session logs.
- Keep XSRF protection enabled unless Cloudflare Access or another trusted access layer is explicitly handling that risk.
