import React from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, AlertCircle, XCircle, ArrowRight } from 'lucide-react';

function StatusBadge({ status }) {
  if (status === 'used') {
    return (
      <span className="pill" style={{ background: 'rgb(245 158 11 / 0.15)', color: 'rgb(245 158 11)', border: '1px solid rgb(245 158 11 / 0.4)' }}>
        <CheckCircle2 size={12} /> Used
      </span>
    );
  }
  if (status === 'voided') {
    return (
      <span className="pill" style={{ background: 'rgb(239 68 68 / 0.15)', color: 'rgb(239 68 68)', border: '1px solid rgb(239 68 68 / 0.4)' }}>
        <XCircle size={12} /> Voided
      </span>
    );
  }
  return (
    <span className="pill" style={{ background: 'rgb(34 197 94 / 0.15)', color: 'rgb(34 197 94)', border: '1px solid rgb(34 197 94 / 0.4)' }}>
      <AlertCircle size={12} /> Valid
    </span>
  );
}

export function TicketCard({ ticket }) {
  const ev = ticket.event || {};
  const tt = ticket.ticket_type || {};
  return (
    <Link to={`/my/tickets/${ticket.id}`} className="block">
      <div className="card card-hover p-4 flex items-center gap-3">
        {ev.poster_thumb_url ? (
          <img src={ev.poster_thumb_url} className="w-16 h-16 rounded-md object-cover" />
        ) : (
          <div className="w-16 h-16 rounded-md bg-bgs2" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusBadge status={ticket.status} />
            <span className="text-[10px] uppercase tracking-wider text-inkm">{tt.name || ''}</span>
          </div>
          <h3 className="text-ink truncate font-display text-base">{ev.title || 'Event'}</h3>
          <div className="text-xs text-inkm truncate">
            {ev.start_at ? new Date(ev.start_at).toLocaleString('en-ZW', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Harare' }) : ''}
            {ev.location ? ` • ${ev.location}` : ''}
          </div>
          <div className="text-xs text-inkm mt-0.5">
            Attendee: <span className="text-ink">{ticket.attendee_name}</span>
          </div>
        </div>
        <ArrowRight size={16} className="text-inkm" />
      </div>
    </Link>
  );
}

export default TicketCard;
