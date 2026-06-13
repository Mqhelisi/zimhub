import React, { createContext, useContext, useRef, useState, useEffect, useCallback } from 'react';
import { Howl } from 'howler';
import { mediaUrl } from '../utils/media.js';
import { creatorApi } from '../modules/creator_platform/api.js';

const PlayerContext = createContext(null);

// One session id per page load — used to dedupe play counts server-side.
const SESSION_ID =
  (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
  `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;

/**
 * App-global audio player. Mounted ABOVE the router (in App.jsx) so the Howl
 * instance and all state survive route changes across every section — start a
 * track on a creator page, keep listening in /shop, /events, /services.
 */
export function PlayerProvider({ children }) {
  const howlRef = useRef(null);
  const rafRef = useRef(null);
  const playedRecordedRef = useRef(false);   // play-count 30s rule, per track load

  const [queue, setQueue] = useState([]);     // array of track objects
  const [index, setIndex] = useState(-1);     // current index in queue
  const [current, setCurrent] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(0.9);

  const stopRaf = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  };

  const tick = useCallback(() => {
    const h = howlRef.current;
    if (h && h.playing()) {
      const pos = h.seek() || 0;
      setPosition(pos);
      // Record a play after 30s of continuous listening (once per load).
      if (!playedRecordedRef.current && pos >= 30 && current?.id) {
        playedRecordedRef.current = true;
        creatorApi.recordPlay(current.id, SESSION_ID).catch(() => {});
      }
      rafRef.current = requestAnimationFrame(tick);
    }
  }, [current]);

  const _unload = () => {
    stopRaf();
    if (howlRef.current) {
      howlRef.current.unload();
      howlRef.current = null;
    }
  };

  const _loadIndex = useCallback((q, i) => {
    if (i < 0 || i >= q.length) return;
    const track = q[i];
    _unload();
    playedRecordedRef.current = false;
    const howl = new Howl({
      src: [mediaUrl(track.audio_url)],
      html5: true,           // stream + range requests (seek) instead of full buffer
      volume,
      onload: () => setDuration(howl.duration() || 0),
      onplay: () => { setIsPlaying(true); rafRef.current = requestAnimationFrame(tick); },
      onpause: () => { setIsPlaying(false); stopRaf(); },
      onend: () => {
        setIsPlaying(false);
        stopRaf();
        // advance to next in queue if any
        setIndex((cur) => {
          const next = cur + 1;
          if (next < q.length) { _loadIndex(q, next); return next; }
          setPosition(0);
          return cur;
        });
      },
    });
    howlRef.current = howl;
    setCurrent(track);
    setIndex(i);
    setPosition(0);
    setDuration(0);
    howl.play();
  }, [volume, tick]);

  // Play a single track (optionally as part of a queue).
  const playTrack = useCallback((track, q = null) => {
    const newQueue = q && q.length ? q : [track];
    const i = Math.max(0, newQueue.findIndex((t) => t.id === track.id));
    setQueue(newQueue);
    _loadIndex(newQueue, i < 0 ? 0 : i);
  }, [_loadIndex]);

  const toggle = useCallback(() => {
    const h = howlRef.current;
    if (!h) return;
    if (h.playing()) h.pause();
    else h.play();
  }, []);

  const seek = useCallback((sec) => {
    const h = howlRef.current;
    if (!h) return;
    h.seek(sec);
    setPosition(sec);
  }, []);

  const next = useCallback(() => {
    if (index + 1 < queue.length) _loadIndex(queue, index + 1);
  }, [index, queue, _loadIndex]);

  const prev = useCallback(() => {
    const h = howlRef.current;
    if (h && (h.seek() || 0) > 3) { seek(0); return; }   // restart if >3s in
    if (index - 1 >= 0) _loadIndex(queue, index - 1);
  }, [index, queue, _loadIndex, seek]);

  const setVolume = useCallback((v) => {
    setVolumeState(v);
    if (howlRef.current) howlRef.current.volume(v);
  }, []);

  const close = useCallback(() => {
    _unload();
    setCurrent(null);
    setQueue([]);
    setIndex(-1);
    setIsPlaying(false);
    setPosition(0);
    setDuration(0);
  }, []);

  useEffect(() => () => _unload(), []);

  const value = {
    current, queue, index, isPlaying, position, duration, volume,
    hasNext: index + 1 < queue.length,
    hasPrev: index > 0,
    playTrack, toggle, seek, next, prev, setVolume, close,
  };
  return <PlayerContext.Provider value={value}>{children}</PlayerContext.Provider>;
}

export function usePlayer() {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error('usePlayer must be used within PlayerProvider');
  return ctx;
}
