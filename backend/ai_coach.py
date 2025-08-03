import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

from tts_manager import TTSManager

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Note: Client is now created fresh for each request to avoid connection issues

def load_config(config_path):
    """Load coaching configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)

def create_system_prompt(config, fps):
    activity = config["activity"]

    analysis_parts = []

    if "goal" in config:
        analysis_parts.append(f"- My goal: {config['goal']}")

    if "focus_on" in config:
        analysis_parts.append(f"- Focus on: {config['focus_on']}")

    if "skill_level" in config:
        analysis_parts.append(f"- My level: {config['skill_level']}")

    analysis_section = "\n".join(analysis_parts) if analysis_parts else "- Focus on my basic form"

    coach = config.get('coach', 'an expert coach')
    base_prompt = f"""You are a real-time {activity} coach. Help me like you're {coach}. FPS is {fps}.
FEEDBACK:
{analysis_section}
- ALWAYS be direct
- NO timestamps
- OUTPUT RESPONSE IS AT MOST {config["max_response_length"]} WORDS
- NEVER LEAVE FORMATTING
"""
    print(base_prompt)
    # quit()
    return base_prompt

def analyze_video_with_gemini(video_file_path, prompt_template, fps, config):
    """Analyze video using direct Gemini API"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"🚀 Using Direct Gemini API for analysis... (attempt {attempt + 1}/{max_retries})")
            
            # Create fresh client for each request to avoid connection issues
            fresh_client = genai.Client(api_key=api_key)
            
            # Read video file as bytes
            with open(video_file_path, 'rb') as f:
                video_bytes = f.read()
            
            # Check video file size - if too large, this might cause issues
            video_size_mb = len(video_bytes) / (1024 * 1024)
            print(f"📹 Video size: {video_size_mb:.2f} MB")
            
            if video_size_mb > 10:  # If video is larger than 10MB, it might cause issues
                print(f"⚠️ Video is large ({video_size_mb:.2f} MB), this might cause API issues")
            
            # Simplified request without JSON schema - more reliable
            parts = [
                types.Part(
                    inline_data=types.Blob(
                        data=video_bytes,
                        mime_type='video/webm'
                    )
                ),
                types.Part(text=prompt_template + "\n\nRespond with ONLY a JSON object containing a 'feedback' field.")
            ]
            
            # Generate content with simplified config
            response = fresh_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=types.Content(parts=parts),
                config=types.GenerateContentConfig(
                    media_resolution='MEDIA_RESOLUTION_LOW'
                )
            )

            print(f"📦 Raw Gemini response type: {type(response)}")
            if hasattr(response, 'candidates'):
                print(f"📄 Response has {len(response.candidates) if response.candidates else 0} candidates")
            
            if response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    content = candidate.content
                    print(f"📎 Content: {content}")
                    
                    # Try to extract text from content
                    if hasattr(content, 'parts') and len(content.parts) > 0:
                        part = content.parts[0]
                        if hasattr(part, 'text') and part.text:
                            text = part.text.strip()
                            print(f"📝 Extracted text: '{text}'")
                            
                            # Try to parse as JSON
                            try:
                                result = json.loads(text)
                                print(f"✅ Successfully parsed JSON: {result}")
                                return result
                            except json.JSONDecodeError:
                                # If not JSON, return as plain feedback
                                return {"feedback": text}
                        else:
                            return {"feedback": "No feedback available"}
                    else:
                        return {"feedback": "No feedback available"}
                return {"feedback": "No feedback available"}
            else:
                return {"feedback": "No feedback available"}
                
        except Exception as e:
            print(f"Error in analysis (attempt {attempt + 1}): {e}")
            import traceback
            print(f"Full error traceback: {traceback.format_exc()}")
            
            # If this is the last attempt, try fallback text-only approach
            if attempt == max_retries - 1:
                print(f"🔄 Trying fallback text-only approach...")
                try:
                    # Fallback: text-only request
                    fallback_prompt = f"{prompt_template}\n\nSince video analysis failed, provide general coaching feedback for {config.get('activity', 'this activity')}."
                    
                    fallback_response = fresh_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=types.Content(parts=[types.Part(text=fallback_prompt)]),
                        config=types.GenerateContentConfig()
                    )
                    
                    if fallback_response.candidates:
                        candidate = fallback_response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            text = candidate.content.parts[0].text.strip()
                            return {"feedback": text}
                    
                    return {"feedback": f"Error in analysis: {str(e)}"}
                except Exception as fallback_e:
                    print(f"Fallback also failed: {fallback_e}")
                    return {"feedback": f"Error in analysis: {str(e)}"}
            
            # Otherwise, wait and retry
            print(f"Retrying in {retry_delay} seconds...")
            import time
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

def capture_live_segment(cap, duration_seconds):
    """Capture live video segment to temporary file and return path"""
    try:
        # Get actual FPS from video capture
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        if actual_fps <= 0:
            actual_fps = 30  # Fallback for webcams that don't report FPS

        # Create temporary MP4 file
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_path = temp_file.name
        temp_file.close()

        # Set up video writer
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, actual_fps, (frame_width, frame_height))

        # Capture frames for specified duration
        frames_to_capture = int(duration_seconds * actual_fps)
        frames_captured = 0

        for _ in range(frames_to_capture):
            ret, frame = cap.read()
            if ret:
                out.write(frame)
                frames_captured += 1
            else:
                break

        out.release()

        if frames_captured == 0:
            os.unlink(temp_path)
            return None

        return temp_path

    except Exception as e:
        print(f"Error capturing live segment: {e}")
        return None

