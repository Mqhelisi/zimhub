import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2, ArrowLeft, Calendar, MapPin, Ticket, ExternalLink } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { accentRgb } from '../../modules/creator_platform/components/index.jsx';
import { mediaUrl } from '../../utils/media.js';

function fmtDate(s) {
  try { return new Date(s).toLocaleString('en-ZW', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Harare' }); }
  catch { return s; }
}

export default function CreatorEventsPage() {
  const { slug } = useParams();
  const [creator, setCreator] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    Promise.all([creatorApi.getCreator(slug), creatorApi.getCreatorEvents(slug)])
      .then(([c, e]) => { setCreator(c.creator); setEvents(e.events); })
      .catch(() => {}).finally(() => setLoading(false));
  }, [slug]);
  if (loading) return <div className="container-page flex items-center gap-2 py-20 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>;
  if (!creator) return <div className="container-page py-20 text-inkm">Creator not found.</div>;
  return (
    <main className="container-page py-10" style={{ '--section-accent': accentRgb(creator.accent_color) }}>
      <Link to={`/creators/${slug}`} className="inline-flex items-center gap-1 text-sm text-inkm hover:text-ink"><ArrowLeft size={14} /> {creator.display_name}</Link>
      <h1 className="accent-rule mt-3 font-display text-4xl text-ink">Events</h1>
      {events.length === 0 ? (
        <p className="mt-6 text-inkm">No upcoming events.</p>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {events.map((ce) => {
            const ticketed = ce.ticketing_mode === 'host_ticketing' && ce.host_event;
            return (
              <div key={ce.id} className="overflow-hidden rounded-xl border border-bordr bg-bgs">
                {ce.poster_url && <img src={mediaUrl(ce.poster_url)} alt="" className="h-44 w-full object-cover" />}
                <div className="p-4">
                  <h3 className="font-display text-xl text-ink">{ce.title}</h3>
                  <div className="mt-2 flex items-center gap-1 text-sm text-inkm"><Calendar size={13} /> {fmtDate(ce.event_date)}</div>
                  {ce.venue_name && <div className="mt-1 flex items-center gap-1 text-sm text-inkm"><MapPin size={13} /> {ce.venue_name}</div>}
                  {ce.description && <p className="mt-2 line-clamp-2 text-sm text-inkm">{ce.description}</p>}
                  <div className="mt-3">
                    {ticketed ? (
                      <Link to={`/events/${ce.host_event_id}`} className="btn-accent"><Ticket size={15} /> Get tickets</Link>
                    ) : ce.external_ticket_url ? (
                      <a href={ce.external_ticket_url} target="_blank" rel="noreferrer noopener" className="btn-accent"><ExternalLink size={15} /> {ce.ticket_price === 'free' ? 'Free — RSVP' : 'Details'}</a>
                    ) : (
                      <span className="text-sm text-inkm">{ce.ticket_price === 'free' ? 'Free entry' : ce.ticket_price}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
