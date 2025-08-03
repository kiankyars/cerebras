import cv2
import time
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import argparse
from tts_manager import TTSManager
import tempfile
import json

# Load environment variables
load_dotenv()

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

# Initialize the new genai client
client = genai.Client(api_key=api_key)

def load_config(config_path):
    """Load coaching configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)

def create_system_prompt(config, fps):
    activity = config["activity"]
    
    # Build analysis section dynamically based on available keys
    analysis_parts = []
    
    if "goal" in config:
        analysis_parts.append(f"- My goal: {config['goal']}")
    
    if "focus_on" in config:
        analysis_parts.append(f"- Focus on: {config['focus_on']}")
    
    if "skill_level" in config: 
        analysis_parts.append(f"- My level: {config['skill_level']}")
    
    analysis_section = "\n".join(analysis_parts) if analysis_parts else "- Focus on my basic form"
    
    base_prompt = f"""You are a real-time {activity} coach. Help me like you're Michael Jordan. The video is {fps}fps.

VALIDATION: Notify me if wrong activity, no movement, or poor lighting detected.

FEEDBACK:
{analysis_section}
- Keep under {config.get('max_response_length', 20)} words
- ALWAYS Be direct"""
    print(base_prompt)
    # quit()
    return base_prompt

def analyze_video_with_gemini(video_file_path, prompt_template, fps, start_offset=None, end_offset=None):
    """Send video file to Gemini API for analysis with optional time offsets"""
    try:
        # Read video file as bytes
        with open(video_file_path, 'rb') as f:
            video_bytes = f.read()
        
        # Create base parts
        parts = [
            types.Part(
                inline_data=types.Blob(
                    data=video_bytes,
                    mime_type='video/mp4'
                )
            ),
            types.Part(text=prompt_template)
        ]
        
        # Add video metadata with time offsets only for upload videos
        if start_offset is not None and end_offset is not None:
            parts[0].video_metadata = types.VideoMetadata(
                fps=fps,
                start_offset=f"{start_offset}s",
                end_offset=f"{end_offset}s"
            )
        
        # Generate content with video and metadata
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=types.Content(parts=parts)
        )
        
        return response.candidates[0].content.parts[0].text if response.candidates else "No feedback available"
    except Exception as e:
        print(f"Analysis error: {e}")
        return "Error in analysis"

def capture_live_segment(cap, duration_seconds):
    """Capture live video segment to temporary file and return path with FPS"""
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
            return None, actual_fps
            
        return temp_path, actual_fps
        
    except Exception as e:
        print(f"Error capturing live segment: {e}")
        return None, 30

def main(activity, video_source, tts_provider, config_path):
    """Main function to capture video and provide real-time coaching"""
    # Load configuration
    config = load_config(config_path)
    config["activity"] = activity  # Override with command line argument
    
    # Initialize TTS manager
    tts_manager = TTSManager(provider=tts_provider)
    
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
    
    # Get actual FPS from video source
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if source_fps <= 0:
        source_fps = 30  # Fallback for webcams that don't report FPS
    
    print(f"AI Coach started for {activity} using {source_name} with {tts_provider} TTS.")
    print(f"Video FPS: {source_fps}")
    
    # Display config info (only if keys exist)
    if "goal" in config:
        print(f"Goal: {config['goal']}")
    if "focus_on" in config:
        print(f"Focus: {config['focus_on']}")
    if "skill_level" in config:
        print(f"Skill level: {config['skill_level']}")
    
    analysis_interval = config.get('feedback_frequency')  # seconds
    print(f"Analyzing video every {analysis_interval} seconds...")
    
    # Create system prompt from config with actual fps
    prompt_template = create_system_prompt(config, source_fps)
    
    try:
        if is_live_stream:
            # LIVE STREAMING WORKFLOW
            print("Starting live streaming analysis...")
            
            while True:
                # Display live feed
                ret, frame = cap.read()
                if not ret:
                    print("Error: Could not read frame")
                    break
                
                cv2.imshow(f'AI Coach - {activity}', frame)
                
                # Capture and analyze segment
                print("Capturing live segment...")
                temp_video_path, actual_fps = capture_live_segment(cap, analysis_interval)
                
                if temp_video_path:
                    print("Analyzing live segment...")
                    feedback = analyze_video_with_gemini(temp_video_path, prompt_template, actual_fps)
                    print(f"Analysis result: {feedback}")
                    
                    # Real-time audio feedback
                    tts_manager.add_to_queue(feedback)
                    
                    # Clean up temp file
                    os.unlink(temp_video_path)
                else:
                    print("Failed to capture live segment")
                
                # Check for exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        else:
            # UPLOAD VIDEO WORKFLOW
            print("Starting upload video analysis...")
            video_start_time = time.time()
            last_analysis_time = -analysis_interval
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("End of video reached")
                    break
                
                current_time = time.time()
                current_video_time = current_time - video_start_time
                
                # Analyze using time offsets
                if current_time - last_analysis_time >= analysis_interval:
                    if current_video_time >= analysis_interval:
                        print("Analyzing video segment...")
                        
                        end_offset = int(current_video_time)
                        start_offset = end_offset - analysis_interval
                        
                        print(f"DEBUG: Video time: {current_video_time:.1f}s, Analyzing {start_offset}s to {end_offset}s")
                        
                        feedback = analyze_video_with_gemini(video_source, prompt_template, source_fps, start_offset, end_offset)
                        print(f"Analysis result: {feedback}")
                        
                        tts_manager.add_to_queue(feedback)
                        last_analysis_time = current_time
                    else:
                        print(f"DEBUG: Waiting for more video time. Current: {current_video_time:.1f}s, Need: {analysis_interval}s")
                
                # Display frame
                cv2.imshow(f'AI Coach - {activity}', frame)
                
                # Check for exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
    except KeyboardInterrupt:
        print("Interrupted by user")
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    tts_manager.stop()
    
    print("AI Coach stopped.")


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Real-time AI Coach")
    parser.add_argument(
        "--activity", 
        choices=["basketball", "yoga", "guitar"], 
        help="Activity to coach"
    )
    parser.add_argument(
        "--video-source",
        help="Video source: 'webcam' for camera input, or path to video file"
    )
    parser.add_argument(
        "--tts-provider",
        choices=["gemini", "chatgpt"],
        default="gemini",
        help="TTS provider to use (default: gemini)"
    )
    
    parser.add_argument(
        "--config",
        help="Path to coaching configuration file"
    )
    
    args = parser.parse_args()
    main(args.activity, args.video_source, args.tts_provider, args.config)
