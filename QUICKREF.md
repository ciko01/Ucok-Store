# 🚀 Ucok Store - Quick Reference

Cheat sheet untuk command yang sering dipakai.

---

## 📦 Deployment

```bash
# Initial deployment
./deploy.sh

# Update code & restart
./update.sh

# Health check
./health-check.sh
```

---

## 🔄 PM2 Commands

```bash
# Status
pm2 status
pm2 monit                    # Real-time monitoring

# Logs
pm2 logs ucok-store          # Tail logs
pm2 logs ucok-store --lines 100
pm2 logs ucok-store --err    # Only errors

# Restart
pm2 restart ucok-store
pm2 reload ucok-store        # Zero-downtime restart

# Stop/Start
pm2 stop ucok-store
pm2 start ucok-store

# Delete
pm2 delete ucok-store
```

---

## 🐛 Debugging

```bash
# View recent errors
pm2 logs ucok-store --err --lines 50

# Check what's using ports
sudo lsof -i :8000
sudo lsof -i :8001
sudo lsof -i :3000

# Kill stuck process
pm2 stop ucok-store
pkill -9 python3
pm2 start ucok-store

# Test endpoints
curl http://localhost:8000/api/health
curl -X POST http://localhost:8001/api/cleanup
curl http://localhost:3000
```

---

## 📊 Monitoring

```bash
# System resources
free -h                      # Memory
df -h                        # Disk
htop                         # CPU & processes

# Network
netstat -tulpn               # All ports
ss -tulpn                    # Modern alternative

# PM2 metrics
pm2 monit                    # Interactive
pm2 list                     # Simple list
```

---

## 🗄️ Database

```bash
# Backup
cp ucok_store.db ucok_store.db.backup.$(date +%Y%m%d)

# Restore
pm2 stop ucok-store
cp ucok_store.db.backup.20260814 ucok_store.db
pm2 start ucok-store

# View database
sqlite3 ucok_store.db
.tables
.quit
```

---

## 🔥 Firewall

```bash
# Status
sudo ufw status

# Allow port
sudo ufw allow 8000

# Delete rule
sudo ufw delete allow 8000

# Reset
sudo ufw disable
sudo ufw reset
```

---

## 🌐 Nginx

```bash
# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Restart
sudo systemctl restart nginx

# Status
sudo systemctl status nginx

# Logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 🔐 SSL/HTTPS

```bash
# Get certificate
sudo certbot --nginx -d your-domain.com

# Renew (auto via cron)
sudo certbot renew --dry-run

# Force renew
sudo certbot renew --force-renewal
```

---

## 📦 Updates

```bash
# Full update
cd ~/Ucok-Store
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
cd webapp && npm install && npm run build && cd ..
pm2 restart ucok-store

# Python only
source venv/bin/activate
pip install -r requirements.txt --upgrade
pm2 restart ucok-store

# Webapp only
cd webapp
npm install
npm run build
cd ..
pm2 restart ucok-store
```

---

## 🧹 Cleanup

```bash
# Clear PM2 logs
pm2 flush

# Clear old logs
rm -f ~/.pm2/logs/*

# Clear pip cache
pip cache purge

# Clear npm cache
npm cache clean --force

# Remove old backups
find ~/Ucok-Store -name "*.backup.*" -mtime +30 -delete
```

---

## 🆘 Emergency

```bash
# Service completely down
pm2 delete ucok-store
pm2 start run_complete.py --name ucok-store --interpreter python3
pm2 save

# Port conflicts
sudo lsof -ti :8000 | xargs kill -9
sudo lsof -ti :8001 | xargs kill -9
sudo lsof -ti :3000 | xargs kill -9
pm2 restart ucok-store

# Out of memory
pm2 stop ucok-store
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
pm2 start ucok-store

# Database corrupted
pm2 stop ucok-store
cp ucok_store.db.backup.* ucok_store.db
pm2 start ucok-store
```

---

## 📈 Performance Tuning

```bash
# Increase PM2 instances (cluster mode)
pm2 delete ucok-store
pm2 start run_complete.py --name ucok-store --interpreter python3 -i max

# Set memory limit
pm2 restart ucok-store --max-memory-restart 1G

# Enable PM2 logrotate
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

---

## 🔍 Useful One-Liners

```bash
# Find large files
find ~/Ucok-Store -type f -size +100M

# Count cookies
find ~/Ucok-Store/stok/netflix -name "*.txt" | wc -l

# Check bot connection
pm2 logs ucok-store --lines 100 | grep -i "bot\|telegram"

# Monitor cleanup progress
watch -n 1 'curl -s http://localhost:8001/api/session/cleanup_*/progress | jq'

# Restart on failure (auto-restart)
pm2 start run_complete.py --name ucok-store --interpreter python3 --max-restarts 10
```

---

## 💡 Tips

1. **Always backup before update**: `./health-check.sh && cp ucok_store.db ucok_store.db.backup`
2. **Monitor after deploy**: `pm2 logs ucok-store --lines 100`
3. **Test endpoints**: `curl http://localhost:8000/api/health`
4. **Check disk space regularly**: `df -h`
5. **Setup monitoring alerts**: Use PM2 Plus or custom monitoring
6. **Keep logs clean**: Use log rotation
7. **Update regularly**: `./update.sh` weekly
8. **Backup database daily**: Add to crontab

---

## 📞 Emergency Contacts

- **Health check**: `./health-check.sh`
- **Logs**: `pm2 logs ucok-store`
- **Status**: `pm2 status`
- **Restart**: `pm2 restart ucok-store`

---

**Last Updated**: 2026-08-14
