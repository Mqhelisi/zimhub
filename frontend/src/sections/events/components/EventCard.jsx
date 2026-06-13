import React from 'react';
import { Link } from 'react-router-dom';
import { Calendar, MapPin, User } from 'lucide-react';
import { ModePill } from './ModePill.jsx';

function fmtDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('en-ZW', {
      weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
      timeZone: 'Africa/Harare',
    });
  } catch { return iso; }
}

export function EventCard({ event, to }) {
  if (!event) return null;
  const href = to || `/events/${event.id}`;
  const poster = event.poster_thumb_url || event.poster_url;
  const isPast = event.is_past;
  return (
    <Link to={href} className="block group">
      <div className={`event-poster-frame transition ${isPast ? 'opacity-65' : ''}`}>
        {poster ? (
          <div className="aspect-[4/3] w-full bg-bgs2 overflow-hidden">
            <img src={poster} alt={event.title}
                 loading="lazy"
                 className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
          </div>
        ) : (
          <div className="aspect-[4/3] w-full bg-gradient-to-br from-bgs to-bgs2 flex items-center justify-center text-inkm">
            No poster
          </div>
        )}
        <div className="p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <ModePill event={event} />
            <span className="text-[10px] uppercase tracking-wider text-inkm">{event.category}</span>
          </div>
          <h3 className="text-ink font-display text-lg leading-snug line-clamp-2 group-hover:text-brand transition-colors">
            {event.title}
          </h3>
          <div className="text-xs text-inkm flex items-center gap-1.5">
            <Calendar size={12} /> {fmtDate(event.start_at)}
          </div>
          {event.location && (
            <div className="text-xs text-inkm flex items-center gap-1.5 truncate">
              <MapPin size={12} /> <span className="truncate">{event.location}</span>
            </div>
          )}
          {event.promoter && (
            <div className="text-xs text-inkm flex items-center gap-1.5 truncate pt-1 border-t border-bordr/40">
              <User size={12} />
              <span className="truncate">
                {event.promoter.organisation_name || event.promoter.name}
              </span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

export default EventCard;
