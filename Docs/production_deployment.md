# Production Deployment Runbook

This guide describes how to provision, configure, secure, and deploy the complete CCTV AMC application to a production Linux server (e.g., Ubuntu 24.04 LTS) using Docker Compose.

---

## 1. System Requirements

* **Operating System**: Ubuntu 22.04 or 24.04 LTS (x86_64 or arm64)
* **Hardware**: Minimum 2 Cores CPU, 4 GB RAM, 40 GB SSD (or larger depending on attachment sizes)
* **Packages**: Docker Engine (v24+), Docker Compose (v2+), Certbot

---

## 2. DNS Settings

To support the white-label and tenant resolution system (e.g., resolving `durwankur.yourdomain.com` or `skyline.yourdomain.com` to the correct tenant branding), you must configure **Wildcard DNS** in your domain registrar:

1. **A Record**: Point `@` (root domain) to your server's public IP address (e.g., `123.45.67.89`).
2. **A Record**: Point `*` (wildcard subdomain) to your server's public IP address (e.g., `123.45.67.89`).
3. Alternatively, if using subdomains under a separate zone, set a wildcard CNAME pointing to the server's primary subdomain.

---

## 3. Server Provisioning & Installation

Log in to your newly provisioned Ubuntu server via SSH and execute the following setup commands:

### A. Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

### B. Install Docker & Docker Compose
```bash
# Add Docker's official GPG key:
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### C. Install Certbot
```bash
sudo apt install -y certbot
```

---

## 4. SSL Certificate Procurement (Let's Encrypt)

Since the application uses subdomains, we require a **Wildcard SSL Certificate**. Let's Encrypt requires a **DNS-01 Challenge** to verify wildcard domains.

### Get Wildcard Certificate via DNS Challenge
Execute this command on your local machine or server to obtain the DNS TXT instructions:
```bash
sudo certbot certonly \
  --manual \
  --preferred-challenges=dns \
  --email admin@yourdomain.com \
  --agree-tos \
  -d yourdomain.com \
  -d "*.yourdomain.com"
```

1. Certbot will output one or two DNS TXT record values (e.g., name: `_acme-challenge.yourdomain.com`, value: `XYZ123...`).
2. Go to your domain registrar DNS settings and add these TXT records.
3. Wait 2 minutes for propagation, then press Enter in the terminal to complete validation.
4. The certificates will be saved to `/etc/letsencrypt/live/yourdomain.com/`.

---

## 5. Bootstrap Application Deployment

### A. Clone the Repository
Clone your project repository into `/var/www/cctvApp`:
```bash
sudo mkdir -p /var/www/cctvApp
sudo chown -R $USER:$USER /var/www/cctvApp
git clone https://github.com/your-username/cctvApp.git /var/www/cctvApp
cd /var/www/cctvApp
```

### B. Set Up Environment Variables
Copy the production environment template:
```bash
cp production.env.example .env
```
Open `.env` in a text editor (e.g., `nano .env`) and populate all secrets:
1. Replace `your_strong_production_postgres_password_here` with a generated password (e.g., `openssl rand -hex 16`). Make sure it matches in `POSTGRES_PASSWORD`, `DATABASE_URL`, and `DATABASE_URL_SYNC`.
2. Generate a secure `JWT_SECRET_KEY` and `REDIS_PASSWORD`.
3. Provide valid SMTP credentials to allow the application to send notification alerts.

### C. Update Nginx SSL Domain Name
Edit `infra/nginx.prod.conf`:
- Locate lines 41 and 42.
- Change `/etc/letsencrypt/live/example.com/...` to `/etc/letsencrypt/live/yourdomain.com/...`.

---

## 6. Build and Launch

### A. Build and Start the Stack
Start all services in detached mode using the production docker-compose:
```bash
docker compose -f infra/docker-compose.prod.yml up -d --build
```

### B. Run Database Migrations
Run the Alembic schema migrations inside the running API container to set up RLS policies and schema components:
```bash
docker compose -f infra/docker-compose.prod.yml exec api alembic upgrade head
```

### C. Seed Initial Administrative User and Starter Tenant
To insert the platform administrator and the first starter tenant:
```bash
docker compose -f infra/docker-compose.prod.yml exec api python -m scripts.seed
```
*Platform Admin*: `platform@durwankur.ai` (Change password upon first login).

---

## 7. Operational Management

### A. Viewing Logs
* View aggregated application logs:
  ```bash
  docker compose -f infra/docker-compose.prod.yml logs -f
  ```
* View logs for a single service (e.g., background worker):
  ```bash
  docker compose -f infra/docker-compose.prod.yml logs -f worker
  ```

### B. Restarting Services
To apply updates or config changes:
```bash
docker compose -f infra/docker-compose.prod.yml restart
```

### C. Database Backups
To run an automated PostgreSQL logical dump (can be added to `crontab -e` daily):
```bash
docker compose -f infra/docker-compose.prod.yml exec -t postgres pg_dumpall -U cctv > /backup/db_$(date +%F).sql
```
For deep instructions on restoring the database in case of disaster, consult [backup_restore_runbook.md](file:///Users/dinesh/Work/cctvApp/Docs/backup_restore_runbook.md).
