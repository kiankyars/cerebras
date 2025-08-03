## Key Insights
- 🤸‍♂️ Real-time sports analytics is an untapped frontier: Using MediaPipe and AI models for live body tracking offers a unique intersection of hardware and software that could provide personalized coaching feedback instantly. This could disrupt traditional sports training by making high-level analysis accessible to everyday athletes.
- 🔄 The convergence of AI and real-time data streams opens new interaction paradigms: Whether in athletics, academic research, or social media, the ability to process and respond to live data dynamically creates opportunities for more interactive and personalized user experiences.

## Real-time AI Coaching Backend

This project implements a real-time AI coaching system that provides voice feedback based on video analysis.

### Features
- Captures video stream from webcam or video file at 1fps
- Analyzes frames using Google Gemini API
- Provides voice feedback through Gemini Text-to-Speech
- Supports multiple activities (basketball, yoga, guitar)
- Uses threading for non-blocking audio playback
- Clean shutdown with 'q' key press

### Setup
1. Install dependencies using uv:
   ```bash
   uv pip install -e .
   ```
   
2. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/)

3. Create a `.env` file in the project root with your API key:
   ```bash
   cp .env.example .env
   # Then edit .env to add your actual API key
   ```

### Usage
Run the AI coach backend with default settings (basketball activity, webcam input):
```bash
uv run ai_coach.py
```

Run with specific activity:
```bash
uv run ai_coach.py --activity=yoga
uv run ai_coach.py --activity=guitar
```

Run with video file input instead of webcam:
```bash
uv run ai_coach.py --video-source=path/to/your/video.mp4
```

Press 'q' while the video window is focused to quit the application cleanly.

### How it Works
1. Video frames are captured from the webcam or video file at 1fps
2. Each frame is sent to the Gemini API with an activity-specific coaching prompt
3. Gemini analyzes the frame and provides feedback
4. Feedback is converted to speech using Gemini Text-to-Speech model
5. Audio is played back in a separate thread to avoid blocking video capture
