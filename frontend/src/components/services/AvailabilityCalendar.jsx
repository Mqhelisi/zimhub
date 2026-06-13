// Buyer-facing availability picker — a react-day-picker month beside the
// selected day's 30-minute slot grid. Read-only against the public
// /api/services/providers/:slug/availability feed; busy slots opaque.
import React, { useEffect, useMemo, useState } from 'react';
import { DayPicker } from 'react-day-picker';
import 'react-day-picker/style.css';
import { Loader2 } from 'lucide-react';
import { providerAvailability } from './api.js';

function dayKey(d) {
  return d.toISOString().slice(0, 10);
}

export default function AvailabilityCalendar({ slug, onSelectSlot, selectedStart }) {
  const [month, setMonth] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState(new Date());
  const [slots, setSlots] = useState({ available: [], busy: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const from = new Date();
        const to = new Date(from.getTime() + 1000 * 60 * 60 * 24 * 45);
        const data = await providerAvailability(slug, from.toISOString(), to.toISOString());
        if (!live) return;
        setSlots({ available: data.available_slots || [], busy: data.booked_slots || [] });
      } catch {
        if (live) setError('Could not load availability — try again shortly.');
      } finally {
        if (live) setLoading(false);
      }
    })();
    return () => { live = false; };
  }, [slug]);

  const availableByDay = useMemo(() => {
    const m = {};
    for (const s of slots.available) {
      const k = dayKey(new Date(s.start_at));
      (m[k] ||= []).push(s);
    }
    return m;
  }, [slots]);

  const busyByDay = useMemo(() => {
    const m = {};
    for (const s of slots.busy) {
      const k = dayKey(new Date(s.start_at));
      (m[k] ||= []).push(s);
    }
    return m;
  }, [slots]);

  const dayList = availableByDay[dayKey(selectedDay)] || [];
  const dayBusy = busyByDay[dayKey(selectedDay)] || [];

  if (loading) {
    return (
      <div className="card flex items-center gap-2 p-6 text-sm text-inkm">
        <Loader2 size={16} className="animate-spin" /> Loading availability…
      </div>
    );
  }
  if (error) return <div className="card p-6 text-sm text-danger">{error}</div>;

  return (
    <div className="card grid gap-6 p-5 md:grid-cols-[auto,1fr]">
      <DayPicker
        mode="single"
        month={month}
        onMonthChange={setMonth}
        selected={selectedDay}
        onSelect={(d) => d && setSelectedDay(d)}
        disabled={{ before: new Date() }}
        modifiers={{ hasSlots: (d) => (availableByDay[dayKey(d)] || []).length > 0 }}
        modifiersClassNames={{ hasSlots: 'font-semibold' }}
      />
      <div>
        <h4 className="mb-2 text-sm font-medium text-ink">
          {selectedDay.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })}
        </h4>
        {dayList.length === 0 && dayBusy.length === 0 && (
          <p className="text-sm text-inkm">No open slots this day — pick another date.</p>
        )}
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {[...dayList.map((s) => ({ ...s, kind: 'free' })),
            ...dayBusy.map((s) => ({ ...s, kind: 'busy' }))]
            .sort((a, b) => a.start_at.localeCompare(b.start_at))
            .map((s) => {
              const t = new Date(s.start_at).toLocaleTimeString(undefined,
                { hour: '2-digit', minute: '2-digit' });
              if (s.kind === 'busy') {
                return <div key={`b-${s.start_at}`} className="avail-slot busy">{t}</div>;
              }
              const selected = selectedStart === s.start_at;
              return (
                <button
                  key={s.start_at}
                  type="button"
                  className={`avail-slot free ${selected ? 'selected' : ''}`}
                  onClick={() => onSelectSlot?.(s)}
                >
                  {t}
                </button>
              );
            })}
        </div>
        <p className="mt-3 text-xs text-inkm">
          Times shown in your local time. Booked time is greyed out — no details are shared.
        </p>
      </div>
    </div>
  );
}
