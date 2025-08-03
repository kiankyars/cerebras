import cv2
import json
import threading
import time
import queue
import os
from google.generativeai import GenerativeModel
import google.generativeai as genai
from openai import OpenAI
import base64
import io
from PIL import Image

class AICoach:
    def __init__(self):
        self.config = self.load_config()
        self.setup_apis()
        self.video_queue = queue.Queue(maxsize=10)
        self.feedback_queue = queue.Queue()
        self.running = True
        
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "activity": "basketball",
                "goal": "improve form",
                "focus_on": "basics",
                "skill_level": "beginner",
                "custom_prompt": ""
            }
    
    def setup_apis(self):
        # Setup Gemini
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.gemini_model = GenerativeModel('gemini-1.5-flash')
        
        # Setup OpenAI for TTS
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Build system prompt
        self.system_prompt = f"""You are a real-time {self.config['activity']} coach. Analyze this video frame. 

VALIDATION:
- If wrong activity detected, say 'Wrong activity'
- If no movement, say 'No movement detected' 
- If poor visibility, say 'Poor visibility'

COACHING:
- Provide specific form feedback for {self.config['activity']}
- Focus on: {self.config['focus_on']}
- Goal: {self.config['goal']}
- Skill level: {self.config['skill_level']}

Keep responses under 50 words. Be encouraging but direct. Use 2-word max encouragement like 'Great form!' or 'Keep going!'"""

    def capture_video(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FPS, 1)
        
        frame_count = 0
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % 30 == 0:  # Process every 30th frame (1fps)
                if not self.video_queue.full():
                    self.video_queue.put(frame)
                    
        cap.release()

    def analyze_frame(self, frame):
        try:
            # Convert frame to base64
            _, buffer = cv2.imencode('.jpg', frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Create prompt with user custom prompt
            user_prompt = f"{self.config['custom_prompt']}\n\nAnalyze this frame:"
            
            # Send to Gemini
            response = self.gemini_model.generate_content([
                self.system_prompt,
                user_prompt,
                {"mime_type": "image/jpeg", "data": img_base64}
            ])
            
            return response.text.strip()
            
        except Exception as e:
            return f"Error analyzing frame: {str(e)}"

    def text_to_speech(self, text):
        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )
            
            # Save and play audio
            with open("feedback.mp3", "wb") as f:
                f.write(response.content)
            
            # Play audio (macOS)
            os.system("afplay feedback.mp3")
            
        except Exception as e:
            print(f"TTS Error: {str(e)}")

    def process_feedback(self):
        while self.running:
            try:
                feedback = self.feedback_queue.get(timeout=1)
                if feedback:
                    print(f"Coach: {feedback}")
                    self.text_to_speech(feedback)
            except queue.Empty:
                continue

    def main_loop(self):
        print("AI Coach starting... Press 'q' to quit")
        
        # Start threads
        video_thread = threading.Thread(target=self.capture_video)
        feedback_thread = threading.Thread(target=self.process_feedback)
        
        video_thread.start()
        feedback_thread.start()
        
        last_feedback_time = 0
        feedback_interval = 3  # Minimum seconds between feedback
        
        while self.running:
            try:
                frame = self.video_queue.get(timeout=1)
                current_time = time.time()
                
                if current_time - last_feedback_time >= feedback_interval:
                    feedback = self.analyze_frame(frame)
                    if feedback and not self.feedback_queue.full():
                        self.feedback_queue.put(feedback)
                        last_feedback_time = current_time
                        
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
                
        self.running = False
        video_thread.join()
        feedback_thread.join()
        print("AI Coach stopped")

if __name__ == "__main__":
    coach = AICoach()
    coach.main_loop()
