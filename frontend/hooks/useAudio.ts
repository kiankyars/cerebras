import { useCallback, useRef } from 'react';

export const useAudio = () => {
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);

  const initializeAudio = useCallback(async () => {
    if (typeof window === 'undefined') return;
    
    if (!audioContextRef.current) {
      try {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        
        // Resume context if suspended (required by browser autoplay policies)
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume();
        }
      } catch (error) {
        console.error('Failed to initialize audio context:', error);
      }
    }
  }, []);

  const playTextToSpeech = useCallback(async (text: string) => {
    if (typeof window === 'undefined' || !text || !('speechSynthesis' in window)) {
      console.warn('Speech synthesis not supported');
      return;
    }

    // Add to queue
    audioQueueRef.current.push(text);
    
    // If already playing, return
    if (isPlayingRef.current) {
      return;
    }

    // Process queue
    while (audioQueueRef.current.length > 0) {
      const currentText = audioQueueRef.current.shift()!;
      isPlayingRef.current = true;

      await new Promise<void>((resolve) => {
        const utterance = new SpeechSynthesisUtterance(currentText);
        
        // Configure voice settings
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 0.8;
        
        // Try to use a good voice
        const voices = speechSynthesis.getVoices();
        const preferredVoice = voices.find(voice => 
          voice.lang.startsWith('en') && (voice.name.includes('Female') || voice.name.includes('Natural'))
        );
        if (preferredVoice) {
          utterance.voice = preferredVoice;
        }

        utterance.onend = () => {
          isPlayingRef.current = false;
          resolve();
        };

        utterance.onerror = (error) => {
          console.error('Speech synthesis error:', error);
          isPlayingRef.current = false;
          resolve();
        };

        speechSynthesis.speak(utterance);
      });

      // Small delay between utterances
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }, []);

  const stopAudio = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      speechSynthesis.cancel();
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
  }, []);

  return {
    initializeAudio,
    playTextToSpeech,
    stopAudio,
    isAudioSupported: typeof window !== 'undefined' && 'speechSynthesis' in window,
  };
};