def split_video_into_segments(input_video_path, segment_duration, output_dir="data"):
    """Split video into segments using FFmpeg - ONLY complete segments"""
    try:
        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: FFmpeg not found. Please install FFmpeg.")
            return []

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get video duration first
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json", 
            "-show_format", input_video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error probing video: {result.stderr}")
            return []
        
        import json
        video_info = json.loads(result.stdout)
        total_duration = float(video_info['format']['duration'])
        
        # Calculate segments, combining last segment with any remaining time
        remaining_time = total_duration % segment_duration
        num_segments = int(total_duration // segment_duration)
        
        print(f"Video duration: {total_duration:.1f}s")
        print(f"Processing {num_segments} segments")
        
        segment_files = []
        
        # Split into segments, extending last one to include remaining time
        for i in range(num_segments):
            start_time = i * segment_duration
            output_file = f"{output_dir}/segment_{i:03d}.mp4"
            
            # For the last segment, include any remaining time
            if i == num_segments - 1 and remaining_time > 0:
                duration = segment_duration + remaining_time
            else:
                duration = segment_duration
            
            cmd = [
                "ffmpeg", "-y", "-i", input_video_path,
                "-ss", str(start_time),
                "-t", str(duration),
                "-c", "copy",  # Copy without re-encoding for speed
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                segment_files.append((output_file, start_time, duration))
                print(f"Created segment {i+1}: {start_time}s-{start_time + duration}s")
            else:
                print(f"Error creating segment {i}: {result.stderr}")
        
        return segment_files
        
    except Exception as e:
        print(f"Error splitting video: {e}")
        return []

def main(video_source, tts_provider, config_path):
    """Main function to capture video and provide real-time coaching"""
    # Load configuration
    config = load_config(config_path)

    # Initialize video capture
    is_live_stream = video_source == "webcam"

    if is_live_stream:
        cap = cv2.VideoCapture(0)  # 0 for default webcam
        source_name = "webcam"
    else:
        cap = cv2.VideoCapture(video_source)
        source_name = video_source

    if not cap.isOpened():
        print(f"Error: Could not open video source: {source_name}")
        return

    print(f"NED started for {config["activity"]} using {source_name} with {tts_provider} TTS.")

    analysis_interval = config.get('feedback_frequency')
    fps = config.get('fps')

    # Create system prompt from config with actual fps
    prompt_template = create_system_prompt(config, fps)

    try:
        if is_live_stream:
            # LIVE STREAMING WORKFLOW - Instant audio feedback
            print("Starting live streaming analysis...")

            # Initialize TTS manager for real-time audio
            tts_manager = TTSManager(provider=tts_provider, mode="live")

            while True:
                # Capture and analyze segment
                print("Capturing live segment...")
                temp_video_path = capture_live_segment(cap, analysis_interval)

                if temp_video_path:
                    print("Analyzing live segment...")
                    feedback_json = analyze_video_with_gemini(temp_video_path, prompt_template, fps, config)
                    feedback_text = feedback_json.get("feedback", "No feedback available")
                    print(f"Analysis result: {feedback_json}")

                    # Real-time audio feedback
                    tts_manager.add_to_queue(feedback_text)

                    # Clean up temp file
                    os.unlink(temp_video_path)
                else:
                    print("Failed to capture live segment")

        else:
            # UPLOAD VIDEO WORKFLOW - Split into segments and analyze each
            print("Starting upload video analysis...")

            # Initialize TTS manager for video overlay
            tts_manager = TTSManager(provider=tts_provider, mode="video")

            # Split video into segments using FFmpeg
            print(f"Splitting video into {analysis_interval}s segments...")
            segment_files = split_video_into_segments(video_source, analysis_interval)

            if not segment_files:
                print("Failed to split video into segments")
                return

            # Analyze each segment
            for segment_file, start_time, duration in segment_files:
                print(f"Analyzing segment: {start_time}s-{start_time + duration}s")
                
                feedback_json = analyze_video_with_gemini(segment_file, prompt_template, fps, config)
                feedback_text = feedback_json.get("feedback", "No feedback available")
                print(f"Analysis result: {feedback_json}")

                # Add feedback to TTS manager with proper timing
                tts_manager.add_to_queue(feedback_text, start_time, duration)

            # Clean up segment files
            for segment_file, _, _ in segment_files:
                try:
                    os.unlink(segment_file)
                except OSError:
                    pass

            # Create output video with audio overlay
            output_path = f"data/coached_{config["activity"]}_{Path(video_source).stem}.mp4"
            print(f"Creating final video with audio overlay: {output_path}")

            success = tts_manager.create_video_with_audio_overlay(video_source, output_path)
            if success:
                print(f"Final video saved: {output_path}")
            else:
                print("Failed to create final video")

    except KeyboardInterrupt:
        print("Interrupted by user")

    # Clean up
    if is_live_stream:
        cap.release()
        cv2.destroyAllWindows()

    print("NED stopped.")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Real-time coaching with NED")
    parser.add_argument(
        "--video-source",
        help="Video source: 'webcam' for camera input, or path to video file"
    )
    parser.add_argument(
        "--tts",
        choices=["gemini", "chatgpt"],
        help="TTS provider to use"
    )

    parser.add_argument(
        "--config",
        help="Path to coaching configuration file"
    )

    args = parser.parse_args()
    main(args.video_source, args.tts, args.config)
