import React, { useState, useEffect } from 'react';
import { validateApiKeys } from '../utils/apiKeys';

interface ApiSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: () => void;
}

export const ApiSettingsModal: React.FC<ApiSettingsModalProps> = ({ 
  isOpen, 
  onClose,
  onSave,
}) => {
  const [googleApiKey, setGoogleApiKey] = useState('');
  const [trellisApiKey, setTrellisApiKey] = useState('');
  const [error, setError] = useState('');

  // Load saved API keys on mount
  useEffect(() => {
    const savedGoogleKey = localStorage.getItem('GOOGLE_API_KEY');
    const savedTrellisKey = localStorage.getItem('TRELLIS_API_KEY');
    if (savedGoogleKey) setGoogleApiKey(savedGoogleKey);
    if (savedTrellisKey) setTrellisApiKey(savedTrellisKey);
  }, []);

  const handleSave = () => {
    // Validate inputs
    if (!googleApiKey.trim() || !trellisApiKey.trim()) {
      setError('Both API keys are required');
      return;
    }

    // Save to localStorage
    localStorage.setItem('GOOGLE_API_KEY', googleApiKey.trim());
    localStorage.setItem('TRELLIS_API_KEY', trellisApiKey.trim());
    
    // Clear any errors
    setError('');
    
    onClose();
    onSave?.();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 10000000,
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '24px',
        borderRadius: '8px',
        width: '400px',
        maxWidth: '90%',
      }}>
        <h2 style={{ margin: '0 0 16px 0' }}>API Settings</h2>
        
        {error && (
          <div style={{
            padding: '8px',
            marginBottom: '16px',
            backgroundColor: '#ffebee',
            color: '#c62828',
            borderRadius: '4px',
          }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px' }}>
            Google API Key
            <span style={{ color: 'red' }}> *</span>
          </label>
          <input
            type="password"
            value={googleApiKey}
            onChange={(e) => {
              setGoogleApiKey(e.target.value);
              setError('');
            }}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ccc',
            }}
            placeholder="Enter Google API Key"
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px' }}>
            Trellis API Key
            <span style={{ color: 'red' }}> *</span>
          </label>
          <input
            type="password"
            value={trellisApiKey}
            onChange={(e) => {
              setTrellisApiKey(e.target.value);
              setError('');
            }}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ccc',
            }}
            placeholder="Enter Trellis API Key"
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #ccc',
              backgroundColor: 'white',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: '#007bff',
              color: 'white',
              cursor: 'pointer',
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
} 