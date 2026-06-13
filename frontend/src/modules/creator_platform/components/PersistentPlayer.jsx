import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Play, Pause, SkipBack, SkipForward, X, Volume2, Music2 } from 'lucide-react';
import { usePlayer } from '../../../contexts/PlayerContext.jsx';
import { mediaUrl } from '../../../utils/media.js';

function fmt(sec) {
  if (!sec || !isFinite(sec)) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

/**
 * Docked player bar. Rendered once at the App root so it survives navigation
 * across ALL sections. Shows only when a track is loaded. Hidden on the gate
 * scanner (a deliberately chrome-free surface) — audio keeps playing regardless
 * since Howler is detached from the DOM.
 */
export default function PersistentPlayer() {
  const { pathname } = useLocation();
  const {
    current, isPlaying, position, duration, volume,
    hasNext, hasPrev, toggle, seek, next, prev, setVolume, close,
  } = usePlayer();

  if (!current) return null;
  if (pathname.startsWith('/gate')) return null;

  const accent = current.creator?.accent_color || '#7c3aed';
  const pct = duration ? Math.min(100, (position / duration) * 100) : 0;
  const accentRgb = hexToRgb(accent);

  const onScrub = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    seek(ratio * (duration || 0));
  };

  return (
    <div
      className="zh-player fixed inset-x-0 bottom-0 z-40"
      style={{ '--player-accent': accentRgb }}
    >
      {/* scrub bar */}
      <div className="zh-player-scrub-track h-1 w-full cursor-pointer" onClick={onScrub}>
        <div className="zh-player-progress h-1" style={{ width: `${pct}%` }} />
      </div>

      <div className="container-page flex items-center gap-3 py-2.5">
        {/* cover + meta */}
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="h-11 w-11 shrink-0 overflow-hidden rounded-md bg-bgs2">
            {current.cover_art_url ? (
              <img src={mediaUrl(current.cover_art_url)} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-inkm">
                <Music2 size={18} />
              </div>
            )}
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-ink">{current.title}</div>
            {current.creator ? (
              <Link
                to={`/creators/${current.creator.creator_slug}`}
                className="truncate text-xs text-inkm hover:text-ink"
              >
                {current.creator.display_name}
              </Link>
            ) : (
              current.featuring && <div className="truncate text-xs text-inkm">{current.featuring}</div>
            )}
          </div>
        </div>

        {/* transport */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={prev} disabled={!hasPrev}
            className="rounded-full p-2 text-inkm hover:text-ink disabled:opacity-30"
            aria-label="Previous"
          >
            <SkipBack size={18} />
          </button>
          <button
            onClick={toggle}
            className="flex h-10 w-10 items-center justify-center rounded-full text-[#0b0b10]"
            style={{ background: accent }}
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
          </button>
          <button
            onClick={next} disabled={!hasNext}
            className="rounded-full p-2 text-inkm hover:text-ink disabled:opacity-30"
            aria-label="Next"
          >
            <SkipForward size={18} />
          </button>
        </div>

        {/* time */}
        <div className="hidden w-24 shrink-0 text-right text-xs tabular-nums text-inkm sm:block">
          {fmt(position)} / {fmt(duration)}
        </div>

        {/* volume (desktop) */}
        <div className="hidden items-center gap-2 md:flex">
          <Volume2 size={16} className="text-inkm" />
          <input
            type="range" min="0" max="1" step="0.05" value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="h-1 w-20 cursor-pointer accent-current"
            style={{ color: accent }}
            aria-label="Volume"
          />
        </div>

        <button onClick={close} className="rounded-full p-2 text-inkm hover:text-ink" aria-label="Close player">
          <X size={18} />
        </button>
      </div>
    </div>
  );
}

function hexToRgb(hex) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || '');
  if (!m) return '124 58 237';
  return `${parseInt(m[1], 16)} ${parseInt(m[2], 16)} ${parseInt(m[3], 16)}`;
}
