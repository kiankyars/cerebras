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

def load_config(config_path="coach_config.json"):
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
    
    base_prompt = f"""You are a real-time {activity} coach. Help me like you're Michael Jordan. This video is {fps}fps.

VALIDATION: Notify me if wrong activity, no movement, or poor lighting detected.

FEEDBACK:
{analysis_section}
- Keep under {config.get('max_response_length', 20)} words
- ALWAYS Be direct"""
    print(base_prompt)
    # quit()
    return base_prompt

def analyze_video_with_gemini(video_source, prompt_template, fps, start_offset, end_offset):
    """Send video to Gemini API for analysis with time offsets"""
    try:
        # Read video file as bytes
        with open(video_source, 'rb') as f:
            video_bytes = f.read()
        
        # Generate content with video and metadata using time offsets
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=types.Content(
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            data=video_bytes,
                            mime_type='video/mp4'
                        ),
                        video_metadata=types.VideoMetadata(
                            fps=fps,
                            start_offset=f"{start_offset}s",
                            end_offset=f"{end_offset}s"
                        )
                    ),
                    types.Part(text=prompt_template)
                ]
            )
        )
        
        return response.candidates[0].content.parts[0].text if response.candidates else "No feedback available"
    except Exception as e:
        print(e)
        return "Error in analysis"

def main(activity, video_source, tts_provider, config_path):
    """Main function to capture video and provide real-time coaching"""
    # Load configuration
    config = load_config(config_path)
    config["activity"] = activity  # Override with command line argument
    
    # Initialize TTS manager
    tts_manager = TTSManager(provider=tts_provider)
    
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
    
    print(f"AI Coach started for {activity} using {source_name} with {tts_provider} TTS.")
    
    # Display config info (only if keys exist)
    if "goal" in config:
        print(f"Goal: {config['goal']}")
    if "focus_on" in config:
        print(f"Focus: {config['focus_on']}")
    if "skill_level" in config:
        print(f"Skill level: {config['skill_level']}")
    
    print(f"Analyzing video every {config.get('feedback_frequency')} seconds...")
    
    frame_count = 0
    analysis_interval = config.get('feedback_frequency')  # seconds
    last_analysis_time = -analysis_interval
    target_fps = 10
    video_start_time = time.time()  # Track when video started
    
    # Create system prompt from config with fps
    prompt_template = create_system_prompt(config, target_fps)
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("Error: Could not read frame")
                break
            
            frame_count += 1
            current_time = time.time()
            
            # Analyze every interval
            if current_time - last_analysis_time >= analysis_interval:
                # Calculate video time offsets (not Unix timestamps!)
                current_video_time = current_time - video_start_time  # Elapsed video time
                
                # Only analyze if we have enough video time accumulated
                if current_video_time >= analysis_interval:
                    print(f"Analyzing video segment...")
                    
                    end_offset = int(current_video_time)
                    start_offset = end_offset - analysis_interval  # Now guaranteed to be >= 0
                    
                    print(f"DEBUG: Video time: {current_video_time:.1f}s, Analyzing {start_offset}s to {end_offset}s")
                    
                    # Analyze video with Gemini using time offsets
                    feedback = analyze_video_with_gemini(video_source, prompt_template, target_fps, start_offset, end_offset)
                    print(f"Analysis result: {feedback}")
                    
                    # Add feedback to audio queue
                    tts_manager.add_to_queue(feedback)
                    
                    last_analysis_time = current_time
                else:
                    print(f"DEBUG: Waiting for more video time. Current: {current_video_time:.1f}s, Need: {analysis_interval}s")
            
            # Display frame (optional, for debugging)
            cv2.imshow(f'AI Coach - {activity}', frame)
                
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
        default="basketball",
        help="Activity to coach (default: basketball)"
    )
    parser.add_argument(
        "--video-source", 
        default="webcam",
        help="Video source: 'webcam' for camera input, or path to video file (default: webcam)"
    )
    parser.add_argument(
        "--tts-provider",
        choices=["gemini", "chatgpt"],
        default="gemini",
        help="TTS provider to use (default: gemini)"
    )
    
    parser.add_argument(
        "--config",
        default="coach_config.json",
        help="Path to coaching configuration file (default: coach_config.json)"
    )
    
    args = parser.parse_args()
    main(args.activity, args.video_source, args.tts_provider, args.config)
