# Deploying Tailored Tuition with HTTPS

This guide puts the app on one small server with its own domain and automatic HTTPS. It assumes no
prior server experience; each step says what to type and how to check it worked. Budget about two
hours the first time, plus waiting for DNS.

What runs on the server (all in Docker, from `docker-compose.prod.yml`):

| Service | Job | Reachable from the internet? |
|---|---|---|
| `caddy` | HTTPS front door; gets and renews certificates automatically | Yes (ports 80 and 443) |
| `frontend` | The website (Next.js) | No, only through Caddy |
| `backend` | The API, tutoring logic, calls to Claude | No, only through the frontend |
| `db` | Postgres database | No, on an internal-only network |

## 1. Before you start

You need:
- **A server (VPS)**: 2 vCPU, 4 GB RAM, 40 GB disk, Ubuntu 24.04 LTS, in a region near your users
  (for India: e.g. AWS Lightsail Mumbai or DigitalOcean Bangalore; roughly US$20–25 a month — check
  current prices). Use SSH-key login, not a password.
- **A domain name** (e.g. `tuition.example.com`), from any registrar.
- **An email-sending provider** for verification and password-reset emails (e.g. Amazon SES, Brevo,
  Postmark or Zoho Mail). You need its SMTP host, port, username and password.
- **An Anthropic API key**, with a monthly **spend limit** set in the Anthropic Console.
- **Access to the private GitHub repository** that holds this project.

## 2. Point the domain at the server

At your registrar, add a DNS **A record**: name `tuition` (or `@` for the bare domain), value = your
server's public IPv4 address. Check from your laptop (it can take minutes to hours):

```bash
nslookup tuition.example.com     # must show the server's IP
```

Caddy cannot get a certificate until this resolves to the server.

## 3. Prepare the server

SSH in, then:

```bash
sudo apt update && sudo apt -y upgrade
# Docker Engine + Compose plugin (official install script; review it first if you prefer:
# https://docs.docker.com/engine/install/ubuntu/)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"      # then log out and back in
docker compose version                # should print a version

# Firewall: only SSH and web traffic
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
sudo ufw enable
```

Note: Docker publishes Caddy's ports itself; nothing else in the stack publishes ports, so the
database and backend stay unreachable from outside regardless of the firewall.

## 4. Get the code onto the server

The repository is private, so give the server read-only access with a **deploy key**:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/tuition_deploy -N ""
cat ~/.ssh/tuition_deploy.pub
```

On GitHub: repository → Settings → Deploy keys → Add deploy key → paste it, leave "Allow write
access" **off**. Then:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github-tuition
  HostName github.com
  IdentityFile ~/.ssh/tuition_deploy
EOF
sudo mkdir -p /opt/tailored-tuition && sudo chown "$USER" /opt/tailored-tuition
git clone git@github-tuition:<your-github-user>/tailored-tuition.git /opt/tailored-tuition
cd /opt/tailored-tuition
```

(If the project still lives in a subfolder of another repo, `cd` into that `tailored-tuition` folder
instead; every command below runs from the folder that contains `docker-compose.prod.yml`.)

## 5. Fill in the settings

```bash
cp deploy/.env.production.example deploy/.env.production
chmod 600 deploy/.env.production
openssl rand -hex 24          # use the output as POSTGRES_PASSWORD
nano deploy/.env.production    # replace every CHANGE_ME and the example domain
```

Things to get right:
- `DOMAIN` and `PUBLIC_URL` use your real domain; `PUBLIC_URL` starts with `https://`.
- `POSTGRES_PASSWORD`: letters and digits only (it is placed inside a URL).
- `SMTP_*`: from your email provider. `SMTP_FROM` must be an address on a domain you have verified
  with that provider.
- `ADMIN_EMAILS`: the guardian email(s) allowed to upload syllabus files.
- `SEED_DEMO_ACCOUNTS=false`.

The file is excluded from git by `deploy/.gitignore`. Never paste its contents into chats or tickets.
`./deploy/compose.sh` refuses to run while any `CHANGE_ME` remains, and the backend refuses to start
in production with insecure settings (no SMTP, insecure cookies, non-HTTPS URL, or SQLite).

## 6. Start it

```bash
./deploy/compose.sh up -d --build     # first build takes several minutes
./deploy/compose.sh ps                # all four services "running"/"healthy" after ~1 minute
```

The backend applies database migrations automatically when it starts.

## 7. Check it works

1. Open `https://tuition.example.com` — the browser shows a padlock and no warnings.
2. Open `https://tuition.example.com/api/health` — it shows `"status":"ok"` and `"llm_mode":"anthropic"`.
3. Sign up as a guardian with a real email address. The verification email should arrive within a
   minute (check spam). Click the link, add a test student, log in as that student, run a short
   tutoring session and a quiz.
