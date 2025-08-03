import cv2
import time
from google import genai
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

def create_system_prompt(config):
    """Create system prompt from config (under 200 words)"""
    activity = config["activity"]
    goal = config["goal"]
    focus_on = config["focus_on"]
    skill_level = config["skill_level"]
    custom_prompt = config["custom_prompt"]
    
    base_prompt = f"""You are a real-time {activity} coach. Analyze this video frame.

VALIDATION:
- If wrong activity detected: "Wrong activity"
- If no movement: "I don't see any movement" 
- If poor lighting/camera: "I can't see you clearly"

ANALYSIS:
- Goal: {goal}
- Focus on: {focus_on}
- Skill level: {skill_level}
{f"- Custom focus: {custom_prompt}" if custom_prompt else ""}

FEEDBACK:
- Provide specific form feedback
- Keep under {config['max_response_length']} words
- Be encouraging but direct

Respond immediately with validation or coaching feedback."""
    
    return base_prompt

def create_video_from_frames(frames, fps=10):
    """Create a temporary video file from frames"""
    if not frames:
        return None
    
    # Create temporary video file
    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_video_path = temp_video.name
    temp_video.close()
    
    # Get frame dimensions
    height, width = frames[0].shape[:2]
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
    
    # Write frames
    for frame in frames:
        out.write(frame)
    
    out.release()
    return temp_video_path

def analyze_video_with_gemini(video_path, prompt_template):
    """Send video to Gemini API for analysis"""
    try:
        # Upload video file using Files API
        video_file = client.files.upload(file=video_path)
        
        # Wait for file to be processed
        while video_file.state.name != "ACTIVE":
            time.sleep(1)
            video_file = client.files.get(name=video_file.name)
        
        # Generate content with video
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                video_file,
                prompt_template
            ]
        )
        
        # Clean up video file
        os.unlink(video_path)
        
        return response.candidates[0].content.parts[0].text if response.candidates else "No feedback available"
    except Exception as e:
        print(f"Error analyzing video with Gemini: {e}")
        # Clean up video file on error
        if os.path.exists(video_path):
            os.unlink(video_path)
        return "Error in analysis"

def main(activity, video_source, tts_provider, config_path):
    """Main function to capture video and provide real-time coaching"""
    # Load configuration
    config = load_config(config_path)
    config["activity"] = activity  # Override with command line argument
    
    # Create system prompt from config
    prompt_template = create_system_prompt(config)
    
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
    
    print(f"AI Coach started for {activity} using {source_name} with {tts_provider} TTS. Press 'q' to quit.")
    print(f"Goal: {config['goal']}")
    print(f"Focus: {config['focus_on']}")
    print(f"Skill level: {config['skill_level']}")
    print(f"Analyzing video every {config['feedback_frequency']} seconds at 10fps...")
    
    frame_count = 0
    last_analysis_time = 0
    frames_buffer = []
    analysis_interval = config['feedback_frequency']  # seconds
    target_fps = 10
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("Error: Could not read frame")
                break
            
            frame_count += 1
            current_time = time.time()
            
            # Add frame to buffer (every 3 frames to get ~10fps from 30fps webcam)
            if frame_count % 3 == 0:
                frames_buffer.append(frame.copy())
            
            # Analyze every 15 seconds
            if current_time - last_analysis_time >= analysis_interval and frames_buffer:
                print(f"Analyzing {len(frames_buffer)} frames at {target_fps}fps...")
                
                # Create video from frames
                video_path = create_video_from_frames(frames_buffer, target_fps)
                if video_path:
                    # Analyze video with Gemini
                    feedback = analyze_video_with_gemini(video_path, prompt_template)
                    print(f"Analysis result: {feedback}")
                    
                    # Add feedback to audio queue
                    tts_manager.add_to_queue(feedback)
                    
                    # Clear buffer
                    frames_buffer = []
                    last_analysis_time = current_time
            
            # Display frame (optional, for debugging)
            cv2.imshow(f'AI Coach - {activity}', frame)
            
            # Check for quit key
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
