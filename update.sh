#!/bin/bash
# Ucok Store - Update Script
# Quick update script untuk pull changes dari Git dan restart services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header "🔄 Ucok Store - Update Script"

PROJECT_DIR="$HOME/Ucok-Store"

if [ ! -d "$PROJECT_DIR" ]; then
    print_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Backup database
print_info "Creating database backup..."
if [ -f "ucok_store.db" ]; then
    cp ucok_store.db "ucok_store.db.backup.$(date +%Y%m%d_%H%M%S)"
    print_success "Database backed up"
fi

# Pull latest changes
print_info "Pulling latest changes from Git..."
git pull
print_success "Code updated"

# Update Python dependencies
print_info "Updating Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt --upgrade
print_success "Python dependencies updated"

# Update webapp dependencies (jika ada perubahan di package.json)
if [ -d "webapp" ]; then
    cd webapp
    
    if git diff HEAD@{1} HEAD -- package.json | grep -q "^+"; then
        print_info "Updating webapp dependencies..."
        npm install
        print_success "Webapp dependencies updated"
    fi
    
    print_info "Rebuilding webapp..."
    npm run build
    print_success "Webapp rebuilt"
    
    cd ..
fi

# Restart services
print_info "Restarting services..."
pm2 restart ucok-store
print_success "Services restarted"

# Show status
echo ""
pm2 status
echo ""

print_success "Update complete! 🎉"
print_info "Check logs: pm2 logs ucok-store"
