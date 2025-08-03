You are building a real-time AI coaching backend. Create a Python application that:

INPUT: Video stream (webcam) at 1fps
OUTPUT: Voice feedback via text-to-speech

CORE PIPELINE:
1. Capture video frames at 1fps
2. Send to Gemini API with prompt template
3. Get text response
4. Convert to speech and play audio

PROMPT TEMPLATE:
"You are a real-time coach. Analyze this video frame. If wrong activity detected, say 'Wrong activity'. Otherwise, provide specific form feedback like Michael Jordan would. Keep responses under 50 words. Be encouraging but direct."

TECH STACK:
- OpenCV for video capture
- Google Gemini API for analysis
- pyttsx3 for text-to-speech
- Threading for non-blocking audio

REQUIREMENTS:
- Process at 1fps (Gemini limitation)
- Real-time voice feedback
- Handle wrong activity detection
- Clean shutdown on 'q' key

Create complete working backend with threading.
Gemini and Cerebrus TTS are not working.
COACH STYLE WILL BE ANOTHER HYPERPAREMTER, THIS IS GOING TO BE SO GOOD, AND BITTER-LESSON PILLED

I'll have to learn to start dealing with these errors because they seem inevitable. {'code': 500, 'message': 'An internal error has occurred. Please retry or report in https://developers.generativeai.google/guide/troubleshooting', 'status': 'INTERNAL'}}

rember that the guy used 1 fps, so I need to play with that