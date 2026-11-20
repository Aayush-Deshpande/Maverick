import React, { useEffect, useRef, useState, useCallback } from 'react';
import './anumaan-splash.css';

interface AnumaanSplashProps {
  onComplete?: () => void;
  videoSrc?: string;
  forceShow?: boolean;
}

export const AnumaanSplash: React.FC<AnumaanSplashProps> = ({
  onComplete,
  videoSrc = '/vids/Anumaan_start.mp4',
  forceShow = false,
}) => {
  // STRICT "ALWAYS-PLAY" RULE:
  // Must be the absolute first thing displayed on EVERY single page load.
  // Never consult or persist to localStorage, sessionStorage, or cookies.
  const [isMounted, setIsMounted] = useState<boolean>(true);
  const [isExiting, setIsExiting] = useState<boolean>(false);
  const [isVideoReady, setIsVideoReady] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismiss = useCallback(
    (reason: string = 'video-ended') => {
      if (isExiting) return;
      console.log(`[AnumaanSplash] Intro animation finished (${reason}). Transitioning to landing...`);
      setIsExiting(true);

      // Allow CSS fade/blur transition (720ms) to complete before unmounting
      setTimeout(() => {
        setIsMounted(false);
        onComplete?.();
      }, 750);
    },
    [isExiting, onComplete]
  );

  // Re-trigger if forceShow prop changes to true (e.g. replaying from nav logo)
  useEffect(() => {
    if (forceShow) {
      setIsMounted(true);
      setIsExiting(false);
      setIsVideoReady(false);
    }
  }, [forceShow]);

  // Handle native video playback and lifecycle
  useEffect(() => {
    if (!isMounted || isExiting) return;

    // Prevent body scroll during full-screen splash presentation
    document.body.classList.add('ae-splash-active');

    const video = videoRef.current;
    if (video) {
      video.muted = true;
      video.playsInline = true;

      const attemptPlay = () => {
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              setIsVideoReady(true);
              console.log('[AnumaanSplash] Logo animation playback active');
            })
            .catch((err) => {
              console.warn('[AnumaanSplash] Playback autoplay constrained:', err);
              // Fallback transition if browser blocks inline media autoplay
              dismiss('playback-constrained');
            });
        }
      };

      if (video.readyState >= 2) {
        attemptPlay();
      } else {
        video.addEventListener('loadeddata', attemptPlay, { once: true });
        video.addEventListener('canplay', attemptPlay, { once: true });
      }
    }

    // Optional user bypass via keyboard (Esc/Space/Enter)
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        dismiss('keyboard-skip');
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    // Fallback safety timeout (8.0s) so user is never trapped if browser media pipeline stalls
    dismissTimerRef.current = setTimeout(() => {
      dismiss('safety-timeout');
    }, 8000);

    return () => {
      document.body.classList.remove('ae-splash-active');
      window.removeEventListener('keydown', handleKeyDown);
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
      }
    };
  }, [isMounted, isExiting, dismiss]);

  if (!isMounted) return null;

  return (
    <div
      className={`ae-splash-root ${isExiting ? 'ae-splash-exiting' : ''}`}
      aria-hidden="true"
      role="presentation"
    >
      {/* Background ambient wash seamlessly matched with landing paper tone */}
      <div className="ae-splash-backdrop" />

      {/* Military HUD Metadata Banner */}
      <div className="ae-splash-hud-meta">
        <span className="ae-splash-pill">ANUMAAN // INIT_SEQUENCE</span>
        <span className="ae-splash-serial">DRDO PS-26054</span>
      </div>

      {/* Native Video Layer without player visual controls */}
      <div className="ae-splash-stage">
        <video
          ref={videoRef}
          className={`ae-splash-video ${isVideoReady ? 'is-playing' : ''}`}
          src={videoSrc}
          autoPlay
          muted
          playsInline
          disablePictureInPicture
          disableRemotePlayback
          controls={false}
          tabIndex={-1}
          preload="auto"
          onEnded={() => dismiss('video-ended')}
          onContextMenu={(e) => e.preventDefault()}
        />
      </div>

      {/* Minimal technical progress line at bottom */}
      <div className="ae-splash-progress">
        <div className="ae-splash-progress-bar" />
      </div>
    </div>
  );
};

export default AnumaanSplash;
