# FR8 AI Coach Frontend

This is the frontend for the FR8 AI Coach application, built with Next.js and React.

## Features

- Live coaching mode (premium) using webcam and real-time analysis
- Video upload mode (free) for offline analysis
- FaceTime-style overlay feedback
- Peloton-style video-first interface
- WebSocket communication with backend for real-time updates
- Support for multiple activities (basketball, yoga, guitar, etc.)

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Implementation Details

### Live Coaching Mode

In live coaching mode, the frontend:
1. Accesses the user's webcam using `getUserMedia()`
2. Records video segments using `MediaRecorder`
3. Sends segments to the backend via WebSocket for real-time analysis
4. Displays feedback overlay on the video stream
5. Plays audio feedback using Web Audio API

### Video Upload Mode

In video upload mode, the frontend:
1. Allows users to upload video files
2. Creates an upload session with the backend
3. Displays progress during analysis
4. Shows feedback results
5. Provides download link for coached video

## Architecture

- Next.js 14 with React 18
- TypeScript for type safety
- Tailwind CSS for styling
- WebSocket for real-time communication
- MediaRecorder API for video capture
- Web Audio API for TTS playback

## Configuration

The frontend automatically fetches available coaching configurations from the backend on startup. Users can select from these configurations to customize their coaching experience.

## Future Enhancements

- Progressive feedback system
- Time awareness features
- Skill level detection
- Progress tracking
- Goal awareness
- Statistics dashboard
- User memory/context
- Multiplayer workouts
