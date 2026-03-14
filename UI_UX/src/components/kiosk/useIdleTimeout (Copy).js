/**
 * useIdleTimeout.js
 * Tracks user inactivity on a kiosk. Fires onWarn at `warnAt` seconds,
 * onExpire at `timeout` seconds of no interaction.
 */
import { useEffect, useRef, useState, useCallback } from 'react';

const EVENTS = ['mousedown', 'touchstart', 'keydown', 'scroll', 'mousemove'];

export function useIdleTimeout({ timeout = 300, warnAt = 30, onExpire, enabled = true }) {
  const [remaining, setRemaining]   = useState(null); // null = not warning yet
  const [isWarning, setIsWarning]   = useState(false);
  const timerRef   = useRef(null);
  const warnRef    = useRef(null);
  const countRef   = useRef(null);

  const reset = useCallback(() => {
    clearTimeout(timerRef.current);
    clearTimeout(warnRef.current);
    clearInterval(countRef.current);
    setIsWarning(false);
    setRemaining(null);

    if (!enabled) return;

    warnRef.current = setTimeout(() => {
      setIsWarning(true);
      setRemaining(warnAt);
      countRef.current = setInterval(() => {
        setRemaining(r => {
          if (r <= 1) { clearInterval(countRef.current); return 0; }
          return r - 1;
        });
      }, 1000);
    }, (timeout - warnAt) * 1000);

    timerRef.current = setTimeout(() => {
      clearInterval(countRef.current);
      onExpire?.();
    }, timeout * 1000);
  }, [timeout, warnAt, onExpire, enabled]);

  useEffect(() => {
    if (!enabled) return;
    reset();
    EVENTS.forEach(e => window.addEventListener(e, reset, { passive: true }));
    return () => {
      clearTimeout(timerRef.current);
      clearTimeout(warnRef.current);
      clearInterval(countRef.current);
      EVENTS.forEach(e => window.removeEventListener(e, reset));
    };
  }, [reset, enabled]);

  return { isWarning, remaining, reset };
}
