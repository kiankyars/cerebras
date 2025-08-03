import argparse
import json
import os
import tempfile
from pathlib import Path

import cv2
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

# Initialize the new genai client
client = genai.Client(api_key=api_key)

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

    base_prompt = f"""You are a real-time {activity} coach. Help me like you're Michael Jordan. The video is {fps}fps.

Notify me if wrong activity, no movement, or poor lighting detected.

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

        # Create video metadata - always include FPS
        video_metadata = types.VideoMetadata(fps=fps)

        # Add time offsets for upload videos
        if start_offset is not None and end_offset is not None:
            video_metadata.start_offset = f"{start_offset}s"
            video_metadata.end_offset = f"{end_offset}s"

        # Create base parts with video metadata
        parts = [
            types.Part(
                inline_data=types.Blob(
                    data=video_bytes,
                    mime_type='video/mp4'
                ),
                video_metadata=video_metadata
            ),
            types.Part(text=prompt_template)
        ]

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
            return None

        return temp_path

    except Exception as e:
        print(f"Error capturing live segment: {e}")
        return None

def main(activity, video_source, tts_provider, config_path):
    """Main function to capture video and provide real-time coaching"""
    # Load configuration
    config = load_config(config_path)
    config["activity"] = activity

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

    print(f"AI Coach started for {activity} using {source_name} with {tts_provider} TTS.")

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
                    feedback = analyze_video_with_gemini(temp_video_path, prompt_template, fps)
                    print(f"Analysis result: {feedback}")

                    # Real-time audio feedback
                    tts_manager.add_to_queue(feedback)

                    # Clean up temp file
                    os.unlink(temp_video_path)
                else:
                    print("Failed to capture live segment")

        else:
            # UPLOAD VIDEO WORKFLOW - Audio overlay into final video
            print("Starting upload video analysis...")

            # Initialize TTS manager for video overlay
            tts_manager = TTSManager(provider=tts_provider, mode="video")

            # Get video properties for proper duration handling
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            video_duration = total_frames / video_fps

            print(f"Video: {video_duration:.1f}s duration, {total_frames} frames at {video_fps}fps")

            # Calculate segments based on video duration
            num_complete_segments = int(video_duration // analysis_interval)
            remaining_time = video_duration % analysis_interval

            # Process complete segments
            for segment_num in range(1, num_complete_segments + 1):
                start_time = (segment_num - 1) * analysis_interval
                end_time = segment_num * analysis_interval

                print(f"Analyzing segment {segment_num}: {start_time}s to {end_time}s")

                feedback = analyze_video_with_gemini(video_source, prompt_template, fps, start_time, end_time)
                print(f"Analysis result: {feedback}")

                # Add feedback to TTS manager with timestamp
                tts_manager.add_to_queue(feedback, start_time)

            # Process remaining partial segment if exists
            if remaining_time > 5:  # Only if significant remaining time
                start_time = num_complete_segments * analysis_interval
                end_time = video_duration

                print(f"Analyzing final segment: {start_time}s to {end_time:.1f}s")

                feedback = analyze_video_with_gemini(video_source, prompt_template, fps, start_time, end_time)
                print(f"Analysis result: {feedback}")

                tts_manager.add_to_queue(feedback, start_time)

            # Create output video with audio overlay
            output_path = f"data/coached_{activity}_{Path(video_source).stem}.mp4"
            print(f"Creating final video with audio overlay: {output_path}")

            success = tts_manager.create_video_with_audio_overlay(video_source, output_path)
            if success:
                print(f"Final video saved: {output_path}")
            else:
                print("Failed to create final video")

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
        default="chatgpt",
    )

    parser.add_argument(
        "--config",
        help="Path to coaching configuration file"
    )

    args = parser.parse_args()
    main(args.activity, args.video_source, args.tts_provider, args.config)
