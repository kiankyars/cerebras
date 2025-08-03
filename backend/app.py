import asyncio
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_coach import analyze_video_with_gemini, capture_live_segment, create_system_prompt, split_video_into_segments
from tts_manager import TTSManager
from utils.config_manager import ConfigManager

app = FastAPI(title="NED API", version="0.1.0")

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for active sessions
active_sessions: Dict[str, Dict] = {}

config_manager = ConfigManager("configs")

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_feedback(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "NED API is running"}

@app.get("/configs")
async def list_configs():
    """List available coaching configurations"""
    configs = config_manager.list_all_configs()
    return {"configs": configs}

@app.get("/configs/categories")
async def list_categories():
    """List available configuration categories"""
    categories = config_manager.list_categories()
    return {"categories": categories}

@app.get("/configs/categories/{category}")
async def list_configs_by_category(category: str):
    """List configurations for a specific category"""
    configs = config_manager.list_configs_by_category(category)
    return {"configs": configs}

@app.get("/configs/{config_id}")
async def get_config(config_id: str):
    """Get specific configuration"""
    config = config_manager.load_config_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {"config": config}

@app.post("/sessions/upload")
async def create_upload_session(
    video: UploadFile = File(...),
    config_id: str = Form(...),
    tts_provider: str = Form(default="chatgpt")
):
    """Create a new session for uploaded video analysis"""
    session_id = str(uuid.uuid4())
    
    # Validate config
    config_path = config_manager.find_config_path(config_id)
    if not config_path:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Save uploaded video
    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    content = await video.read()
    temp_video.write(content)
    temp_video.close()
    
    # Store session info
    active_sessions[session_id] = {
        "type": "upload",
        "video_path": temp_video.name,
        "config_path": config_path,
        "tts_provider": tts_provider,
        "status": "created"
    }
    
    return {
        "session_id": session_id,
        "message": "Upload session created successfully",
        "video_duration": None  # Could add duration calculation here
    }

@app.post("/sessions/live")
async def create_live_session(
    config_id: str = Form(...),
    tts_provider: str = Form(default="chatgpt")
):
    """Create a new session for live video analysis"""
    session_id = str(uuid.uuid4())
    
    # Validate config
    config_path = config_manager.find_config_path(config_id)
    if not config_path:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Store session info
    active_sessions[session_id] = {
        "type": "live",
        "config_path": config_path,
        "tts_provider": tts_provider,
        "status": "created"
    }
    
    return {
        "session_id": session_id,
        "message": "Live session created successfully"
    }

