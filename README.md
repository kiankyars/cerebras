# AI Coach Backend

Real-time AI coaching system with video analysis and voice feedback.

## Setup

1. Install dependencies:
```bash
uv pip install -r requirements.txt
```

2. Set environment variables:
```bash
export GOOGLE_API_KEY="your_gemini_api_key"
export OPENAI_API_KEY="your_openai_api_key"
```

3. Configure activity in `config.json`:
```json
{
  "activity": "basketball",
  "goal": "improve shooting form", 
  "focus_on": "knee bend",
  "skill_level": "beginner",
  "custom_prompt": "Focus on my follow-through"
}
```

## Usage

Run the backend:
```bash
python ai_coach.py
```

Press 'q' to quit.

## Features

- **Real-time video analysis** at 1fps
- **Voice feedback** via OpenAI TTS
- **Configurable prompts** per activity
- **Threaded processing** for smooth operation
- **Activity validation** and error handling

## Architecture

```
Video Input → Gemini API → Text Response → OpenAI TTS → Voice Output
```

## Supported Activities

- Basketball
- Yoga  
- Guitar
- Custom (via config.json)
