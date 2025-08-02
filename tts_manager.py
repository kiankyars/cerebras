import os
import wave
import threading
import time
from pathlib import Path
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    def speak_text(self, text: str) -> bool:
        """Convert text to speech and play it"""
        pass

class GeminiTTS(TTSProvider):
    """Gemini TTS implementation"""
    
    def __init__(self):
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=api_key)
    
    def speak_text(self, text: str) -> bool:
        try:
            # Generate speech using Gemini TTS
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=text,
                config=self.client.types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=self.client.types.SpeechConfig(
                        voice_config=self.client.types.VoiceConfig(
                            prebuilt_voice_config=self.client.types.PrebuiltVoiceConfig(
                                voice_name='Kore',
                            )
                        )
                    ),
                )
            )
            
            # Extract audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Save to temporary file and play
            temp_file = "temp_feedback.wav"
            self._save_wave_file(temp_file, audio_data)
            
            # Play the audio file
            os.system(f"afplay {temp_file}")  # macOS command to play audio
            
            # Clean up temporary file
            os.remove(temp_file)
            return True
            
        except Exception as e:
            print(f"Error generating or playing speech with Gemini: {e}")
            return False
    
    def _save_wave_file(self, filename, pcm, channels=1, rate=24000, sample_width=2):
        """Save PCM audio data to a wave file"""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

class ChatGPTTTS(TTSProvider):
    """ChatGPT TTS implementation"""
    
    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
    
    def speak_text(self, text: str) -> bool:
        try:
            speech_file_path = Path(__file__).parent / "temp_speech.mp3"
            
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=text,
                instructions="Speak in a cheerful and positive tone.",
            ) as response:
                response.stream_to_file(speech_file_path)
            
            # Play the audio file
            os.system(f"afplay {speech_file_path}")  # macOS command to play audio
            
            # Clean up temporary file
            speech_file_path.unlink(missing_ok=True)
            return True
            
        except Exception as e:
            print(f"Error generating or playing speech with ChatGPT: {e}")
            return False

class TTSManager:
    """Manages TTS providers and audio queue"""
    
    def __init__(self, provider: str = "gemini"):
        self.audio_queue = []
        self.audio_lock = threading.Lock()
        self.stop_event = threading.Event()
        
        # Initialize TTS provider
        if provider == "gemini":
            self.tts_provider = GeminiTTS()
        elif provider == "chatgpt":
            self.tts_provider = ChatGPTTTS()
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")
        
        # Start audio worker thread
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()
    
    def add_to_queue(self, text: str):
        """Add text to audio queue"""
        with self.audio_lock:
            self.audio_queue.append(text)
    
    def _audio_worker(self):
        """Background thread function to handle audio playback"""
        while not self.stop_event.is_set():
            with self.audio_lock:
                if self.audio_queue:
                    text = self.audio_queue.pop(0)
                else:
                    text = None
            if text:
                self.tts_provider.speak_text(text)
            else:
                time.sleep(0.1)  # Small delay to prevent busy waiting
    
    def stop(self):
        """Stop the TTS manager"""
        self.stop_event.set()
        self.audio_thread.join(timeout=1.0) 