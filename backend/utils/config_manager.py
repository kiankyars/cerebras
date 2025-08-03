"""Configuration management utilities for NED"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

class ConfigManager:
    """Manages coaching configurations organized by categories"""
    
    def __init__(self, configs_dir: str = "configs"):
        self.configs_dir = Path(configs_dir)
    
    def list_all_configs(self) -> List[Dict]:
        """List all available configurations with metadata"""
        configs = []
        
        if not self.configs_dir.exists():
            return configs
        
        for category_dir in self.configs_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category = category_dir.name
            for config_file in category_dir.glob("*.json"):
                try:
                    config = self.load_config_by_path(config_file)
                    configs.append({
                        "id": config_file.stem,
                        "category": category,
                        "name": config.get("activity", config_file.stem),
                        "description": config.get("description", ""),
                        "coach": config.get("coach", ""),
                        "skill_level": config.get("skill_level", ""),
                        "path": str(config_file)
                    })
                except Exception as e:
                    print(f"Error loading config {config_file}: {e}")
                    continue
        
        return sorted(configs, key=lambda x: (x["category"], x["name"]))
    
    def find_config_path(self, config_id: str) -> Optional[str]:
        """Find config file path by ID, searching all categories"""
        for category_dir in self.configs_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            config_file = category_dir / f"{config_id}.json"
            if config_file.exists():
                return str(config_file)
        
        return None
    
    def load_config_by_id(self, config_id: str) -> Optional[Dict]:
        """Load configuration by ID"""
        config_path = self.find_config_path(config_id)
        if not config_path:
            return None
        
        return self.load_config_by_path(config_path)
    
    def load_config_by_path(self, config_path: str) -> Dict:
        """Load configuration from file path"""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def list_categories(self) -> List[str]:
        """List all available categories"""
        categories = []
        for category_dir in self.configs_dir.iterdir():
            if category_dir.is_dir():
                categories.append(category_dir.name)
        return sorted(categories)
    
    def list_configs_by_category(self, category: str) -> List[Dict]:
        """List configurations for a specific category"""
        configs = self.list_all_configs()
        return [c for c in configs if c["category"] == category]