import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="NED API", version="0.1.0")
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "message": "NED API is running"}
    
    @app.get("/")
    async def root():
        return {"message": "NED API is running"}
    
    # Import other modules only if they exist
    try:
        from utils.config_manager import ConfigManager
        config_manager = ConfigManager("configs")
        
        @app.get("/configs")
        async def list_configs():
            configs = config_manager.list_all_configs()
            return {"configs": configs}
            
    except ImportError as e:
        print(f"Warning: Could not import config_manager: {e}")
    
    # Import other routes if modules exist
    try:
        from app import *
    except ImportError as e:
        print(f"Warning: Could not import full app: {e}")
        
except ImportError as e:
    print(f"Critical error: {e}")
    raise 