#!/bin/bash
# Deploy Jocko AI Coach to server
# Usage: ./deploy.sh

SERVER="root@203.57.51.49"
APP_DIR="/opt/jocko"

echo "=== Deploying to $SERVER ==="

# 1. Create app directory on server
echo "Creating app directory..."
ssh $SERVER "mkdir -p $APP_DIR"

# 2. Copy code files (excluding sensitive data, venv, etc)
echo "Copying application files..."
rsync -avz --exclude='venv' \
          --exclude='__pycache__' \
          --exclude='*.db' \
          --exclude='.env' \
          --exclude='archive' \
          --exclude='*.log' \
          ./ $SERVER:$APP_DIR/

# 3. Check if config.py exists on server, if not warn user
echo "Checking server configuration..."
ssh $SERVER "if [ ! -f $APP_DIR/config.py ]; then echo 'WARNING: config.py not found on server!'; echo 'You need to copy your config.py or create a .env file on the server.'; fi"

echo "=== Deploy complete ==="
echo ""
echo "Next steps:"
echo "1. If this is first deploy, copy your config.py to the server:"
echo "   scp config.py $SERVER:$APP_DIR/"
echo ""
echo "2. Or create a .env file on the server:"
echo "   ssh $SERVER"
echo "   cd $APP_DIR"
echo "   nano .env"
echo ""
echo "3. Then SSH to server and start the bot:"
echo "   ssh $SERVER"
echo "   cd $APP_DIR && python main.py"