@app.post("/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start analysis for a session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    config = config_manager.load_config_by_path(session["config_path"])
    
    try:
        if session["type"] == "upload":
            # Process uploaded video
            session["status"] = "processing"
            await process_upload_video(session_id, session, config)
        else:
            # Start live session
            session["status"] = "live"
            # Live processing happens via WebSocket
        
        return {"message": f"Session {session_id} started successfully"}
    
    except Exception as e:
        session["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Error starting session: {str(e)}")

async def process_upload_video(session_id: str, session: dict, config: dict):
    """Process uploaded video in background"""
    try:
        video_path = session["video_path"]
        tts_provider = session["tts_provider"]
        
        # Initialize TTS manager
        tts_manager = TTSManager(provider=tts_provider, mode="video")
        
        # Create prompt
        fps = config.get('fps')
        prompt_template = create_system_prompt(config, fps)
        
        # Split video into segments
        analysis_interval = config.get('feedback_frequency')
        segment_files = split_video_into_segments(video_path, analysis_interval)
        
        total_segments = len(segment_files)
        
        # Analyze each segment
        for i, (segment_file, start_time, duration) in enumerate(segment_files):
            feedback_json = analyze_video_with_gemini(segment_file, prompt_template, fps, config)
            feedback_text = feedback_json.get("feedback", "No feedback available")
            
            # Send progress via WebSocket
            await manager.send_feedback(session_id, {
                "type": "progress",
                "segment": i + 1,
                "total": total_segments,
                "start_time": start_time,
                "feedback": feedback_text
            })
            
            # Add to TTS queue
            tts_manager.add_to_queue(feedback_text, start_time, duration)
            
            # Clean up segment file
            try:
                os.unlink(segment_file)
            except OSError:
                pass
        
        # Create final video with audio overlay
        activity = config["activity"]
        output_path = f"data/coached_{activity}_{session_id}.mp4"
        success = tts_manager.create_video_with_audio_overlay(video_path, output_path)
        
        if success:
            session["output_path"] = output_path
            session["status"] = "completed"
            await manager.send_feedback(session_id, {
                "type": "completed",
                "download_url": f"/sessions/{session_id}/download"
            })
        else:
            session["status"] = "error"
            await manager.send_feedback(session_id, {
                "type": "error",
                "message": "Failed to create final video"
            })
    
    except Exception as e:
        session["status"] = "error"
        await manager.send_feedback(session_id, {
            "type": "error",
            "message": str(e)
        })

@app.get("/sessions/{session_id}/download")
async def download_result(session_id: str):
    """Download the processed video result"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    if "output_path" not in session:
        raise HTTPException(status_code=404, detail="No output file available")
    
    return FileResponse(
        path=session["output_path"],
        filename=f"coached_video_{session_id}.mp4",
        media_type="video/mp4"
    )

@app.delete("/sessions/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up session resources"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    # Clean up temporary files
    if "video_path" in session:
        try:
            os.unlink(session["video_path"])
        except OSError:
            pass
    
    if "output_path" in session:
        try:
            os.unlink(session["output_path"])
        except OSError:
            pass
    
    # Remove from active sessions
    del active_sessions[session_id]
    
    return {"message": "Session cleaned up successfully"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket, session_id)
    
    try:
        if session_id in active_sessions:
            session = active_sessions[session_id]
            
            if session["type"] == "live":
                # Handle live video analysis
                await handle_live_session(websocket, session_id, session)
            else:
                # For upload sessions, just maintain connection for progress updates
                while True:
                    data = await websocket.receive_text()
                    # Handle any client messages if needed
        else:
            await websocket.send_json({"type": "error", "message": "Session not found"})
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)

async def handle_live_session(websocket: WebSocket, session_id: str, session: dict):
    """Handle live video analysis via WebSocket"""
    config = config_manager.load_config_by_path(session["config_path"])
    tts_provider = session["tts_provider"]
    
    # Initialize TTS manager for live mode
    tts_manager = TTSManager(provider=tts_provider, mode="live")
    
    # Create prompt
    fps = config.get('fps')
    prompt_template = create_system_prompt(config, fps)
    
    try:
        # Send confirmation that session is ready
        await websocket.send_json({
            "type": "ready", 
            "message": "Live session ready for video analysis"
        })
        
        while True:
            # Wait for client to send video data or commands
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                message = json.loads(data)
                print(f"📨 Received WebSocket message: {message.get('type', 'unknown')}")
                
                if message.get("type") == "analyze":
                    print(f"🔍 Received analyze message for session {session_id}")
                    video_data = message.get("videoData")
                    if video_data:
                        print(f"📹 Video data received, size: {len(video_data)} characters")
                        # Save video data to temporary file
                        import base64
                        import time
                        temp_video_path = f"data/live_{session_id}_{int(time.time())}.webm"
                        os.makedirs("data", exist_ok=True)
                        print(f"💾 Saving video to: {temp_video_path}")
                        
                        try:
                            with open(temp_video_path, "wb") as f:
                                f.write(base64.b64decode(video_data))
                            print(f"✅ Video file saved successfully")
                            
                            # Analyze the video segment
                            print(f"🤖 Starting Gemini analysis...")
                            feedback_json = analyze_video_with_gemini(temp_video_path, prompt_template, fps, config)
                            feedback_text = feedback_json.get("feedback", "No feedback available")
                            print(f"💬 Analysis result: {feedback_text}")
                            
                            # Send feedback
                            await websocket.send_json({
                                "type": "feedback",
                                "text": feedback_text,
                                "timestamp": asyncio.get_event_loop().time()
                            })
                            print(f"📤 Feedback sent via WebSocket")
                            
                            # Play audio feedback only if not an error
                            is_error = feedback_text.startswith("Error in") or "error" in feedback_text.lower()
                            if not is_error:
                                tts_manager.add_to_queue(feedback_text)
                                print(f"🔊 Added to TTS queue")
                            else:
                                print(f"⚠️ Skipping TTS for error message")
                            
                            # Clean up
                            os.unlink(temp_video_path)
                            print(f"🗑️ Cleaned up temp file")
                            
                        except Exception as e:
                            print(f"❌ Error processing video: {e}")
                            import traceback
                            print(f"❌ Full error traceback: {traceback.format_exc()}")
                            # Send error to frontend but DON'T add to TTS queue
                            await websocket.send_json({
                                "type": "error", 
                                "message": f"Error processing video: {str(e)}"
                            })
                            # Skip TTS for errors
                    else:
                        print(f"⚠️ No video data in analyze message")
                        await websocket.send_json({
                            "type": "error", 
                            "message": "No video data received"
                        })
                
                elif message.get("type") == "stop":
                    break
            
            except asyncio.TimeoutError:
                # This is normal - just waiting for messages
                continue
            except WebSocketDisconnect:
                break
        
        # Session ended
        print(f"Live session {session_id} ended")
    
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)