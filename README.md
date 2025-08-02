<div align="center">
    <img alt="Logo" src="docs/icon.png" width="100" />
</div>
<h1 align="center">
    Vibe Draw - Cursor for 3D Modeling
</h1>
<p align="center">
   turn your roughest sketches into stunning 3D worlds by vibe drawing
</p>

https://github.com/user-attachments/assets/a3c804e1-b208-4855-b285-d571bedf1f3e

![Vibe Draw UI](docs/ui.jpeg)

![Vibe Draw 2D Canvas](docs/canvas.jpeg)

![Vibe Draw 3D World](docs/world.jpeg)

## How It Works

1. **Sketch**: Draw freely on the 2D canvas
2. **Enhance**: Use the "Improve Drawing" button to refine sketches into detailed, polished drawings
3. **Transform**: Click "Make 3D" to convert your drawing into a 3D model
4. **Build**: Add your 3D models to the world by switching to the 3D World tab
5. **Iterate**: Edit and refine your 3D models by sketching or by writing a text prompt
6. **Export**: Export your 3D world with 1 click in a standard format (.glTF) to integrate with your pre-existing tooling 

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- API keys for Claude, Gemini, Cerebras, and PiAPI

### Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

### Backend Setup

```bash
cd backend

# remember to add api keys
cp .env.example .env

docker compose up
```

## Architecture

### Frontend

- **Next.js & React**: Responsive, user-friendly UI
- **Three.js**: Rendering interactive 3D models
- **TLDraw**: Powerful 2D drawing canvas
- **Zustand**: State management

### Backend

- **FastAPI**: High-performance API framework
- **Celery**: Asynchronous task queue for AI operations
- **Redis**: Pub/Sub for real-time updates and task result storage
- **SSE (Server-Sent Events)**: Real-time progress updates

## Inspiration

Creativity is often constrained by technical skills or complex software. Vibe Draw makes 3D modeling accessible to anyone regardless of artistic or technical abilities.

Our goal is to empower people to freely express their imagination and bring their ideas effortlessly into 3D worlds.

## License

[AGPL](LICENSE)


# Vibe-Draw - Cerebras optional setup

Since Cerebras pricing so expensive, I tried making it optional. 

## Prerequisites

* Node.js 18+
* Python 3.10+
* Redis
* API keys for:
  * Claude (Anthropic)
  * Gemini (Google)
  * PiAPI Trellis (for 3D model generation)
  * Cerebras (optional)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/frybitsinc/vibe-draw.git
cd vibe-draw
```

### 2. Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.template .env
# Edit .env file and add your API keys
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

## Running the Application

You can run the application in two ways:

### Option 1: Using the start script (recommended)

This script will start all required services in one command:

```bash
cd vibe-draw
chmod +x start-vibe-draw.sh  # Make the script executable (first time only)
./start-vibe-draw.sh
```

### Option 2: Running each component separately

You'll need three terminal windows for this approach:

#### Terminal 1: Start Redis and Celery Worker
```bash
# Make sure Redis is running (install if needed)
# Verify Redis is running: redis-cli ping should return PONG

cd backend
source venv/bin/activate
celery -A worker worker --loglevel=info
```

#### Terminal 2: Start the Backend API
```bash
cd backend
source venv/bin/activate
python run.py
```

#### Terminal 3: Start the Frontend
```bash
cd frontend
npm run dev
```

## Accessing the Application

Once all components are running, open your browser and go to:
```
http://localhost:3000
```

## How to Use

1. Draw a sketch in the 2D Canvas tab
2. Click "Make 3D" to convert your drawing into a 3D model
3. The 3D model will appear on the right
4. You can switch to the 3D World tab to interact with the model

## Troubleshooting

### API Errors
- Verify that all API keys are correctly added to your `.env` file
- Check that Redis is running: `redis-cli ping` should return `PONG`

### Frontend Errors
- If you see "window is not defined" errors, it's due to server-side rendering issues. The project should handle these automatically.
- Clear your browser cache if you experience unusual behavior

### Backend Errors
- Check logs for any specific error messages
- Verify Python version (3.10+ required)
- Ensure all dependencies are installed correctly

## Notes

- The Cerebras API is optional. The application will use a mock implementation if no API key is provided.
- For optimal performance, ensure your computer meets the minimum requirements for running AI-based applications.