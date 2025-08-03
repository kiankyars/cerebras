#!/usr/bin/env python3
"""
Direct Web Interface for NED Backend
Bypasses FastAPI to use the backend directly with a simple web interface
"""

import asyncio
import base64
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

import cv2
from aiohttp import web, WSMsgType
from aiohttp.web import WebSocketResponse

# Import backend functions
from ai_coach import analyze_video_with_gemini, create_system_prompt
from tts_manager import TTSManager
from utils.config_manager import ConfigManager

# Global storage
active_sessions: Dict[str, Dict] = {}
config_manager = ConfigManager("configs")

class DirectWebManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocketResponse] = {}
        self.last_api_call: Dict[str, float] = {}
        self.min_call_interval = 10  # Minimum seconds between API calls

    def connect(self, websocket: WebSocketResponse, session_id: str):
        self.active_connections[session_id] = websocket
        self.last_api_call[session_id] = 0

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.last_api_call:
            del self.last_api_call[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to {session_id}: {e}")

    def can_make_api_call(self, session_id: str) -> bool:
        """Check if enough time has passed since last API call"""
        if session_id not in self.last_api_call:
            return True
        
        time_since_last = time.time() - self.last_api_call[session_id]
        return time_since_last >= self.min_call_interval

    def update_api_call_time(self, session_id: str):
        """Update the last API call time for a session"""
        self.last_api_call[session_id] = time.time()

manager = DirectWebManager()

async def websocket_handler(request):
    """Handle WebSocket connections"""
    session_id = request.match_info.get('session_id')
    if not session_id or session_id not in active_sessions:
        return web.Response(text="Session not found", status=404)

    session = active_sessions[session_id]
    ws = WebSocketResponse()
    await ws.prepare(request)
    
    manager.connect(ws, session_id)
    
    try:
        # Send ready message
        await manager.send_message(session_id, {
            "type": "ready",
            "message": "Direct backend session ready"
        })

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await handle_websocket_message(session_id, session, data)
                except json.JSONDecodeError:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Invalid JSON"
                    })
            elif msg.type == WSMsgType.ERROR:
                print(f"WebSocket error: {ws.exception()}")
                break
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(session_id)
    
    return ws

async def handle_websocket_message(session_id: str, session: dict, message: dict):
    """Handle incoming WebSocket messages"""
    msg_type = message.get("type")
    
    if msg_type == "analyze":
        await handle_analyze_request(session_id, session, message)
    elif msg_type == "stop":
        await manager.send_message(session_id, {
            "type": "stopped",
            "message": "Session stopped"
        })

async def handle_analyze_request(session_id: str, session: dict, message: dict):
    """Handle video analysis request"""
    video_data = message.get("videoData")
    if not video_data:
        await manager.send_message(session_id, {
            "type": "error",
            "message": "No video data received"
        })
        return

    # Check rate limiting
    if not manager.can_make_api_call(session_id):
        time_since_last = time.time() - manager.last_api_call[session_id]
        wait_time = manager.min_call_interval - time_since_last
        await manager.send_message(session_id, {
            "type": "rate_limited",
            "message": f"Rate limited. Wait {wait_time:.1f}s",
            "wait_time": wait_time
        })
        return

    try:
        # Save video data
        temp_video_path = f"data/direct_{session_id}_{int(time.time())}.webm"
        os.makedirs("data", exist_ok=True)
        
        with open(temp_video_path, "wb") as f:
            f.write(base64.b64decode(video_data))

        # Analyze video
        config = config_manager.load_config_by_path(session["config_path"])
        fps = config.get('fps', 30)
        prompt_template = create_system_prompt(config, fps)
        
        feedback_json = analyze_video_with_gemini(temp_video_path, prompt_template, fps, config)
        feedback_text = feedback_json.get("feedback", "No feedback available")
        
        # Update API call time
        manager.update_api_call_time(session_id)
        
        # Send feedback
        await manager.send_message(session_id, {
            "type": "feedback",
            "text": feedback_text,
            "timestamp": time.time()
        })
        
        # TTS (if not error)
        if not feedback_text.startswith("Error"):
            tts_manager = TTSManager(provider=session["tts_provider"], mode="live")
            tts_manager.add_to_queue(feedback_text)
        
        # Cleanup
        os.unlink(temp_video_path)
        
    except Exception as e:
        print(f"Error in analysis: {e}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Analysis error: {str(e)}"
        })

async def create_session_handler(request):
    """Create a new session"""
    try:
        data = await request.json()
        config_id = data.get("config_id")
        tts_provider = data.get("tts_provider", "gemini")
        
        # Validate config
        config_path = config_manager.find_config_path(config_id)
        if not config_path:
            return web.json_response({
                "error": "Configuration not found"
            }, status=404)
        
        session_id = str(uuid.uuid4())
        active_sessions[session_id] = {
            "type": "live",
            "config_path": config_path,
            "tts_provider": tts_provider,
            "created_at": time.time()
        }
        
        return web.json_response({
            "session_id": session_id,
            "websocket_url": f"/ws/{session_id}"
        })
        
    except Exception as e:
        return web.json_response({
            "error": str(e)
        }, status=500)

