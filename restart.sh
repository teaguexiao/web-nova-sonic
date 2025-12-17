#!/bin/bash
# Quick script to restart nova-sonic service
# Usage: ./restart.sh

echo "🔄 Restarting nova-sonic service..."
sudo systemctl restart nova-sonic

echo "⏳ Waiting for service to start..."
sleep 3

echo ""
echo "📊 Service Status:"
sudo systemctl status nova-sonic --no-pager | head -15

echo ""
echo "📝 Recent Logs:"
sudo journalctl -u nova-sonic -n 10 --no-pager

echo ""
echo "🔍 Port Check:"
ss -tlnp | grep 8100

echo ""
echo "✅ Restart complete!"