4. Delete the test student from the guardian dashboard.

If something fails, see the logs (section 10).

## 8. Backups (do this on day one)

```bash
mkdir -p deploy/backups
./deploy/backup.sh                         # writes deploy/backups/tuition-<timestamp>.sql.gz
crontab -e                                  # add this line for a daily 02:15 backup:
15 2 * * * cd /opt/tailored-tuition && ./deploy/backup.sh >> deploy/backups/backup.log 2>&1
```

Backups older than 14 days are deleted automatically (`KEEP_DAYS` to change).

**Copy backups off the server.** A backup on the same disk is lost with the server. Use your VPS
provider's snapshot feature and/or copy `deploy/backups/` daily to private cloud storage (e.g. with
`rclone`). Backups contain children's personal data: keep the destination private and encrypted.

**Test a restore before launch**, ideally on a second test server:

```bash
./deploy/restore.sh deploy/backups/tuition-<timestamp>.sql.gz    # asks you to type RESTORE
```

It takes a safety backup first, stops the backend, replaces the database, and starts the backend again.

## 9. Updating

```bash
cd /opt/tailored-tuition
./deploy/backup.sh                   # always back up before an update
git pull
./deploy/compose.sh up -d --build    # rebuilds changed images; migrations run on start
./deploy/compose.sh ps
```

Update the server itself monthly: `sudo apt update && sudo apt -y upgrade` (reboot if asked).
Refresh base images occasionally: `./deploy/compose.sh pull && ./deploy/compose.sh up -d --build`.

## 10. Logs and troubleshooting

```bash
./deploy/compose.sh logs -f backend      # API errors, startup safety-check messages
./deploy/compose.sh logs -f caddy        # HTTPS/certificate problems, access log (JSON)
./deploy/compose.sh logs --tail 100 frontend
```

Logs rotate automatically (5 files × 10 MB per service).

| Symptom | Likely cause |
|---|---|
| Browser can't connect | DNS not pointing at the server yet, or firewall blocks 80/443 |
| Certificate error | DNS wrong, or port 80 blocked (Let's Encrypt needs it); see `logs caddy` |
| Backend keeps restarting | A setting fails the production safety check; the reason is in `logs backend` |
| No verification email | Wrong SMTP settings, or missing SPF/DKIM so mail is rejected or spam-filtered |

## 11. Rotating secrets

- **Anthropic key**: create a new key in the Console, put it in `deploy/.env.production`, run
  `./deploy/compose.sh up -d backend`, then delete the old key.
- **SMTP password**: same pattern.
- **Database password**: change it inside Postgres first, then in the env file:
  ```bash
  ./deploy/compose.sh exec db psql -U tuition -d tuition -c "ALTER USER tuition PASSWORD 'NEW_HEX_PASSWORD';"
  # edit POSTGRES_PASSWORD in deploy/.env.production to the same value, then:
  ./deploy/compose.sh up -d backend
  ```
- If the server itself may be compromised, rotate everything and rebuild on a fresh server from backups.

## 12. Pre-launch checklist

- [ ] Privacy notice: contact details and grievance officer filled in, reviewed, version bumped in
      `PRIVACY_POLICY_VERSION` if the text changed
- [ ] Legal review of the guardian-consent flow against India's DPDP Act and Rules (verifiable
      parental consent for under-18s)
- [ ] Anthropic monthly spend limit set; daily per-student limits reviewed
- [ ] Email domain has SPF, DKIM and DMARC records; a test email lands in the inbox, not spam
- [ ] Daily backups running, copied off the server, and a restore tested
- [ ] `ADMIN_EMAILS` set to the right people only
- [ ] Uptime monitoring set up (below)
- [ ] SSH: key-only login, root login disabled

## What this setup does NOT cover

Be clear-eyed about the limits of a single-server deployment:
- **One server, no redundancy.** If it goes down, the app is down until it is restarted or restored.
- **No autoscaling.** Fine for hundreds of students; plan a bigger setup before thousands.
- **No monitoring or alerting** beyond logs. At minimum, add a free uptime monitor (e.g. UptimeRobot
  or Better Stack) that checks `https://<your-domain>/api/health` every few minutes and emails you.
- **No off-site backups by default** (section 8 tells you how to add them).
- **No DDoS protection or web application firewall.** A CDN/proxy such as Cloudflare in front of
  Caddy adds this if needed.
- **Containers were not test-run in this repository's CI**: the configuration is validated with
  `docker compose config`, but do the section 7 checks on your server before inviting users.
