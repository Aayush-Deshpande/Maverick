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
  const [isMounted, setIsMounted] = useState(() => {
    if (forceShow) return true;
    try {
      return !sessionStorage.getItem('anumaan_splash_shown');
    } catch {
      return true;
    }
  });

  const [isExiting, setIsExiting] = useState(false);
  const [isVideoReady, setIsVideoReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismiss = useCallback((reason: string = 'ended') => {
    if (isExiting) return;
    console.log(`[AnumaanSplash] Dismissing intro (${reason})`);
    setIsExiting(true);
    try {
      sessionStorage.setItem('anumaan_splash_shown', 'true');
    } catch {
      // storage unavailable
    }

    // Complete transition and unmount after CSS fade finishes
    setTimeout(() => {
      setIsMounted(false);
      onComplete?.();
    }, 750);
  }, [isExiting, onComplete]);

  // If forceShow prop toggles to true, remount splash
  useEffect(() => {
    if (forceShow) {
      setIsMounted(true);
      setIsExiting(false);
      setIsVideoReady(false);
    }
  }, [forceShow]);

  // Initial setup: ensure video is 100% muted so Chrome/Safari never block autoplay
  useEffect(() => {
    if (!isMounted || isExiting) return;

    // Lock body scrolling while intro splash is active
    document.body.classList.add('ae-splash-active');

    const video = videoRef.current;
    if (video) {
      video.muted = true;
      video.playsInline = true;

      const attemptPlay = () => {
        video.play().then(() => {
          setIsVideoReady(true);
          console.log('[AnumaanSplash] Playback started successfully');
        }).catch((err) => {
          console.warn('[AnumaanSplash] Autoplay blocked, dismissing:', err);
          dismiss('autoplay-blocked');
        });
      };

      if (video.readyState >= 2) {
        attemptPlay();
      } else {
        video.addEventListener('loadeddata', attemptPlay, { once: true });
        video.addEventListener('canplay', attemptPlay, { once: true });
      }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === ' ' || e.key === 'Enter') {
        dismiss('keyboard-skip');
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    // Fallback safety timeout (6.8s) to guarantee landing page displays even if video fails
    dismissTimerRef.current = setTimeout(() => {
      dismiss('safety-timeout');
    }, 6800);

    return () => {
      document.body.classList.remove('ae-splash-active');
      window.removeEventListener('keydown', handleKeyDown);
      if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);
    };
  }, [isMounted, isExiting, dismiss]);

  if (!isMounted) return null;

  return (
    <div
      className={`ae-splash-root ${isExiting ? 'ae-splash-exiting' : ''}`}
      aria-hidden="true"
      role="presentation"
    >
      {/* Background ambient texture & color matching landing theme */}
      <div className="ae-splash-backdrop" />

      {/* Futuristic Telemetry Header Badge */}
      <div className="ae-splash-hud-meta">
        <span className="ae-splash-pill">ANUMAAN // INIT_SEQUENCE</span>
        <span className="ae-splash-serial">DRDO PS-26054</span>
      </div>

      {/* Main Native Video Layer */}
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
          preload="metadata"
          onEnded={() => dismiss('video-ended')}
          onContextMenu={(e) => e.preventDefault()}
        />
      </div>

      {/* Minimal subtle skip trigger */}
      <button
        type="button"
        className="ae-splash-skip"
        onClick={() => dismiss('skip-clicked')}
        title="Skip intro (Esc)"
      >
        <span>Skip intro</span>
        <kbd>ESC</kbd>
      </button>

      {/* Minimal technical progress line at bottom */}
      <div className="ae-splash-progress">
        <div className="ae-splash-progress-bar" />
      </div>
    </div>
  );
};
