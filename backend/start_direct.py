#!/usr/bin/env python3
"""
Start the direct web interface for NED backend
"""

import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from direct_web import create_app
from aiohttp import web

if __name__ == '__main__':
    print("🚀 Starting NED Direct Backend...")
    print("📱 Web interface will be available at: http://localhost:8080")
    print("🎯 This bypasses FastAPI and uses the backend directly")
    print("⏱️  Rate limiting: 10s between API calls")
    print("🛑 Press Ctrl+C to stop")
    
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080) 