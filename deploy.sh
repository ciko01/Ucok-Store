#!/bin/bash
# Ucok Store - Auto Deploy Script untuk VPS
# Version: 1.0.0
# Author: Kiro AI

set -e  # Exit on error

# Colors untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Jangan jalankan script ini sebagai root!"
    print_info "Jalankan sebagai user biasa, script akan request sudo jika perlu."
    exit 1
fi

# Detect OS
OS="unknown"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
fi

print_header "🚀 Ucok Store - Auto Deploy Script"
echo ""
print_info "OS Detected: $OS"
print_info "User: $(whoami)"
print_info "Working Directory: $(pwd)"
echo ""

# Konfirmasi
read -p "Deploy Ucok Store ke VPS ini? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Deployment dibatalkan."
    exit 1
fi

# Step 1: Update sistem
print_header "📦 Step 1: Update Sistem"
print_info "Updating package lists..."
sudo apt update -y
print_success "Package lists updated"

# Step 2: Install Dependencies
print_header "📦 Step 2: Install Dependencies"

# Python
if ! command -v python3 &> /dev/null; then
    print_info "Installing Python 3..."
    sudo apt install python3 python3-pip python3-venv -y
    print_success "Python 3 installed"
else
    print_success "Python 3 already installed: $(python3 --version)"
fi

# Node.js
if ! command -v node &> /dev/null; then
    print_info "Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install nodejs -y
    print_success "Node.js installed"
else
    NODE_VERSION=$(node --version)
    print_success "Node.js already installed: $NODE_VERSION"
fi

# Git
if ! command -v git &> /dev/null; then
    print_info "Installing Git..."
    sudo apt install git -y
    print_success "Git installed"
else
    print_success "Git already installed"
fi

# PM2
if ! command -v pm2 &> /dev/null; then
    print_info "Installing PM2..."
    sudo npm install -g pm2
    print_success "PM2 installed"
else
    print_success "PM2 already installed"
fi

# Nginx (optional)
read -p "Install Nginx reverse proxy? (y/n): " -n 1 -r
echo
INSTALL_NGINX=false
if [[ $REPLY =~ ^[Yy]$ ]]; then
    INSTALL_NGINX=true
    if ! command -v nginx &> /dev/null; then
        print_info "Installing Nginx..."
        sudo apt install nginx -y
        print_success "Nginx installed"
    else
        print_success "Nginx already installed"
    fi
fi

# Step 3: Clone atau Update Repository
print_header "📥 Step 3: Setup Project"

PROJECT_DIR="$HOME/Ucok-Store"

if [ -d "$PROJECT_DIR" ]; then
    print_warning "Directory $PROJECT_DIR sudah ada"
    read -p "Pull update dari Git? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$PROJECT_DIR"
        git pull
        print_success "Repository updated"
    fi
else
    print_info "Cloning repository..."
    read -p "Enter Git repository URL (atau tekan Enter untuk skip): " REPO_URL
    if [ -n "$REPO_URL" ]; then
        git clone "$REPO_URL" "$PROJECT_DIR"
        print_success "Repository cloned"
    else
        print_warning "Skip cloning. Pastikan kode sudah ada di $PROJECT_DIR"
        mkdir -p "$PROJECT_DIR"
    fi
fi

cd "$PROJECT_DIR"

# Step 4: Setup Python Virtual Environment
print_header "🐍 Step 4: Setup Python Environment"

if [ -d "venv" ]; then
    print_info "Virtual environment sudah ada, skip..."
else
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

print_info "Activating virtual environment..."
source venv/bin/activate

print_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Python dependencies installed"
else
    print_warning "requirements.txt not found, skip..."
fi

# Step 5: Setup Webapp
print_header "⚛️ Step 5: Setup Webapp (Next.js)"

if [ -d "webapp" ]; then
    cd webapp
    
    if [ ! -d "node_modules" ]; then
        print_info "Installing Node.js dependencies..."
        npm install
        print_success "Node.js dependencies installed"
    else
        print_info "Node modules already installed, updating..."
        npm install
    fi
    
    print_info "Building webapp..."
    npm run build
    print_success "Webapp built successfully"
    
    cd ..
else
    print_warning "Webapp directory not found, skip..."
fi

# Step 6: Configure Environment Variables
print_header "⚙️ Step 6: Configure Environment"

if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    
    # Get VPS IP
    VPS_IP=$(curl -s ifconfig.me)
    print_info "Detected VPS IP: $VPS_IP"
    
    # Interactive prompts
    read -p "Enter Telegram Bot Token: " BOT_TOKEN
    read -p "Enter WEBAPP_ORIGIN (default: http://$VPS_IP:3000): " WEBAPP_ORIGIN
    WEBAPP_ORIGIN=${WEBAPP_ORIGIN:-"http://$VPS_IP:3000"}
    
    # Create .env
    cat > .env << EOF
# Telegram Bot
TELEGRAM_BOT_TOKEN=$BOT_TOKEN

# Database
DATABASE_URL=sqlite:///./ucok_store.db

