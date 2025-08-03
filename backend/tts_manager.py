import os
import shutil
import subprocess
import threading
import time
import wave
from abc import ABC, abstractmethod
from pathlib import Path

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
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=api_key)
        self.types = types

    def speak_text(self, text: str) -> bool:
        try:
            # Generate speech using Gemini TTS
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=text,
                config=self.types.GenerateContentConfig(
                    speech_config=self.types.SpeechConfig(
                        voice_config=self.types.VoiceConfig(
                            prebuilt_voice_config=self.types.PrebuiltVoiceConfig(
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

            # Always play audio
            os.system(f"afplay {temp_file}")

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

    def __init__(self, voice_style: str = "cheerful"):
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.voice_style = voice_style

    def speak_text(self, text: str) -> bool:
        try:
            speech_file_path = Path(__file__).parent / "temp_speech.mp3"

            # Create voice instructions based on style
            voice_instructions = self._get_voice_instructions()

            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=text,
                instructions=voice_instructions,
            ) as response:
                response.stream_to_file(speech_file_path)

            # Always play audio
            os.system(f"afplay {speech_file_path}")

            # Clean up temporary file
            speech_file_path.unlink(missing_ok=True)
            return True

        except Exception as e:
            print(f"Error generating or playing speech with ChatGPT: {e}")
            return False

    def generate_audio_base64(self, text: str) -> str:
        """Generate audio and return as base64 string for frontend playback"""
        try:
            speech_file_path = Path(__file__).parent / "temp_speech.mp3"

            # Create voice instructions based on style
            voice_instructions = self._get_voice_instructions()

            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=text,
                instructions=voice_instructions,
            ) as response:
                response.stream_to_file(speech_file_path)

            # Read the file and convert to base64
            import base64
            with open(speech_file_path, "rb") as f:
                audio_data = f.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Clean up temporary file
            speech_file_path.unlink(missing_ok=True)
            
            return audio_base64

        except Exception as e:
            print(f"Error generating audio with ChatGPT: {e}")
            return None

    def _get_voice_instructions(self) -> str:
        """Get voice instructions based on selected style"""
        instructions = {
            "cheerful": "Speak in a cheerful and positive tone with enthusiasm.",
            "encouraging": "Speak in an encouraging and motivational tone.",
            "professional": "Speak in a professional and authoritative coaching tone.",
            "friendly": "Speak in a friendly and approachable tone.",
            "energetic": "Speak with high energy and excitement."
        }
        return instructions.get(self.voice_style, "Speak in a cheerful and positive tone.")

class TTSManager:
    """Manages TTS providers and audio queue"""

    def __init__(self, provider: str = "gemini", mode: str = "live", voice_style: str = "cheerful"):
        self.provider_name = provider
        self.mode = mode  # "live" or "video"
        self.voice_style = voice_style
        self.audio_queue = []
        self.audio_lock = threading.Lock()
        self.stop_event = threading.Event()

        # For video mode, store audio files with timestamps
        self.audio_files_with_timestamps = []

        # Initialize TTS provider
        if provider == "gemini":
            self.tts_provider = GeminiTTS()
        elif provider == "chatgpt":
            self.tts_provider = ChatGPTTTS(voice_style=voice_style)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")

        if mode == "live":
            # Start audio worker thread for live playback
            self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
            self.audio_thread.start()

    def add_to_queue(self, text: str, timestamp: float = None, interval_duration: float = None):
        """Add text to audio queue"""
        if self.mode == "live":
            with self.audio_lock:
                self.audio_queue.append(text)
        elif self.mode == "video":
            # Generate audio file for video overlay
            temp_audio_file = self._generate_audio_file(text, timestamp)
            if temp_audio_file:
                # Calculate timing so message ends at end of interval
                audio_duration = self.get_audio_duration(temp_audio_file)
                if interval_duration and audio_duration > 0:
                    # Calculate when to start so message ends at interval end
                    interval_end = timestamp + interval_duration
                    adjusted_start_time = max(timestamp, interval_end - audio_duration)
                else:
                    adjusted_start_time = timestamp
                
                self.audio_files_with_timestamps.append((temp_audio_file, adjusted_start_time))
                print(f"Audio: {audio_duration:.1f}s, Interval: {timestamp:.1f}s-{timestamp + (interval_duration or 0):.1f}s, Playing: {adjusted_start_time:.1f}s-{adjusted_start_time + audio_duration:.1f}s")

    def _generate_audio_file(self, text: str, timestamp: float):
        """Generate audio file for video overlay"""
        try:
            if self.provider_name == "gemini":
                from google import genai
                from google.genai import types
                api_key = os.getenv("GEMINI_API_KEY")
                client = genai.Client(api_key=api_key)

                response = client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=text,
                    config=types.GenerateContentConfig(
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name='Kore',
                                )
                            )
                        ),
                    )
                )

                audio_data = response.candidates[0].content.parts[0].inline_data.data

            elif self.provider_name == "chatgpt":
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                client = OpenAI(api_key=api_key)

                response = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="coral",
                    input=text,
                    instructions="Speak in a cheerful and positive tone.",
                )
                audio_data = response.content

            # Save audio file with timestamp
            os.makedirs("data", exist_ok=True)
            audio_filename = f"data/feedback_{timestamp:.1f}s.wav"
            with open(audio_filename, "wb") as f:
                f.write(audio_data)

            return audio_filename

        except Exception as e:
            print(f"Error generating audio: {e}")
            return None

    def get_audio_duration(self, audio_file: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json", 
                "-show_format", audio_file
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                import json
                audio_info = json.loads(result.stdout)
                return float(audio_info['format']['duration'])
        except Exception as e:
            print(f"Error getting audio duration: {e}")
        return 0.0

    def create_video_with_audio_overlay(self, input_video_path: str, output_path: str):
        """Create final video with audio overlay using FFmpeg directly"""
        try:
            if not self.audio_files_with_timestamps:
                # No audio to overlay, just copy the original
                shutil.copy2(input_video_path, output_path)
                print("No audio feedback to overlay, copied original video")
                return True
            
            # Check if ffmpeg is available
            try:
                subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Error: FFmpeg not found. Please install FFmpeg.")
                return False
            
            # Build FFmpeg command for mixing audio
            cmd = ["ffmpeg", "-y", "-i", input_video_path]
            
            # Add all feedback audio files as inputs
            audio_delays = []
            valid_audio_count = 0
            
            for audio_file, timestamp in self.audio_files_with_timestamps:
                if audio_file and os.path.exists(audio_file):
                    cmd.extend(["-i", audio_file])
                    # Convert timestamp to milliseconds and create delay filter
                    delay_ms = int(timestamp * 1000)
                    audio_delays.append(f"[{valid_audio_count + 1}:a]adelay={delay_ms}|{delay_ms}[a{valid_audio_count}]")
                    valid_audio_count += 1
            
            if valid_audio_count == 0:
                shutil.copy2(input_video_path, output_path)
                print("No valid audio files found, copied original video")
                return True
            
            # Build filter complex to mix all audio
            filter_parts = audio_delays.copy()
            
            # Create the mixing command
            mix_inputs = "[0:a]" + "".join([f"[a{i}]" for i in range(valid_audio_count)])
            filter_parts.append(f"{mix_inputs}amix=inputs={valid_audio_count + 1}:duration=longest[out]")
            
            filter_complex = ";".join(filter_parts)
            
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "0:v",  # Copy video from input
                "-map", "[out]",  # Use mixed audio output
                "-c:v", "copy",  # Copy video without re-encoding
                "-c:a", "aac",   # Encode audio as AAC
                "-b:a", "128k",  # Audio bitrate
                output_path
            ])
            
            print(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return False
            
            print(f"Successfully created video with audio overlay: {output_path}")
            
            # Clean up temp audio files
            for audio_file, _ in self.audio_files_with_timestamps:
                if audio_file and os.path.exists(audio_file):
                    try:
                        os.remove(audio_file)
                    except OSError:
                        pass  # Ignore cleanup errors
            
            return True
            
        except Exception as e:
            print(f"Error creating video with audio overlay: {e}")
            return False

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
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join(timeout=1.0)