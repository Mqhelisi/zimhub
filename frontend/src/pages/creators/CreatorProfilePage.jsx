import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Loader2, Instagram, Facebook, Youtube, Music, ExternalLink,
  MapPin, Calendar, Ticket, ArrowLeft, Mail, MessageCircle,
} from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { TrackList, TypeBadges, accentRgb } from '../../modules/creator_platform/components/index.jsx';
import GalleryGrid from '../../modules/creator_platform/components/GalleryGrid.jsx';
import { mediaUrl } from '../../utils/media.js';

function fmtDate(s) {
  try {
    return new Date(s).toLocaleString('en-ZW', {
      weekday: 'short', day: 'numeric', month: 'short',
      hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Harare',
    });
  } catch { return s; }
}

const SOCIAL_ICONS = { instagram: Instagram, facebook: Facebook, youtube: Youtube };
const EXTERNAL_ICONS = { spotify: Music, soundcloud: Music, youtube: Youtube, behance: ExternalLink };

function LinkRow({ links, icons }) {
  const entries = Object.entries(links || {}).filter(([, v]) => v);
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {entries.map(([k, v]) => {
        const Icon = icons[k] || ExternalLink;
        const href = k === 'whatsapp'
          ? `https://wa.me/${String(v).replace(/[^\d]/g, '')}`
          : v;
        return (
          <a key={k} href={href} target="_blank" rel="noreferrer noopener"
             className="inline-flex items-center gap-1.5 rounded-full border border-bordr px-3 py-1.5 text-xs text-inkm hover:text-ink hover:border-[rgb(var(--section-accent)/0.6)]">
            {k === 'whatsapp' ? <MessageCircle size={13} /> : <Icon size={13} />}
            <span className="capitalize">{k}</span>
          </a>
        );
      })}
    </div>
  );
}

function EventsStrip({ events }) {
  if (!events.length) return <p className="text-sm text-inkm">No upcoming events.</p>;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {events.map((ce) => {
        const ticketed = ce.ticketing_mode === 'host_ticketing' && ce.host_event;
        return (
          <div key={ce.id} className="flex gap-3 rounded-xl border border-bordr bg-bgs p-3">
            <div className="h-20 w-16 shrink-0 overflow-hidden rounded-md bg-bgs2">
              {ce.poster_url && <img src={mediaUrl(ce.poster_url)} alt="" className="h-full w-full object-cover" />}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-ink">{ce.title}</div>
              <div className="mt-1 flex items-center gap-1 text-xs text-inkm">
                <Calendar size={12} /> {fmtDate(ce.event_date)}
              </div>
              {ce.venue_name && (
                <div className="mt-0.5 flex items-center gap-1 text-xs text-inkm">
                  <MapPin size={12} /> <span className="truncate">{ce.venue_name}</span>
                </div>
              )}
              <div className="mt-2">
                {ticketed ? (
                  <Link to={`/events/${ce.host_event_id}`} className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: 'rgb(var(--section-accent))' }}>
                    <Ticket size={13} /> Get tickets
                  </Link>
                ) : ce.external_ticket_url ? (
                  <a href={ce.external_ticket_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: 'rgb(var(--section-accent))' }}>
                    <ExternalLink size={13} /> {ce.ticket_price === 'free' ? 'Free — RSVP' : 'Details'}
                  </a>
                ) : (
                  <span className="text-xs text-inkm">{ce.ticket_price === 'free' ? 'Free entry' : ce.ticket_price}</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function CreatorProfilePage() {
  const { slug } = useParams();
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    setLoading(true); setNotFound(false);
    creatorApi.getCreator(slug)
      .then((r) => setCreator(r.creator))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return <div className="container-page flex items-center gap-2 py-20 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>;
  }
  if (notFound || !creator) {
    return (
      <div className="container-page py-20 text-center">
        <p className="text-inkm">Creator not found.</p>
        <Link to="/creators" className="mt-3 inline-block text-sm" style={{ color: 'rgb(var(--section-accent))' }}>← Back to creators</Link>
      </div>
    );
  }

  const accent = creator.accent_color || '#7c3aed';
  const modules = creator.modules || [];

  const SectionTitle = ({ children }) => (
    <h2 className="accent-rule mb-4 font-display text-3xl text-ink">{children}</h2>
  );

  const renderModule = (m) => {
    if (m === 'music' && creator.tracks?.length >= 0 && creator.creator_types.includes('musician')) {
      return (
        <section key="music" className="mt-12">
          <SectionTitle>Discography</SectionTitle>
          <TrackList tracks={creator.tracks} creator={creator} />
        </section>
      );
    }
    if ((m === 'gallery_photo' || m === 'gallery_art') && creator.collections?.length) {
      // Render gallery once even for multi (both gallery modules map to one grid).
      if (m === 'gallery_art' && creator.modules.includes('gallery_photo')) return null;
      return (
        <section key="gallery" className="mt-12">
          <SectionTitle>{creator.creator_types.includes('visual_artist') && !creator.creator_types.includes('photographer') ? 'Artwork' : 'Gallery'}</SectionTitle>
          <GalleryGrid collections={creator.collections} />
        </section>
      );
    }
    if (m === 'events') {
      return (
        <section key="events" className="mt-12">
          <SectionTitle>Events</SectionTitle>
          <EventsStrip events={creator.events || []} />
        </section>
      );
    }
    return null;
  };

  return (
    <div style={{ '--section-accent': accentRgb(accent) }}>
      {/* Hero */}
      <div className="creator-hero">
        {creator.hero_image_url && (
          <div className="absolute inset-0 opacity-40">
            <img src={mediaUrl(creator.hero_image_url)} alt="" className="h-full w-full object-cover" />
          </div>
        )}
        <div className="container-page relative pb-8 pt-10">
          <Link to="/creators" className="inline-flex items-center gap-1 text-sm text-inkm hover:text-ink">
            <ArrowLeft size={14} /> Creators
          </Link>
          <div className="mt-6 flex items-end gap-5">
            <div className="h-24 w-24 shrink-0 overflow-hidden rounded-full border-2 bg-bgs2" style={{ borderColor: 'rgb(var(--section-accent))' }}>
              {creator.photo_url && <img src={mediaUrl(creator.photo_url)} alt="" className="h-full w-full object-cover" />}
            </div>
            <div className="min-w-0">
              <TypeBadges types={creator.creator_types} />
              <h1 className="mt-2 font-display text-5xl leading-none text-ink sm:text-6xl">{creator.display_name}</h1>
            </div>
          </div>
          {creator.bio && <p className="mt-5 max-w-2xl text-sm leading-relaxed text-inkm">{creator.bio}</p>}
          {creator.discipline_tags?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {creator.discipline_tags.map((t) => (
                <span key={t} className="rounded-full bg-bgs2 px-2.5 py-0.5 text-[11px] text-inkm">#{t}</span>
              ))}
            </div>
          )}
          <div className="mt-4 space-y-2">
            <LinkRow links={creator.social_links} icons={SOCIAL_ICONS} />
            <LinkRow links={creator.external_links} icons={EXTERNAL_ICONS} />
            {creator.contact_email && (
              <a href={`mailto:${creator.contact_email}`} className="inline-flex items-center gap-1.5 text-xs text-inkm hover:text-ink">
                <Mail size={13} /> {creator.contact_email}
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Type-aware modules */}
      <main className="container-page pb-24">
        {modules.map(renderModule)}
      </main>
    </div>
  );
}
