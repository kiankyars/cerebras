import { FC } from 'react';

interface FeedbackOverlayProps {
  feedback: string;
  timeElapsed: number;
}

const FeedbackOverlay: FC<FeedbackOverlayProps> = ({ feedback, timeElapsed }) => {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  if (!feedback) return null;

  return (
    <div className="absolute bottom-4 left-4 right-4 bg-black bg-opacity-70 text-white p-4 rounded-lg">
      <p>{feedback}</p>
      <p className="text-xs mt-2">Time: {formatTime(timeElapsed)}</p>
    </div>
  );
};

export default FeedbackOverlay;
