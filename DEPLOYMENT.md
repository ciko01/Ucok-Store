# 🚀 Ucok Store - VPS Deployment Guide

Panduan lengkap untuk deploy Ucok Store ke VPS (Ubuntu/Debian).

---

## 📋 Requirements

- **VPS**: Ubuntu 20.04+ atau Debian 11+
- **RAM**: Minimal 2GB (recommended 4GB)
- **Storage**: Minimal 10GB free space
- **Network**: Public IP address
- **Domain** (optional): Untuk production dengan Nginx

---

## 🚀 Quick Deploy (Recommended)

### 1. Upload Project ke VPS

```bash
# Di local machine, push ke Git
git add .
git commit -m "Ready for deployment"
git push origin main

# Atau upload via SCP
scp -r Ucok-Store/ user@your-vps-ip:~/
```

### 2. Jalankan Auto Deploy Script

```bash
# SSH ke VPS
ssh user@your-vps-ip

# Masuk ke project directory
cd ~/Ucok-Store

# Buat script executable
chmod +x deploy.sh update.sh

# Jalankan deployment
./deploy.sh
```

Script akan otomatis:
- ✅ Install semua dependencies (Python, Node.js, PM2, etc.)
- ✅ Setup virtual environment
- ✅ Build webapp
- ✅ Configure environment variables
- ✅ Setup firewall
- ✅ Start services dengan PM2
- ✅ (Optional) Configure Nginx reverse proxy

**Input yang dibutuhkan:**
1. Telegram Bot Token
2. Domain name (optional)
3. Konfirmasi install Nginx (y/n)

---

## 📝 Manual Deployment

Jika prefer manual setup:

### 1. Install Dependencies

```bash
# Update sistem
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install PM2
sudo npm install -g pm2

# Install Git
sudo apt install git -y
```

### 2. Clone Project

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/Ucok-Store.git
cd Ucok-Store
```

### 3. Setup Python

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Setup Webapp

```bash
cd webapp
npm install
npm run build
cd ..
```

### 5. Configure Environment

```bash
# Create .env
cp .env.example .env
nano .env
```

**Minimal `.env` configuration:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///./ucok_store.db
WEBAPP_ORIGIN=http://your-vps-ip:3000
API_URL=http://localhost:8000
WEBCHECKER_URL=http://localhost:8001
```

### 6. Configure Firewall

```bash
sudo ufw allow 22      # SSH
sudo ufw allow 3000    # Webapp
sudo ufw allow 8000    # API
sudo ufw allow 8001    # Webchecker
sudo ufw enable
```

### 7. Start Services

```bash
# Start dengan PM2
pm2 start run_complete.py --name ucok-store --interpreter python3

# Setup auto-restart
pm2 startup
pm2 save
```

---

## 🔄 Update Deployment

Ketika ada perubahan code:

```bash
cd ~/Ucok-Store
./update.sh
```

Atau manual:

```bash
cd ~/Ucok-Store
git pull
source venv/bin/activate
pip install -r requirements.txt
cd webapp && npm run build && cd ..
pm2 restart ucok-store
```

---

## 🌐 Nginx Reverse Proxy (Production)

### Install Nginx

```bash
sudo apt install nginx -y
```

### Configure Site

```bash
sudo nano /etc/nginx/sites-available/ucok-store
```

**Configuration:**

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Webapp
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Webchecker
    location /webchecker {
        rewrite ^/webchecker/(.*) /$1 break;
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
    }
}
```

### Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/ucok-store /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL dengan Let's Encrypt (Optional)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

## 🛠️ Useful Commands

### PM2 Management

```bash
# View status
pm2 status

# View logs
pm2 logs ucok-store

# Real-time logs
pm2 logs ucok-store --lines 100 --raw

# Monitor resources
pm2 monit

# Restart service
pm2 restart ucok-store

# Stop service
pm2 stop ucok-store

# Delete from PM2
pm2 delete ucok-store
```

### System Monitoring

```bash
# Check ports
netstat -tulpn | grep -E ":(3000|8000|8001)"

# Check disk space
df -h

# Check memory
free -h

# Check processes
ps aux | grep python
```

### Database Management

```bash
# Backup database
cp ucok_store.db ucok_store.db.backup.$(date +%Y%m%d)

# Restore database
cp ucok_store.db.backup.20260814 ucok_store.db
pm2 restart ucok-store
```

### Logs

```bash
# PM2 logs
pm2 logs ucok-store --lines 200

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# System logs
sudo journalctl -u nginx -f
```

---

## 🐛 Troubleshooting

### Bot Tidak Connect

**Gejala:** Bot tidak respond di Telegram

**Solusi:**
```bash
# Check logs
pm2 logs ucok-store | grep -i telegram

# Check .env
cat .env | grep TELEGRAM_BOT_TOKEN

# Restart bot
pm2 restart ucok-store
```

### Webapp Error 503

**Gejala:** Webapp menampilkan "Backend tidak dapat dijangkau"

**Solusi:**
```bash
# Check API status
curl http://localhost:8000/api/health

# Check logs
pm2 logs ucok-store | grep -i error

# Restart services
pm2 restart ucok-store
```

### Database Locked

**Gejala:** Error "database is locked"

**Solusi:**
```bash
# Stop service
pm2 stop ucok-store

# Check processes
ps aux | grep python

# Kill hanging processes
pkill -9 python3

# Restart
pm2 restart ucok-store
```

### Port Already in Use

**Gejala:** Error "Address already in use"

**Solusi:**
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :8001
sudo lsof -i :3000

# Kill process
sudo kill -9 <PID>

# Restart
pm2 restart ucok-store
```

### Memory Issues

**Gejala:** Service restart sendiri, OOM errors

**Solusi:**
```bash
# Check memory usage
free -h
pm2 monit

# Set PM2 memory limit
pm2 stop ucok-store
pm2 start run_complete.py --name ucok-store --interpreter python3 --max-memory-restart 1G
pm2 save

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 Monitoring & Logs

### Setup PM2 Monitoring

```bash
# Enable PM2 web dashboard
pm2 web

# Enable PM2 monitoring (pm2.io)
pm2 link <secret> <public>
```

### Log Rotation

PM2 automatically handles log rotation. Manual configuration:

```bash
pm2 install pm2-logrotate

# Configure
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true
```

---

## 🔒 Security Best Practices

1. **SSH Key Authentication**
   ```bash
   # Disable password auth
   sudo nano /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   sudo systemctl restart sshd
   ```

2. **Firewall Rules**
   ```bash
   # Only allow necessary ports
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

3. **Regular Updates**
   ```bash
   # Weekly security updates
   sudo apt update && sudo apt upgrade -y
   ```

4. **Database Backups**
   ```bash
   # Add to crontab
   crontab -e
   # Add: 0 2 * * * cp ~/Ucok-Store/ucok_store.db ~/backups/ucok_store.db.$(date +\%Y\%m\%d)
   ```

---

## 📞 Support

Jika ada masalah:
1. Check logs: `pm2 logs ucok-store`
2. Check status: `pm2 status`
3. Restart: `pm2 restart ucok-store`

---

## 📜 License

MIT License - Ucok Store © 2026
