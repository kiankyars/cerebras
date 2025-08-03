# Roadmap

## Technical Architecture
### Frontend (Web App, IOS & Android by Friday August 8, 2025)
- Next.js/React (web-first, mobile responsive)
- getUserMedia() API for camera access
- MediaRecorder API for video capture
- WebSocket for real-time feedback
- Web Audio API for TTS playback

## UX
- FaceTime-style with overlay feedback
- Peloton-style Video-first interface
- The name of the activiaty you are doing is overlayed on the video

### Backend (Python + FastAPI)
- FastAPI REST API + WebSocket server
- OpenCV for video processing
- Gemini API for real-time analysis
- Multi-provider TTS (Gemini, ChatGPT)
- Video segmentation & analysis pipeline

### Infrastructure
- Supabase for user data & auth
- Supabase Storage for video files
- Real-time subscriptions via WebSocket


### Pricing Model
- **Two modes:** live (premium) upload video (FREE)
- Language will be any language

## Feedback Categories

### User Experience
- Progressive feedback - Start basic, get more detailed
- Time awareness - "You've been at this for 5 minutes"

### Personalization Hooks
- Skill level detection - "This looks like beginner form"
- Progress tracking - "You've improved since last time"
- Goal awareness - "Remember, you're working on flexibility"

## Future Features
- Statistics will be optional in the future like in bball from Farza
- I will eventually supply the previous recommendations in the prompt to the model so that it has context on what happened before
- You can choose the voice is another and the speed of the voice - this is going to be so fucking good
- I will also need to have max session lengths and video durations that are increased if you're on the premium plan
- Coaching style will be another hyperparameter, this is going to be so good, and bitter-lesson pilled
- memory on the user
- workouts with friends
- help docs: first tip will be to leave the camera stationary

## Technical Notes
- Gemini and Cerebras TTS are not working
- I'll have to learn to start dealing with these errors because they seem inevitable: `{'code': 500, 'message': 'An internal error has occurred. Please retry or report in https://developers.generativeai.google/guide/troubleshooting', 'status': 'INTERNAL'}}`
- Remember that the guy used 1 fps, so I need to play with that
- FPS and many other parameters will be tunable - this will be my hyperparameter tuning