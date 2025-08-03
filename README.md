# NED

Real-time AI coaching for sports, fitness, music, and more using computer vision and voice feedback.

## 🚀 Quick Start

### Prerequisites
- Python 3.13+ with `uv` package manager
- Node.js 18+ with `npm`
- API Keys: `GEMINI_API_KEY` (required), `OPENAI_API_KEY` (optional)

### 1. Clone & Setup Environment
```bash
git clone <repository-url>
cd NED
cp .env.example .env
# Add your API keys to .env
```

### 2. Start Backend (Terminal 1)
```bash
cd backend
uv sync
export GEMINI_API_KEY="your_key_here"
uv run uvicorn app:app --reload
# Backend runs on http://localhost:8000
```

### 3. Start Frontend (Terminal 2)  
```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

### 4. Open Application
Visit [http://localhost:3000](http://localhost:3000) and start coaching!

## 🎯 Features

### **Live Coaching (Premium)**
- Real-time video analysis via webcam
- Instant AI feedback with voice synthesis
- FaceTime-style overlay interface
- Real-time form analysis and corrections

### **Video Upload (Free)**
- Upload videos for analysis
- Progress tracking during processing
- Download coached video with audio overlay
- Segment-by-segment feedback

### **Multi-Activity Support**
- **Sports**: Basketball, football, yoga, plyometrics
- **Health**: Sleep coaching and wellness
- **Music**: Guitar and instrument coaching
- **Cooking**: Culinary technique improvement

## 🏗 Architecture

### Frontend (Next.js + React)
- **Camera Access**: `getUserMedia()` API for webcam
- **Real-time Communication**: WebSocket with auto-reconnect
- **Audio Playback**: Web Speech API for TTS
- **State Management**: React hooks with error boundaries
- **Styling**: Tailwind CSS with responsive design

### Backend (Python + FastAPI)
- **Video Processing**: OpenCV for computer vision
- **AI Analysis**: Gemini API for real-time coaching
- **Audio Synthesis**: Multi-provider TTS (Gemini, ChatGPT)
- **Session Management**: WebSocket + REST API
- **Configuration**: Category-based coaching configs

### API Endpoints
```
GET  /health                     # Health check
GET  /configs                    # List all coaching configs
GET  /configs/categories         # List config categories
POST /sessions/upload            # Create video upload session
POST /sessions/live              # Create live coaching session  
GET  /sessions/{id}/download     # Download processed video
WebSocket /ws/{session_id}       # Real-time feedback
```

## 🔧 Configuration

### Coaching Configurations
Located in `backend/configs/` organized by category:
```
configs/
├── sports/          # Basketball, football, yoga, etc.
├── health/          # Sleep, wellness coaching
├── instruments/     # Guitar, piano, etc.
└── cooking/         # Culinary techniques
```

Each config includes:
```json
{
  "activity": "basketball",
  "coach": "Michael Jordan",
  "skill_level": "beginner", 
  "feedback_frequency": 10,
  "fps": 5,
  "max_response_length": 15
}
```

### Environment Variables
```bash
# Backend
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key  # Optional

# Frontend  
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 🛠 Development

### Backend Development
```bash
cd backend
uv run python ai_coach.py --video-source webcam --config configs/sports/basketball_config.json --tts gemini
```

### Frontend Development
```bash  
cd frontend
npm run dev      # Development server
npm run build    # Production build
npm run start    # Production server
```

### Testing
```bash
# Backend API test
curl http://localhost:8000/health
curl http://localhost:8000/configs

# Full integration test
# 1. Start both services
# 2. Visit http://localhost:3000
# 3. Select activity and start coaching
```

## 📁 Project Structure

```
NED/
├── backend/                 # Python FastAPI backend
│   ├── app.py              # Main FastAPI application
│   ├── ai_coach.py         # Core AI coaching logic
│   ├── tts_manager.py      # Text-to-speech management
│   ├── utils/              # Utilities and helpers
│   └── configs/            # Coaching configurations
├── frontend/               # Next.js React frontend  
│   ├── pages/              # Next.js pages
│   ├── components/         # React components
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utilities and config
│   └── styles/             # Tailwind CSS styles
├── data/                   # Sample videos and outputs
└── docs/                   # Documentation
```

## 🚀 Deployment

### Production Backend
```bash
cd backend
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

### Production Frontend
```bash
cd frontend  
npm run build
npm run start
```

### Docker (Coming Soon)
```bash
docker-compose up -d
```

## 🔮 Roadmap

- **Supabase Integration**: User accounts, session history, progress tracking
- **Advanced Features**: Progressive feedback, skill level detection
- **Social Features**: Share sessions, multiplayer workouts
- **Mobile App**: React Native version
- **AI Improvements**: Memory, context awareness, custom coaching styles

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for better coaching experiences**