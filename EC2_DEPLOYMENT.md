# EC2 Deployment Guide

## Running as a Service (systemd)

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/dataops.service
```

Paste the following:

```ini
[Unit]
Description=Fee Billing Excellence Analytic System
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/dataops/DataOps_agent
ExecStart=/home/ubuntu/dataops/DataOps_agent/venv/bin/python3 src/apps/main_app_full.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Save and exit: `Ctrl+X`, `Y`, `Enter`

### 2. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable dataops
sudo systemctl start dataops
```

### 3. Service Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl status dataops` | Check service status |
| `sudo systemctl start dataops` | Start the service |
| `sudo systemctl stop dataops` | Stop the service |
| `sudo systemctl restart dataops` | Restart the service |
| `sudo journalctl -u dataops -f` | View live logs |

---

## Updating from Git

### Standard Update

```bash
cd ~/dataops/DataOps_agent
git pull
sudo systemctl restart dataops
sudo systemctl status dataops
```

### Update with New Dependencies

```bash
cd ~/dataops/DataOps_agent
git pull
source venv/bin/activate
pip install -r config/requirements.txt
sudo systemctl restart dataops
```

### Quick Alias (Optional)

Add to `~/.bashrc`:

```bash
echo 'alias update-app="cd ~/dataops/DataOps_agent && git pull && sudo systemctl restart dataops && sudo systemctl status dataops"' >> ~/.bashrc
source ~/.bashrc
```

Then just run:

```bash
update-app
```

---

## Access the Application

Once running, access at: `http://<EC2-PUBLIC-IP>:7860`

Make sure port 7860 is open in your EC2 Security Group (Inbound Rules).
