import { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import FeedbackOverlay from '../components/FeedbackOverlay';
import LoadingSpinner from '../components/LoadingSpinner';
import { useAudio } from '../hooks/useAudio';
import { useWebSocket } from '../hooks/useWebSocket';
import config from '../lib/config';

export default function Home() {
  // State variables
  const [mode, setMode] = useState<'live' | 'upload'>('live');
  const [isRecording, setIsRecording] = useState(false);
  const [feedback, setFeedback] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [configs, setConfigs] = useState<any[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>('basketball');
  const [timeElapsed, setTimeElapsed] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timeIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Hooks
  const { initializeAudio, playTextToSpeech, stopAudio } = useAudio();
  const { connect, send, disconnect } = useWebSocket();
  
  // Fetch available configs on mount
  useEffect(() => {
    fetchConfigs();
  }, []);
  
  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (timeIntervalRef.current) {
        clearInterval(timeIntervalRef.current);
      }
    };
  }, []);
  
  const fetchConfigs = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${config.apiUrl}/configs`);
      if (!response.ok) {
        throw new Error(`Failed to fetch configs: ${response.statusText}`);
      }
      const data = await response.json();
      setConfigs(data.configs);
      
      // Set default config if available
      if (data.configs.length > 0) {
        setSelectedConfig(data.configs[0].id);
      }
    } catch (error) {
      console.error('Error fetching configs:', error);
      setError('Failed to load coaching configurations. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720 },
        audio: true
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      
      streamRef.current = stream;
    } catch (error) {
      console.error('Error accessing camera:', error);
      setFeedback('Could not access camera. Please check permissions.');
    }
  };
  
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };
  
  const startLiveSession = async () => {
    setIsLoading(true);
    setError('');
    try {
      // Initialize audio first
      await initializeAudio();
      
      const response = await fetch(`${config.apiUrl}/sessions/live`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `config_id=${selectedConfig}&tts_provider=gemini`
      });
      
      if (!response.ok) {
        throw new Error(`Failed to start session: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      // Connect to WebSocket
      connect(data.session_id, (message) => {
        if (message.type === 'feedback' && message.text) {
          setFeedback(message.text);
          // Play audio feedback
          playTextToSpeech(message.text);
        } else if (message.type === 'error') {
          setError(`Error: ${message.message}`);
        }
      });
      
      setFeedback('Connected to AI coach. Starting analysis...');
      
      // Start camera
      await startCamera();
      
      // Start time tracking
      setTimeElapsed(0);
      if (timeIntervalRef.current) {
        clearInterval(timeIntervalRef.current);
      }
      timeIntervalRef.current = setInterval(() => {
        setTimeElapsed(prev => prev + 1);
      }, 1000);
    } catch (error) {
      console.error('Error starting live session:', error);
      setError('Failed to start live session. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const stopLiveSession = async () => {
    disconnect();
    stopCamera();
    stopAudio();
    
    if (timeIntervalRef.current) {
      clearInterval(timeIntervalRef.current);
      timeIntervalRef.current = null;
    }
    
    setFeedback('');
    setTimeElapsed(0);
    setError('');
  };
  
  const startRecording = () => {
    if (!streamRef.current) return;
    
    const mediaRecorder = new MediaRecorder(streamRef.current);
    mediaRecorderRef.current = mediaRecorder;
    
    mediaRecorder.ondataavailable = async (event) => {
      if (event.data.size > 0 && sessionId) {
        // Send analyze command via WebSocket
        send({ type: 'analyze' });
      }
    };
    
    mediaRecorder.onstop = () => {
      console.log('Recording stopped');
    };
    
    // Start recording with 3-second segments
    mediaRecorder.start(3000);
    setIsRecording(true);
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };
  
  const handleStart = async () => {
    if (mode === 'live') {
      await startLiveSession();
      startRecording();
    }
  };
  
  const handleStop = async () => {
    if (mode === 'live') {
      stopRecording();
      await stopLiveSession();
    }
  };
  
  const handleVideoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setIsLoading(true);
    setError('');
    setProgress(0);
    
    try {
      // Create upload session
      const formData = new FormData();
      formData.append('video', file);
      formData.append('config_id', selectedConfig);
      formData.append('tts_provider', 'gemini');
      
      const response = await fetch(`${config.apiUrl}/sessions/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      // Start the session
      const startResponse = await fetch(`${config.apiUrl}/sessions/${data.session_id}/start`, {
        method: 'POST'
      });
      
      if (!startResponse.ok) {
        throw new Error(`Failed to start analysis: ${startResponse.statusText}`);
      }
      
      // Connect to WebSocket for progress updates
      connect(data.session_id, (message) => {
        if (message.type === 'progress') {
          setProgress((message.segment! / message.total!) * 100);
          setFeedback(message.text || 'Processing...');
        } else if (message.type === 'completed') {
          setProgress(100);
          setVideoUrl(`${config.apiUrl}${message.download_url}`);
          setFeedback('Video analysis complete! Download your coached video below.');
        } else if (message.type === 'error') {
          setError(`Error: ${message.message}`);
        }
      });
      
    } catch (error) {
      console.error('Error uploading video:', error);
      setError('Failed to upload video. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };
  
  return (
    <div className="min-h-screen bg-gray-100">
      <Head>
        <title>FR8 AI Coach</title>
        <meta name="description" content="Real-time AI coaching for sports and more" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-8">FR8 AI Coach</h1>
        
        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-center">
            {error}
          </div>
        )}
        
        {/* Loading Display */}
        {isLoading && (
          <div className="mb-6 text-center">
            <LoadingSpinner text="Loading..." />
          </div>
        )}
        
        {/* Mode Selection */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium rounded-l-lg ${
                mode === 'live' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
              onClick={() => setMode('live')}
            >
              Live Coaching (Premium)
            </button>
            <button
              type="button"
              className={`px-4 py-2 text-sm font-medium rounded-r-lg ${
                mode === 'upload' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
              onClick={() => setMode('upload')}
            >
              Upload Video (Free)
            </button>
          </div>
        </div>
        
        {/* Configuration Selection */}
        <div className="mb-6">
          <label htmlFor="config-select" className="block text-sm font-medium text-gray-700 mb-2">
            Select Activity:
          </label>
          <select
            id="config-select"
            className="block w-full max-w-xs mx-auto rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            value={selectedConfig}
            onChange={(e) => setSelectedConfig(e.target.value)}
          >
            {configs.map((config) => (
              <option key={config.id} value={config.id}>
                {config.name} ({config.category})
              </option>
            ))}
          </select>
        </div>
        
        {/* Live Mode */}
        {mode === 'live' && (
          <div className="text-center">
            <div className="relative inline-block">
              <video
                ref={videoRef}
                autoPlay
                muted
                className="w-full max-w-2xl mx-auto rounded-lg shadow-lg"
                style={{ transform: 'scaleX(-1)' }} // Mirror effect
              />
              
              <FeedbackOverlay feedback={feedback} timeElapsed={timeElapsed} />
            </div>
            
            <div className="mt-6">
              {!isRecording ? (
                <button
                  onClick={handleStart}
                  disabled={isLoading}
                  className="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Starting...' : 'Start Live Coaching'}
                </button>
              ) : (
                <button
                  onClick={handleStop}
                  className="px-6 py-3 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                >
                  Stop Coaching
                </button>
              )}
            </div>
          </div>
        )}
        
        {/* Upload Mode */}
        {mode === 'upload' && (
          <div className="text-center">
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload Video:
              </label>
              <input
                type="file"
                accept="video/*"
                onChange={handleVideoUpload}
                disabled={isLoading}
                className="block w-full max-w-xs mx-auto text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-600 file:text-white
                  hover:file:bg-blue-700
                  disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            
            {progress > 0 && (
              <div className="mb-6">
                <div className="w-full max-w-xs mx-auto bg-gray-200 rounded-full h-2.5">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-sm text-gray-600">{Math.round(progress)}% complete</p>
              </div>
            )}
            
            {videoUrl && (
              <div className="mt-6">
                <a 
                  href={videoUrl} 
                  download
                  className="px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                >
                  Download Coached Video
                </a>
              </div>
            )}
            
            {feedback && (
              <div className="mt-6 p-4 bg-white rounded-lg shadow-md max-w-2xl mx-auto">
                <p>{feedback}</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
