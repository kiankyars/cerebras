import { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import FeedbackOverlay from '../components/FeedbackOverlay';
import LoadingSpinner from '../components/LoadingSpinner';
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
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedConfig, setSelectedConfig] = useState<string>('');
  const [selectedTTSProvider, setSelectedTTSProvider] = useState<string>('chatgpt');
  const [selectedVoiceStyle, setSelectedVoiceStyle] = useState<string>('cheerful');
  const [timeElapsed, setTimeElapsed] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showActivityModal, setShowActivityModal] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timeIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Hooks
  const { connect, send, disconnect } = useWebSocket();
  
  // Voice style options
  const voiceStyles = [
    { id: 'cheerful', name: 'Cheerful & Positive', icon: '😊', instruction: 'Speak in a cheerful and positive tone.' },
    { id: 'motivational', name: 'Motivational & Energetic', icon: '💪', instruction: 'Speak with high energy and motivation.' },
    { id: 'calm', name: 'Calm & Relaxed', icon: '🧘‍♀️', instruction: 'Speak in a calm and soothing tone.' },
    { id: 'professional', name: 'Professional & Clear', icon: '👔', instruction: 'Speak in a professional and authoritative tone.' },
    { id: 'friendly', name: 'Friendly & Casual', icon: '🤝', instruction: 'Speak in a friendly and conversational tone.' }
  ];
  
  // Fetch available configs and categories on mount
  useEffect(() => {
    fetchConfigs();
    fetchCategories();
  }, []);
  
  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      disconnect();
      if (timeIntervalRef.current) {
        clearInterval(timeIntervalRef.current);
      }
    };
  }, [disconnect]);
  
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
        setSelectedCategory(data.configs[0].category);
      }
      
    } catch (error) {
      console.error('Error fetching configs:', error);
      setError('Failed to load coaching configurations. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${config.apiUrl}/configs/categories`);
      if (!response.ok) {
        throw new Error(`Failed to fetch categories: ${response.statusText}`);
      }
      const data = await response.json();
      setCategories(data.categories);
    } catch (error) {
      console.error('Error fetching categories:', error);
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
      console.log('Sending config_id:', selectedConfig);
      const response = await fetch(`${config.apiUrl}/sessions/live`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `config_id=${selectedConfig}&tts_provider=${selectedTTSProvider}&voice_style=${selectedVoiceStyle}`
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error(`Failed to start session: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      // Connect to WebSocket
      connect(data.session_id, (message) => {
        if (message.type === 'feedback' && message.text) {
          setFeedback(message.text);
        } else if (message.type === 'error') {
          setError(`Error: ${message.message}`);
        }
      });
      
      setFeedback('Connected to NED. Starting analysis...');
      
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
      
      return data;
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
    
    if (timeIntervalRef.current) {
      clearInterval(timeIntervalRef.current);
      timeIntervalRef.current = null;
    }
    
    setFeedback('');
    setTimeElapsed(0);
    setError('');
  };
  
  const startRecording = (currentSessionId?: string) => {
    if (!streamRef.current) {
      console.error('No stream available for recording');
      return;
    }
    
    let mediaRecorder;
    try {
      if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
        mediaRecorder = new MediaRecorder(streamRef.current, {
          mimeType: 'video/webm;codecs=vp8',
          videoBitsPerSecond: 250000
        });
      } else {
        mediaRecorder = new MediaRecorder(streamRef.current);
      }
    } catch (error) {
      console.error('Failed to create MediaRecorder with options, trying default:', error);
      mediaRecorder = new MediaRecorder(streamRef.current);
    }
    
    mediaRecorderRef.current = mediaRecorder;
    
    mediaRecorder.ondataavailable = async (event) => {
      const activeSessionId = currentSessionId || sessionId;
      if (event.data.size > 0 && activeSessionId) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          const base64Index = base64.indexOf('base64,');
          const videoData = base64Index !== -1 ? base64.substring(base64Index + 7) : null;
          
          if (videoData && videoData.length >= 1000) {
            send({ 
              type: 'analyze', 
              videoData: videoData
            });
          }
        };
        reader.readAsDataURL(event.data);
      }
    };
    
    mediaRecorder.onstop = () => {
      console.log('Recording stopped');
    };
    
    try {
      mediaRecorder.start(2000);
      setIsRecording(true);
      
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.requestData();
        }
      }, 3000);
      
    } catch (error) {
      console.error('Failed to start MediaRecorder:', error);
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };
  
  const handleStart = async () => {
    if (mode === 'live') {
      if (!selectedConfig) {
        setError('Please select an activity first');
        return;
      }
      const sessionData = await startLiveSession();
      if (sessionData) {
        startRecording(sessionData.session_id);
      }
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
      const formData = new FormData();
      formData.append('video', file);
      formData.append('config_id', selectedConfig);
      formData.append('tts_provider', selectedTTSProvider);
      formData.append('voice_style', selectedVoiceStyle);
      
      const response = await fetch(`${config.apiUrl}/sessions/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      const startResponse = await fetch(`${config.apiUrl}/sessions/${data.session_id}/start`, {
        method: 'POST'
      });
      
      if (!startResponse.ok) {
        throw new Error(`Failed to start analysis: ${startResponse.statusText}`);
      }
      
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

  const getCategoryIcon = (category: string) => {
    const icons: { [key: string]: string } = {
      sports: '🏃‍♂️',
      health: '💪',
      instruments: '🎸',
      cooking: '👨‍🍳'
    };
    return icons[category] || '📋';
  };

  const getActivityIcon = (activity: string) => {
    const icons: { [key: string]: string } = {
      basketball_config: '🏀',
      soccer_config: '⚽',
      yoga_config: '🧘‍♀️',
      guitar_config: '🎸',
      sandwich_config: '🥪',
      sleep_config: '😴',
      hurdles_config: '🏃‍♂️',
      paddle_ball_config: '🏓',
      plyometrics_config: '💪'
    };
    return icons[activity] || '🎯';
  };

  const getVoiceIcon = (provider: string) => {
    return provider === 'chatgpt' ? '💬' : '🎤';
  };

  const getVoiceName = (provider: string) => {
    return provider === 'chatgpt' ? 'Clear Coach AI' : 'Natural Coach AI';
  };

  const getVoiceStyleName = (style: string) => {
    const styles: { [key: string]: string } = {
      'cheerful': 'Cheerful',
      'encouraging': 'Encouraging', 
      'professional': 'Professional',
      'friendly': 'Friendly',
      'energetic': 'Energetic'
    };
    return styles[style] || 'Cheerful';
  };

  const getVoiceStyleIcon = (style: string) => {
    const icons: { [key: string]: string } = {
      'cheerful': '😊',
      'encouraging': '💪',
      'professional': '👔', 
      'friendly': '🤝',
      'energetic': '⚡'
    };
    return icons[style] || '😊';
  };

  const getSelectedVoiceStyle = () => {
    return voiceStyles.find(style => style.id === selectedVoiceStyle) || voiceStyles[0];
  };

  const filteredConfigs = selectedCategory 
    ? configs.filter(config => config.category === selectedCategory)
    : [];

  const selectedConfigData = configs.find(c => c.id === selectedConfig);
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900">
      <Head>
        <title>NED</title>
        <meta name="description" content="Real-time coaching for sports and more" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <main className="container mx-auto px-6 py-8 max-w-lg">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-white mb-3">NED</h1>
          <p className="text-blue-200 text-base">NED</p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-400 rounded-lg text-red-200 text-sm text-center">
            {error}
          </div>
        )}

        {/* Loading Display */}
        {isLoading && (
          <div className="mb-6 text-center">
            <LoadingSpinner text="Loading..." />
          </div>
        )}

        {/* Mode Selection Tabs */}
        <div className="flex bg-blue-800/50 rounded-lg p-1 mb-8">
          <button
            type="button"
            className={`flex-1 py-4 px-6 text-base font-medium rounded-md transition-colors ${
              mode === 'live' 
                ? 'bg-blue-600 text-white shadow-sm' 
                : 'text-blue-200 hover:text-white'
            }`}
            onClick={() => setMode('live')}
          >
            Live Coaching
          </button>
          <button
            type="button"
            className={`flex-1 py-4 px-6 text-base font-medium rounded-md transition-colors ${
              mode === 'upload' 
                ? 'bg-blue-600 text-white shadow-sm' 
                : 'text-blue-200 hover:text-white'
            }`}
            onClick={() => setMode('upload')}
          >
            Upload Video
          </button>
        </div>

        {/* Activity Selection */}
        <div className="mb-4">
          <label className="block text-base font-medium text-blue-200 mb-3">
            Select Category:
          </label>
          <button
            onClick={() => setShowCategoryModal(true)}
            className="w-full bg-blue-800/50 border border-blue-600/50 rounded-lg p-4 flex items-center justify-between text-left hover:bg-blue-700/50 transition-colors"
          >
            <div className="flex items-center space-x-4">
              <span className="text-2xl">{getCategoryIcon(selectedCategory)}</span>
              <span className="text-white font-medium text-lg">
                {selectedCategory ? selectedCategory.charAt(0).toUpperCase() + selectedCategory.slice(1) : 'Select Category'}
              </span>
            </div>
            <span className="text-blue-300 text-xl">›</span>
          </button>
        </div>

        {selectedCategory && (
          <div className="mb-4">
            <label className="block text-base font-medium text-blue-200 mb-3">
              Select Activity:
            </label>
            <button
              onClick={() => setShowActivityModal(true)}
              className="w-full bg-blue-800/50 border border-blue-600/50 rounded-lg p-4 flex items-center justify-between text-left hover:bg-blue-700/50 transition-colors"
            >
              <div className="flex items-center space-x-4">
                <span className="text-2xl">{getActivityIcon(selectedConfig)}</span>
                <span className="text-white font-medium text-lg">
                  {selectedConfigData?.name || selectedConfig}
                </span>
              </div>
              <span className="text-blue-300 text-xl">›</span>
            </button>
          </div>
        )}

        {/* Voice Style Selection */}
        <div className="mb-4">
          <label className="block text-base font-medium text-blue-200 mb-3">
            Voice Style:
          </label>
          <button
            onClick={() => setShowVoiceModal(true)}
            className="w-full bg-blue-800/50 border border-blue-600/50 rounded-lg p-4 flex items-center justify-between text-left hover:bg-blue-700/50 transition-colors"
          >
            <div className="flex items-center space-x-4">
              <span className="text-2xl">{getVoiceStyleIcon(selectedVoiceStyle)}</span>
              <span className="text-white font-medium text-lg">
                {getVoiceStyleName(selectedVoiceStyle)}
              </span>
            </div>
            <span className="text-blue-300 text-xl">›</span>
          </button>
        </div>

        {/* Live Mode */}
        {mode === 'live' && (
          <div className="text-center">
            {/* Video Container */}
            <div className="relative mb-8">
              {/* Coach Avatar Overlay - Above Video */}
              {isRecording && (
                <div className="absolute -top-16 left-1/2 transform -translate-x-1/2 z-10">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-2xl border-4 border-blue-400/50">
                    <div className="w-14 h-14 rounded-full bg-gray-800 flex items-center justify-center">
                      <span className="text-xl">👨‍🏫</span>
                    </div>
                  </div>
                </div>
              )}
              
              <video
                ref={videoRef}
                autoPlay
                muted
                className="w-full aspect-video rounded-lg shadow-2xl bg-gray-900"
                style={{ transform: 'scaleX(-1)' }}
              />
            </div>
            
            {/* Control Button */}
            <div className="mt-8">
              {!isRecording ? (
                <button
                  onClick={handleStart}
                  disabled={isLoading || !selectedConfig}
                  className="w-full py-5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg text-lg"
                >
                  {isLoading ? 'Starting...' : !selectedConfig ? 'Select Activity First' : 'Start Live Coaching'}
                </button>
              ) : (
                <button
                  onClick={handleStop}
                  className="w-full py-5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 shadow-lg text-lg"
                >
                  End Session
                </button>
              )}
            </div>
          </div>
        )}

        {/* Upload Mode */}
        {mode === 'upload' && (
          <div className="text-center">
            <div className="mb-8">
              <label className="block text-base font-medium text-blue-200 mb-4">
                Upload Video:
              </label>
              <input
                type="file"
                accept="video/*"
                onChange={handleVideoUpload}
                disabled={isLoading}
                className="block w-full text-base text-gray-400
                  file:mr-4 file:py-4 file:px-6
                  file:rounded-lg file:border-0
                  file:text-base file:font-semibold
                  file:bg-blue-600 file:text-white
                  hover:file:bg-blue-700
                  disabled:opacity-50 disabled:cursor-not-allowed
                  bg-blue-800/50 border border-blue-600/50 rounded-lg p-4"
              />
            </div>
            
            {progress > 0 && (
              <div className="mb-8">
                <div className="w-full bg-blue-800/50 rounded-full h-4">
                  <div 
                    className="bg-blue-600 h-4 rounded-full transition-all duration-300" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="mt-3 text-base text-blue-200">{Math.round(progress)}% complete</p>
              </div>
            )}
            
            {videoUrl && (
              <div className="mt-8">
                <a 
                  href={videoUrl} 
                  download
                  className="w-full py-5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 shadow-lg block text-lg"
                >
                  Download Coached Video
                </a>
              </div>
            )}
            
            {feedback && (
              <div className="mt-8 p-5 bg-blue-800/50 rounded-lg border border-blue-600/50">
                <p className="text-blue-200 text-base">{feedback}</p>
              </div>
            )}
          </div>
        )}

        {/* Activity Selection Modal */}
        {showActivityModal && (
          <div 
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowActivityModal(false)}
          >
            <div 
              className="bg-blue-900 rounded-lg p-6 w-80 max-h-96 overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-white mb-4">Select Activity</h3>
              <div className="space-y-2">
                {filteredConfigs.map((config) => (
                  <button
                    key={config.id}
                    onClick={() => {
                      setSelectedConfig(config.id);
                      setSelectedCategory(config.category);
                      setShowActivityModal(false);
                    }}
                    className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-xl">{getActivityIcon(config.id)}</span>
                      <span className="text-white">{config.name}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Voice Selection Modal */}
        {showVoiceModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-blue-900 rounded-lg p-6 w-80">
              <h3 className="text-lg font-semibold text-white mb-4">Select Voice Style</h3>
              <div className="space-y-2">
                <button
                  onClick={() => {
                    setSelectedVoiceStyle('cheerful');
                    setShowVoiceModal(false);
                  }}
                  className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">😊</span>
                    <span className="text-white">Cheerful</span>
                  </div>
                </button>
                <button
                  onClick={() => {
                    setSelectedVoiceStyle('encouraging');
                    setShowVoiceModal(false);
                  }}
                  className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">💪</span>
                    <span className="text-white">Encouraging</span>
                  </div>
                </button>
                <button
                  onClick={() => {
                    setSelectedVoiceStyle('professional');
                    setShowVoiceModal(false);
                  }}
                  className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">👔</span>
                    <span className="text-white">Professional</span>
                  </div>
                </button>
                <button
                  onClick={() => {
                    setSelectedVoiceStyle('friendly');
                    setShowVoiceModal(false);
                  }}
                  className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">🤝</span>
                    <span className="text-white">Friendly</span>
                  </div>
                </button>
                <button
                  onClick={() => {
                    setSelectedVoiceStyle('energetic');
                    setShowVoiceModal(false);
                  }}
                  className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">⚡</span>
                    <span className="text-white">Energetic</span>
                  </div>
                </button>
              </div>
              <button
                onClick={() => setShowVoiceModal(false)}
                className="mt-4 w-full py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Category Selection Modal */}
        {showCategoryModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-blue-900 rounded-lg p-6 w-80 max-h-96 overflow-y-auto">
              <h3 className="text-lg font-semibold text-white mb-4">Select Category</h3>
              <div className="space-y-2">
                {categories.map((category) => (
                  <button
                    key={category}
                    onClick={() => {
                      setSelectedCategory(category);
                      // Set first activity from this category as default
                      const categoryConfigs = configs.filter(config => config.category === category);
                      if (categoryConfigs.length > 0) {
                        setSelectedConfig(categoryConfigs[0].id);
                      }
                      setShowCategoryModal(false);
                    }}
                    className="w-full p-3 text-left bg-blue-800/50 rounded-lg hover:bg-blue-700/50 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-xl">{getCategoryIcon(category)}</span>
                      <span className="text-white capitalize">{category}</span>
                    </div>
                  </button>
                ))}
              </div>
              <button
                onClick={() => setShowCategoryModal(false)}
                className="mt-4 w-full py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