async def list_configs_handler(request):
    """List available configurations"""
    configs = config_manager.list_all_configs()
    return web.json_response({"configs": configs})

async def index_handler(request):
    """Serve the main HTML page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>NED Direct Backend</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        .info { background-color: #d1ecf1; color: #0c5460; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        #video { width: 100%; max-width: 640px; }
        #feedback { margin-top: 20px; padding: 10px; border: 1px solid #ccc; min-height: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>NED Direct Backend</h1>
        
        <div id="setup">
            <h2>Setup</h2>
            <select id="configSelect">
                <option value="">Select configuration...</option>
            </select>
            <select id="ttsSelect">
                <option value="chatgpt">ChatGPT TTS</option>
                <option value="gemini">Gemini TTS</option>
            </select>
            <button onclick="createSession()">Start Session</button>
        </div>
        
        <div id="session" style="display: none;">
            <h2>Live Session</h2>
            <div id="status" class="status info">Connecting...</div>
            <video id="video" autoplay muted></video>
            <br>
            <button onclick="startVideo()">Start Video</button>
            <button onclick="stopVideo()">Stop Video</button>
            <button onclick="endSession()">End Session</button>
            <div id="feedback"></div>
        </div>
    </div>

    <script>
        let ws = null;
        let sessionId = null;
        let stream = null;
        let mediaRecorder = null;
        let isRecording = false;

        // Load configurations
        async function loadConfigs() {
            try {
                const response = await fetch('/configs');
                const data = await response.json();
                const select = document.getElementById('configSelect');
                
                data.configs.forEach(config => {
                    const option = document.createElement('option');
                    option.value = config.id;
                    option.textContent = config.name;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading configs:', error);
            }
        }

        async function createSession() {
            const configId = document.getElementById('configSelect').value;
            const ttsProvider = document.getElementById('ttsSelect').value;
            
            if (!configId) {
                alert('Please select a configuration');
                return;
            }

            try {
                const response = await fetch('/sessions', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config_id: configId, tts_provider: ttsProvider})
                });
                
                const data = await response.json();
                if (data.session_id) {
                    sessionId = data.session_id;
                    connectWebSocket();
                    document.getElementById('setup').style.display = 'none';
                    document.getElementById('session').style.display = 'block';
                } else {
                    alert('Error creating session: ' + data.error);
                }
            } catch (error) {
                alert('Error creating session: ' + error);
            }
        }

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws/${sessionId}`);
            
            ws.onopen = () => {
                updateStatus('Connected', 'success');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = () => {
                updateStatus('Disconnected', 'error');
            };
            
            ws.onerror = (error) => {
                updateStatus('WebSocket error: ' + error, 'error');
            };
        }

        function handleWebSocketMessage(data) {
            switch (data.type) {
                case 'ready':
                    updateStatus('Ready for analysis', 'success');
                    break;
                case 'feedback':
                    document.getElementById('feedback').innerHTML += 
                        `<div><strong>${new Date().toLocaleTimeString()}:</strong> ${data.text}</div>`;
                    break;
                case 'error':
                    updateStatus('Error: ' + data.message, 'error');
                    break;
                case 'rate_limited':
                    updateStatus('Rate limited: ' + data.message, 'info');
                    break;
            }
        }

        function updateStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
        }

        async function startVideo() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({video: true, audio: true});
                document.getElementById('video').srcObject = stream;
                
                // Start recording
                mediaRecorder = new MediaRecorder(stream, {mimeType: 'video/webm'});
                isRecording = true;
                
                mediaRecorder.ondataavailable = async (event) => {
                    if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                        const reader = new FileReader();
                        reader.onload = () => {
                            const base64 = reader.result.split(',')[1];
                            ws.send(JSON.stringify({
                                type: 'analyze',
                                videoData: base64
                            }));
                        };
                        reader.readAsDataURL(event.data);
                    }
                };
                
                mediaRecorder.start(3000); // Send every 3 seconds
                updateStatus('Recording started', 'success');
            } catch (error) {
                updateStatus('Error starting video: ' + error, 'error');
            }
        }

        function stopVideo() {
            if (mediaRecorder) {
                mediaRecorder.stop();
                isRecording = false;
            }
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            updateStatus('Video stopped', 'info');
        }

        function endSession() {
            if (ws) {
                ws.close();
            }
            stopVideo();
            sessionId = null;
            document.getElementById('setup').style.display = 'block';
            document.getElementById('session').style.display = 'none';
            document.getElementById('feedback').innerHTML = '';
        }

        // Load configs on page load
        loadConfigs();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type='text/html')

def create_app():
    """Create the web application"""
    app = web.Application()
    
    # Routes
    app.router.add_get('/', index_handler)
    app.router.add_get('/configs', list_configs_handler)
    app.router.add_post('/sessions', create_session_handler)
    app.router.add_get('/ws/{session_id}', websocket_handler)
    
    return app

if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080) 