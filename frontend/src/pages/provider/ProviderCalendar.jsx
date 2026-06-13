// /provider/calendar — the provider's resolved week: confirmed solid,
// requested semi-transparent + pulse, blocks cross-hatched, availability
// rules tinting the open-hours background (Stage 4 §6.5). react-big-calendar
// with the date-fns localizer.
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enGB } from 'date-fns/locale';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { providerCalendar } from '../../modules/booking_interface/api.js';
import { Modal } from '../../components/ui/Modal.jsx';
import {
  BookingStatusBadge, BookingActions, fmtRange,
} from '../../modules/booking_interface/components/BookingPrimitives.jsx';

const localizer = dateFnsLocalizer({
  format, parse, startOfWeek: (d) => startOfWeek(d, { locale: enGB }), getDay,
  locales: { 'en-GB': enGB },
});

export default function ProviderCalendar() {
  const [range, setRange] = useState(() => {
    const from = startOfWeek(new Date(), { locale: enGB });
    const to = new Date(from.getTime() + 7 * 86400000);
    return { from, to };
  });
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = useCallback(() => {
    providerCalendar(range.from.toISOString(), range.to.toISOString())
      .then(setData).catch(() => setData({ bookings: [], time_blocks: [], availability_rules: [] }));
  }, [range]);
  useEffect(load, [load]);

  const events = useMemo(() => {
    if (!data) return [];
    const bookingEvents = (data.bookings || [])
      .filter((b) => ['requested', 'confirmed', 'disputed', 'no_show', 'completed'].includes(b.status))
      .map((b) => ({
        id: b.id,
        title: `${b.label || 'Booking'}${b.requester?.name ? ` — ${b.requester.name}` : ''}`,
        start: new Date(b.start_at),
        end: new Date(b.end_at),
        resource: { kind: 'booking', booking: b },
      }));
    const blockEvents = (data.time_blocks || []).map((bl) => ({
      id: bl.id,
      title: bl.reason || 'Blocked',
      start: new Date(bl.start_at),
      end: new Date(bl.end_at),
      resource: { kind: 'block' },
    }));
    return [...bookingEvents, ...blockEvents];
  }, [data]);

  // Tint open hours via slotPropGetter — availability rules are weekly,
  // local-time HH:MM windows per weekday (Mon=0 … Sun=6).
  const rulesByDay = useMemo(() => {
    const m = {};
    for (const r of data?.availability_rules || []) {
      (m[r.weekday] ||= []).push(r);
    }
    return m;
  }, [data]);

  const slotPropGetter = useCallback((date) => {
    const weekday = (date.getDay() + 6) % 7; // JS Sun=0 → spec Mon=0
    const hm = format(date, 'HH:mm');
    const open = (rulesByDay[weekday] || []).some(
      (r) => r.start_time <= hm && hm < r.end_time,
    );
    return open ? { className: 'availability-tint' } : {};
  }, [rulesByDay]);

  const eventPropGetter = useCallback((event) => {
    if (event.resource.kind === 'block') return { className: 'calendar-block' };
    const st = event.resource.booking.status;
    if (st === 'requested') return { className: 'booking-requested' };
    if (st === 'confirmed') return { className: 'booking-confirmed' };
    return { className: 'booking-terminal' };
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="heading-accent font-display text-2xl text-ink">Calendar</h1>
        <div className="flex items-center gap-3 text-xs text-inkm">
          <span className="inline-flex items-center gap-1.5">
            <i className="inline-block h-3 w-3 rounded-sm bg-[rgb(var(--section-accent))]" /> Confirmed
          </span>
          <span className="inline-flex items-center gap-1.5">
            <i className="inline-block h-3 w-3 rounded-sm border border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.35)]" /> Requested
          </span>
          <span className="inline-flex items-center gap-1.5">
            <i className="inline-block h-3 w-3 rounded-sm border border-dashed border-inkm bg-bgs2" /> Blocked
          </span>
        </div>
      </div>
      <div className="card p-4" style={{ height: 640 }}>
        <Calendar
          localizer={localizer}
          events={events}
          defaultView="week"
          views={['week', 'day', 'agenda']}
          step={30}
          timeslots={2}
          min={new Date(1970, 0, 1, 6, 0)}
          max={new Date(1970, 0, 1, 21, 0)}
          slotPropGetter={slotPropGetter}
          eventPropGetter={eventPropGetter}
          onSelectEvent={(ev) => ev.resource.kind === 'booking' && setSelected(ev.resource.booking)}
          onRangeChange={(r) => {
            const from = Array.isArray(r) ? r[0] : r.start;
            const to = Array.isArray(r) ? new Date(r[r.length - 1].getTime() + 86400000) : r.end;
            if (from && to) setRange({ from, to });
          }}
          style={{ height: '100%' }}
        />
      </div>

      <Modal open={!!selected} onClose={() => setSelected(null)}
             title={selected?.label || 'Booking'}>
        {selected && (
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <BookingStatusBadge status={selected.status} />
              <span className="text-inkm">{fmtRange(selected)}</span>
            </div>
            {selected.requester?.name && (
              <p className="text-ink">
                {selected.requester.name}
                {selected.requester.phone && <span className="text-inkm"> · {selected.requester.phone}</span>}
              </p>
            )}
            {selected.message && (
              <p className="rounded-md border border-bordr bg-bgs2 p-2.5 text-inkm">{selected.message}</p>
            )}
            <BookingActions booking={selected} onChanged={() => { setSelected(null); load(); }} />
          </div>
        )}
      </Modal>
    </div>
  );
}
