# Deploying Jocko AI Coach to Server

## Overview

The deployment process separates **code** (goes to Git + server) from **secrets** (only on your local machine and server).

```
Your Local Machine          GitHub (Public)            Server
     │                           │                        │
     ├── config.py (with secrets)│                        │
     ├── venv/                   │                        │
     ├── *.db                    │                        │
     │                           │                        │
     └── Code files ────────────►├── config.py.example    │
                                 ├── main.py etc. ───────►├── Code files
                                 │                        │
                                 │                        ├── config.py (secrets)
                                 │                        └── OR .env file
```

## Step 1: Prepare Your Local Repository

### 1.1 Initialize Git (if not done)

```bash
cd ai-coach
git init
```

### 1.2 Check What's Being Committed

```bash
git status
```

You should see:
- **Green (staged)**: `main.py`, `coach.py`, `config.py.example`, `.gitignore`, etc.
- **Red (untracked)**: `config.py`, `venv/`, `*.db`, `.env`

### 1.3 Stage and Commit

```bash
git add .
git commit -m "Initial commit - Jocko AI Coach"
```

### 1.4 Push to GitHub (optional but recommended)

```bash
# Create a repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/jocko-ai-coach.git
git push -u origin main
```

## Step 2: First-Time Server Setup

### 2.1 SSH to Your Server

```bash
ssh root@203.57.51.49
```

### 2.2 Install Python (if not installed)

```bash
apt update
apt install -y python3 python3-pip python3-venv
```

### 2.3 Create App Directory

```bash
mkdir -p /opt/jocko
cd /opt/jocko
```

### 2.4 Get the Code

**Option A: From GitHub (if you pushed)**
```bash
git clone https://github.com/YOUR_USERNAME/jocko-ai-coach.git .
```

**Option B: From your local machine (using deploy script)**
```bash
# On your local machine:
./deploy.sh
```

## Step 3: Add Secrets to Server

**VERY IMPORTANT**: Your secrets are NOT in Git, so you must add them manually to the server.

### Option A: Copy your config.py (easiest)

From your **local machine**:

```bash
cd ai-coach
scp config.py root@203.57.51.49:/opt/jocko/
```

### Option B: Create .env file on server

SSH to server and create the file:

```bash
ssh root@203.57.51.49
cd /opt/jocko
nano .env
```

Paste your secrets:
```
TELEGRAM_BOT_TOKEN=8672706902:AAHvmdcJ-Y-QlZCGPMExWl21qjFBYDKQQOQ
TELEGRAM_CHAT_ID=8604616782
OPENAI_API_KEY=sk-proj-...
GARMIN_EMAIL=mattgreenhough@hotmail.com
GARMIN_PASSWORD=3590Matt..
PAYPAL_CLIENT_ID=AZwhnysZ4Kex8IfRx4cgmBeLvCmwMCbkFMtdaw-JSO6EOuX13FLxHsaXh6kvyixnt2bc1wocTFaX7D5c
PAYPAL_CLIENT_SECRET=ENZ4IfVmcfNM9P3r5RpXbpTRwdV8Kt5JKdRN0MF9kMstEwW5HlfhatV1d8ko3wHnxkVNUOVWEY0bHXRm
PAYPAL_RECIPIENT_EMAIL=breeanna.greenhough@gmail.com
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`

## Step 4: Install Dependencies on Server

```bash
ssh root@203.57.51.49
cd /opt/jocko
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Step 5: Test the Bot

```bash
venv/bin/python main.py
```

You should see "Bot started" or similar. Press `Ctrl+C` to stop.

## Step 6: Set Up Auto-Start (Systemd)

Create a service file:

```bash
ssh root@203.57.51.49
cat > /etc/systemd/system/jocko.service << 'EOF'
[Unit]
Description=Jocko AI Coach Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/jocko
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/jocko/venv/bin/python /opt/jocko/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable jocko
systemctl start jocko
```

Check status:
```bash
systemctl status jocko
```

View logs:
```bash
journalctl -u jocko -f
```

## Step 7: Future Updates

When you update code locally:

```bash
# 1. Commit changes
git add .
git commit -m "Your changes"

# 2. Push to GitHub
git push

# 3. Deploy to server
./deploy.sh

# 4. Restart service (if using systemd)
ssh root@203.57.51.49 "systemctl restart jocko"
```

## Summary of What Goes Where

| Location | Contains Secrets? | What's There |
|----------|------------------|--------------|
| Your local machine | YES | `config.py` with real tokens, `venv/`, `*.db` |
| GitHub | NO | Code only, `config.py.example`, `.gitignore` |
| Server | YES | `config.py` or `.env` with real tokens (copied manually) |

## Security Checklist

- [ ] `.gitignore` excludes `config.py`, `.env`, `venv/`, `*.db`
- [ ] You committed `config.py.example` (template) not `config.py` (real)
- [ ] Server has `config.py` or `.env` with real secrets
- [ ] GitHub repo is private (recommended) or public with NO secrets
- [ ] Server firewall configured (if needed)
