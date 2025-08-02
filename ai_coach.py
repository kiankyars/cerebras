import cv2
import threading
import time
from google import genai
import os
from dotenv import load_dotenv
import argparse
import wave

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Initialize the new genai client
client = genai.Client(api_key=api_key)

# Activity-specific prompt templates
PROMPT_TEMPLATES = {
    "basketball": """You are a real-time basketball coach. Analyze this video frame of someone playing basketball. 
If they are not playing basketball, say 'Wrong activity'. Otherwise, provide specific form feedback like Michael Jordan would. 
Keep responses under 50 words. Be encouraging but direct.""",
    
    "yoga": """You are a real-time yoga coach. Analyze this video frame of someone doing yoga poses. 
If they are not doing yoga, say 'Wrong activity'. Otherwise, provide specific form feedback to improve their pose. 
Keep responses under 50 words. Be encouraging but direct.""",
    
    "guitar": """You are a real-time guitar instructor. Analyze this video frame of someone playing guitar. 
If they are not playing guitar, say 'Wrong activity'. Otherwise, provide specific feedback on their finger positioning and technique. 
Keep responses under 50 words. Be encouraging but direct."""
}

# Global variables for threading
audio_queue = []
audio_lock = threading.Lock()
stop_event = threading.Event()

def save_wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM audio data to a wave file"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def speak_text(text):
    """Convert text to speech using Gemini TTS and play it"""
    try:
        # Generate speech using Gemini TTS with new API
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=text,
            config=genai.types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai.types.SpeechConfig(
                    voice_config=genai.types.VoiceConfig(
                        prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
                            voice_name='Kore',  # You can change this to other available voices
                        )
                    )
                ),
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        
        # Save to temporary file and play
        temp_file = "temp_feedback.wav"
        save_wave_file(temp_file, audio_data)
        
        # Play the audio file
        os.system(f"afplay {temp_file}")  # macOS command to play audio
        
        # Clean up temporary file
        os.remove(temp_file)
        
    except Exception as e:
        print(f"Error generating or playing speech: {e}")

def audio_worker():
    """Background thread function to handle audio playback"""
    while not stop_event.is_set():
        with audio_lock:
            if audio_queue:
                text = audio_queue.pop(0)
            else:
                text = None
        if text:
            speak_text(text)
        else:
            time.sleep(0.1)  # Small delay to prevent busy waiting

def analyze_frame_with_gemini(frame, prompt_template):
    """Send frame to Gemini API for analysis"""
    try:
        # Convert frame to bytes for Gemini API
        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = buffer.tobytes()
        
        # Create the prompt with the image using new API
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                prompt_template,
                {'mime_type': 'image/jpeg', 'data': image_bytes}
            ]
        )
        
        return response.candidates[0].content.parts[0].text if response.candidates else "No feedback available"
    except Exception as e:
        print(f"Error analyzing frame with Gemini: {e}")
        return "Error in analysis"

def main(activity, video_source):
    """Main function to capture video and provide real-time coaching"""
    # Validate activity
    if activity not in PROMPT_TEMPLATES:
        print(f"Invalid activity: {activity}. Available activities: {list(PROMPT_TEMPLATES.keys())}")
        return
    
    prompt_template = PROMPT_TEMPLATES[activity]
    
    # Start audio thread
    audio_thread = threading.Thread(target=audio_worker, daemon=True)
    audio_thread.start()
    
    # Initialize video capture
    if video_source == "webcam":
        cap = cv2.VideoCapture(0)  # 0 for default webcam
        source_name = "webcam"
    else:
        cap = cv2.VideoCapture(video_source)
        source_name = video_source
    
    if not cap.isOpened():
        print(f"Error: Could not open video source: {source_name}")
        return
    
    print(f"AI Coach started for {activity} using {source_name}. Press 'q' to quit.")
    
    frame_count = 0
    last_analysis_time = 0
    
    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            
            if not ret:
                print("Error: Could not read frame")
                break
            
            frame_count += 1
            
            # Process at 1fps
            current_time = time.time()
            if current_time - last_analysis_time >= 1.0:  # At least 1 second between analyses
                # Analyze frame with Gemini
                feedback = analyze_frame_with_gemini(frame, prompt_template)
                print(f"Frame {frame_count}: {feedback}")
                
                # Add feedback to audio queue
                with audio_lock:
                    audio_queue.append(feedback)
                
                last_analysis_time = current_time
            
            # Display frame (optional, for debugging)
            cv2.imshow(f'AI Coach - {activity}', frame)
            
            # Check for quit key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_event.set()
                break
                
    except KeyboardInterrupt:
        print("Interrupted by user")
        stop_event.set()
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    
    # Wait for audio thread to finish
    stop_event.set()
    audio_thread.join(timeout=1.0)
    
    print("AI Coach stopped.")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Real-time AI Coach")
    parser.add_argument(
        "--activity", 
        choices=["basketball", "yoga", "guitar"], 
        default="basketball",
        help="Activity to coach (default: basketball)"
    )
    parser.add_argument(
        "--video-source", 
        default="webcam",
        help="Video source: 'webcam' for camera input, or path to video file (default: webcam)"
    )
    
    args = parser.parse_args()
    main(args.activity, args.video_source)
