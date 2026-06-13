import React from 'react';
import { Link } from 'react-router-dom';
import { Play, Pause, Music2, Image as ImageIcon, Palette } from 'lucide-react';
import { usePlayer } from '../../../contexts/PlayerContext.jsx';
import { mediaUrl } from '../../../utils/media.js';

export function accentRgb(hex) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || '');
  if (!m) return '124 58 237';
  return `${parseInt(m[1], 16)} ${parseInt(m[2], 16)} ${parseInt(m[3], 16)}`;
}

const TYPE_META = {
  musician: { label: 'Musician', Icon: Music2 },
  photographer: { label: 'Photographer', Icon: ImageIcon },
  visual_artist: { label: 'Visual Artist', Icon: Palette },
};

export function TypeBadges({ types = [], className = '' }) {
  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      {types.map((t) => {
        const meta = TYPE_META[t] || { label: t, Icon: Music2 };
        const { Icon } = meta;
        return (
          <span key={t} className="creator-type-badge">
            <Icon size={11} /> {meta.label}
          </span>
        );
      })}
    </div>
  );
}

export function CreatorCard({ creator }) {
  const accent = creator.accent_color || '#7c3aed';
  return (
    <Link
      to={`/creators/${creator.creator_slug}`}
      className="group block overflow-hidden rounded-xl border border-bordr bg-bgs transition hover:-translate-y-0.5"
      style={{ '--section-accent': accentRgb(accent) }}
    >
      <div className="relative h-36 overflow-hidden bg-bgs2">
        {creator.hero_image_url ? (
          <img
            src={mediaUrl(creator.hero_image_url)}
            alt=""
            className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="h-full w-full" style={{ background: `rgb(${accentRgb(accent)} / 0.25)` }} />
        )}
        <div
          className="absolute inset-0"
          style={{ background: `linear-gradient(180deg, transparent 40%, rgb(9 9 13 / 0.92))` }}
        />
        <div className="absolute -bottom-6 left-4 h-14 w-14 overflow-hidden rounded-full border-2 border-bgp bg-bgs2">
          {creator.photo_url && (
            <img src={mediaUrl(creator.photo_url)} alt="" className="h-full w-full object-cover" />
          )}
        </div>
      </div>
      <div className="px-4 pb-4 pt-8">
        <h3 className="font-display text-xl leading-tight text-ink">{creator.display_name}</h3>
        <TypeBadges types={creator.creator_types} className="mt-2" />
        {creator.bio && <p className="mt-2 line-clamp-2 text-xs text-inkm">{creator.bio}</p>}
      </div>
    </Link>
  );
}

/** Liner-notes style numbered track list with play/pause. */
export function TrackList({ tracks = [], creator }) {
  const { current, isPlaying, playTrack, toggle } = usePlayer();
  if (!tracks.length) {
    return <p className="text-sm text-inkm">No tracks published yet.</p>;
  }
  // Attach the creator's display info so the player can link back + accent.
  const enriched = tracks.map((t) => ({
    ...t,
    creator: t.creator || (creator && {
      creator_slug: creator.creator_slug,
      display_name: creator.display_name,
      accent_color: creator.accent_color,
    }),
  }));

  return (
    <div className="divide-y divide-bordr/60 overflow-hidden rounded-xl border border-bordr">
      {enriched.map((t, i) => {
        const active = current?.id === t.id;
        return (
          <div
            key={t.id}
            className="track-row flex items-center gap-3 border-l-2 border-transparent px-4 py-3"
            data-active={active ? 'true' : 'false'}
          >
            <button
              onClick={() => (active ? toggle() : playTrack(t, enriched))}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-bordr text-ink hover:border-[rgb(var(--section-accent))]"
              aria-label={active && isPlaying ? 'Pause' : 'Play'}
            >
              {active && isPlaying ? <Pause size={15} /> : <Play size={15} className="ml-0.5" />}
            </button>
            <span className="track-index w-6 text-sm">{String(i + 1).padStart(2, '0')}</span>
            {t.cover_art_url && (
              <img src={mediaUrl(t.cover_art_url)} alt="" className="hidden h-9 w-9 rounded object-cover sm:block" />
            )}
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-ink">{t.title}</div>
              <div className="truncate text-xs text-inkm">
                {[t.featuring && `feat. ${t.featuring}`, t.genre, t.album].filter(Boolean).join(' · ')}
              </div>
            </div>
            <span className="shrink-0 text-xs tabular-nums text-inkm">{t.play_count} plays</span>
          </div>
        );
      })}
    </div>
  );
}