# Webapp
WEBAPP_ORIGIN=$WEBAPP_ORIGIN
NEXTAUTH_URL=$WEBAPP_ORIGIN
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# API
API_URL=http://localhost:8000
API_HOST=0.0.0.0
API_PORT=8000

# Web Checker
WEBCHECKER_URL=http://localhost:8001
WEBCHECKER_HOST=0.0.0.0
WEBCHECKER_PORT=8001

# Webapp Server
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=3000
EOF
    
    print_success ".env file created"
else
    print_success ".env file already exists"
fi

# Step 7: Initialize Database
print_header "🗄️ Step 7: Initialize Database"

if [ -f "ucok_store.db" ]; then
    print_info "Database already exists, skip initialization..."
else
    print_info "Initializing database..."
    # Database akan auto-create saat startup API
    print_success "Database will be initialized on first API start"
fi

# Step 8: Setup Firewall
print_header "🔥 Step 8: Configure Firewall"

if command -v ufw &> /dev/null; then
    print_info "Configuring UFW..."
    
    sudo ufw allow 22/tcp comment 'SSH'
    sudo ufw allow 3000/tcp comment 'Webapp'
    sudo ufw allow 8000/tcp comment 'API'
    sudo ufw allow 8001/tcp comment 'Webchecker'
    
    # Enable UFW jika belum
    sudo ufw --force enable
    
    print_success "Firewall configured"
    sudo ufw status
else
    print_warning "UFW not installed, skip firewall configuration"
fi

# Step 9: Setup PM2
print_header "🔄 Step 9: Setup PM2 Process Manager"

# Stop existing processes
pm2 delete ucok-store 2>/dev/null || true

# Start new process
print_info "Starting Ucok Store with PM2..."
pm2 start run_complete.py --name ucok-store --interpreter python3 --cwd "$PROJECT_DIR"

# Setup auto-restart on reboot
print_info "Setting up PM2 startup..."
pm2 startup | tail -n 1 | sudo bash
pm2 save

print_success "PM2 configured and service started"

# Step 10: Setup Nginx (optional)
if [ "$INSTALL_NGINX" = true ]; then
    print_header "🌐 Step 10: Configure Nginx"
    
    read -p "Enter domain name (atau tekan Enter untuk skip reverse proxy): " DOMAIN_NAME
    
    if [ -n "$DOMAIN_NAME" ]; then
        NGINX_CONFIG="/etc/nginx/sites-available/ucok-store"
        
        sudo tee "$NGINX_CONFIG" > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Webapp
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_cache_bypass \$http_upgrade;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # Webchecker
    location /webchecker {
        rewrite ^/webchecker/(.*) /\$1 break;
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
EOF
        
        # Enable site
        sudo ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
        
        # Test config
        if sudo nginx -t; then
            sudo systemctl restart nginx
            print_success "Nginx configured for $DOMAIN_NAME"
        else
            print_error "Nginx configuration error"
        fi
    else
        print_info "Skip Nginx reverse proxy configuration"
    fi
fi

# Step 11: Verification
print_header "✅ Step 11: Verification"

sleep 5  # Wait for services to start

# Check PM2
print_info "Checking PM2 status..."
pm2 status

# Check ports
print_info "\nChecking listening ports..."
netstat -tulpn 2>/dev/null | grep -E ":(3000|8000|8001)" || true

# Test endpoints
print_info "\nTesting endpoints..."

# Test API
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health | grep -q "200"; then
    print_success "API is responding (port 8000)"
else
    print_warning "API not responding yet (port 8000)"
fi

# Test Webchecker
if curl -s -X POST http://localhost:8001/api/cleanup 2>&1 | grep -q "detail"; then
    print_success "Webchecker is responding (port 8001)"
else
    print_warning "Webchecker not responding yet (port 8001)"
fi

# Final summary
print_header "🎉 Deployment Complete!"

echo ""
print_info "Services Status:"
echo "  - Ucok Store: pm2 list"
echo "  - Logs: pm2 logs ucok-store"
echo "  - Restart: pm2 restart ucok-store"
echo ""

print_info "Access URLs:"
if [ -n "$DOMAIN_NAME" ]; then
    echo "  - Webapp: http://$DOMAIN_NAME"
    echo "  - API: http://$DOMAIN_NAME/api/health"
else
    echo "  - Webapp: http://$VPS_IP:3000"
    echo "  - API: http://$VPS_IP:8000/api/health"
    echo "  - Webchecker: http://$VPS_IP:8001"
fi
echo ""

print_info "Useful Commands:"
echo "  - View logs: pm2 logs ucok-store"
echo "  - Monitor: pm2 monit"
echo "  - Restart: pm2 restart ucok-store"
echo "  - Stop: pm2 stop ucok-store"
echo "  - Update code: cd $PROJECT_DIR && git pull && pm2 restart ucok-store"
echo ""

print_success "Setup selesai! Bot Telegram seharusnya sudah aktif 🤖"
print_info "Test dengan mengirim /start ke bot Telegram"
echo ""
