# FR8 AI Coach Backend

## Directory Structure

```
backend/
├── app.py                 # FastAPI web server
├── start_server.py        # Server startup script
├── ai_coach.py           # Core AI coaching logic
├── tts_manager.py        # Text-to-speech management
├── list_models.py        # Model listing utilities
├── utils/
│   ├── __init__.py
│   └── config_manager.py # Configuration management
└── configs/              # Coaching configurations
    ├── sports/           # Sports-related configs
    │   ├── basketball_config.json
    │   ├── football_config.json
    │   ├── yoga_config.json
    │   └── ...
    ├── health/           # Health & wellness configs
    │   └── sleep_config.json
    ├── instruments/      # Musical instruments
    │   └── guitar_config.json
    └── cooking/          # Cooking & culinary
        └── ...
```

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set environment variables:**
   ```bash
   export GEMINI_API_KEY="your_key_here"
   export OPENAI_API_KEY="your_key_here"  # Optional for ChatGPT TTS
   ```

3. **Start the server:**
   ```bash
   cd backend
   uv run uvicorn app:app --reload
   # or
   uv run python start_server.py
   ```

4. **Test the API:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/configs/categories
   ```

## API Endpoints

### Configuration Management
- `GET /configs` - List all configurations
- `GET /configs/categories` - List configuration categories
- `GET /configs/categories/{category}` - List configs by category
- `GET /configs/{config_id}` - Get specific configuration

### Session Management
- `POST /sessions/upload` - Create video upload session
- `POST /sessions/live` - Create live camera session
- `POST /sessions/{id}/start` - Start analysis
- `GET /sessions/{id}/download` - Download processed video
- `DELETE /sessions/{id}` - Clean up session

### Real-time Communication
- `WebSocket /ws/{session_id}` - Real-time feedback and progress

## Configuration Structure

Each coaching configuration is a JSON file with:
```json
{
  "activity": "basketball",
  "coach": "Michael Jordan", 
  "skill_level": "beginner",
  "feedback_frequency": 10,
  "fps": 5,
  "max_response_length": 15,
  "description": "Basketball fundamentals coaching"
}
```

## Legacy CLI

The original command-line interface is still available:
```bash
uv run python ai_coach.py --video-source webcam --tts gemini --config configs/sports/basketball_config.json
```