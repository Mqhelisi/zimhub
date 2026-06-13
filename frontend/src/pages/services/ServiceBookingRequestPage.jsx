// /services/providers/:slug/book/:serviceId — the booking request flow:
// calendar slot pick → duration → notes (+ distance for per_km) → estimate →
// submit. Estimate rules per Stage 4 §6.4: flat = rate; per_hour = rate ×
// duration; per_day = rate × ceil(days); per_km = NO estimate ("billed by
// distance — agree with your provider"). Auth gate: redirect to /login?next=.
import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link, useLocation } from 'react-router-dom';
import { CalendarClock, Info } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { useToast } from '../../components/ui/Toast.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { errMessage } from '../../api/client.js';
import { providerBySlug } from '../../components/services/api.js';
import { createBooking } from '../../modules/booking_interface/api.js';
import AvailabilityCalendar from '../../components/services/AvailabilityCalendar.jsx';
import { PricingUnitChip } from '../../components/services/ServicesSectionLayout.jsx';

const DUR_CHOICES = [0.5, 1, 1.5, 2, 3, 4, 6, 8];

export default function ServiceBookingRequestPage() {
  const { slug, serviceId } = useParams();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const [data, setData] = useState(null);
  const [slot, setSlot] = useState(null);          // {start_at, end_at}
  const [hours, setHours] = useState(null);
  const [notes, setNotes] = useState('');
  const [distanceKm, setDistanceKm] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    providerBySlug(slug).then(setData).catch(() => setData({ missing: true }));
  }, [slug]);

  const service = useMemo(
    () => data?.services?.find((s) => s.id === serviceId),
    [data, serviceId],
  );

  useEffect(() => {
    if (service && hours === null) {
      setHours(service.default_duration_minutes
        ? Math.max(0.5, service.default_duration_minutes / 60)
        : 1);
    }
  }, [service, hours]);

  // Auth gate — login first, come back here.
  useEffect(() => {
    if (!authLoading && !user) {
      navigate(`/login?next=${encodeURIComponent(location.pathname)}`, { replace: true });
    }
  }, [authLoading, user, navigate, location.pathname]);

  if (data?.missing) {
    return <div className="card p-8 text-center text-inkm">Provider not found.</div>;
  }
  if (!data || !user) return <p className="text-sm text-inkm">Loading…</p>;
  if (!service) {
    return (
      <div className="card p-8 text-center text-inkm">
        That service isn't available any more.{' '}
        <Link to={`/services/providers/${slug}`} className="text-brand">Back to profile →</Link>
      </div>
    );
  }

  const rate = parseFloat(service.rate_usd);
  let estimate = null;
  let estimateNote = '';
  if (service.pricing_unit === 'flat') {
    estimate = rate;
  } else if (service.pricing_unit === 'per_hour' && hours) {
    estimate = rate * hours;
    estimateNote = `$${service.rate_usd}/hour × ${hours}h`;
  } else if (service.pricing_unit === 'per_day' && hours) {
    const days = Math.max(1, Math.ceil(hours / 8));
    estimate = rate * days;
    estimateNote = `$${service.rate_usd}/day × ${days} day${days > 1 ? 's' : ''}`;
  }
  // per_km → estimate stays null: "billed by distance".

  const startAt = slot?.start_at ? new Date(slot.start_at) : null;
  const endAt = startAt && hours
    ? new Date(startAt.getTime() + hours * 3600 * 1000)
    : null;

  const submit = async () => {
    if (!startAt || !endAt) return;
    setBusy(true);
    try {
      const booking = await createBooking({
        bookable_type: 'service_provider',
        bookable_id: service.id,
        start_at: startAt.toISOString(),
        end_at: endAt.toISOString(),
        message: notes.trim() || null,
        domain_payload: {
          service_id: service.id,
          buyer_notes: notes.trim(),
          buyer_phone_at_request: user.phone,
          distance_km: service.pricing_unit === 'per_km' && distanceKm
            ? parseFloat(distanceKm) : null,
        },
      });
      navigate(`/services/booking/${booking.id}/success`);
    } catch (err) {
      toast.error(errMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-7">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-inkm">
          <Link to={`/services/providers/${slug}`} className="hover:text-ink">
            {data.provider.name}
          </Link>
        </p>
        <h1 className="heading-accent mt-1 font-display text-2xl text-ink">
          Request: {service.name}
        </h1>
        <div className="mt-2 flex items-center gap-2">
          <PricingUnitChip unit={service.pricing_unit} rate={service.rate_usd} />
        </div>
      </div>

      <section>
        <h2 className="mb-2 text-sm font-medium uppercase tracking-wider text-inkm">
          1 · Pick a start time
        </h2>
        <AvailabilityCalendar
          slug={slug}
          selectedStart={slot?.start_at}
          onSelectSlot={setSlot}
        />
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="card space-y-4 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wider text-inkm">
            2 · Duration & details
          </h2>
          <div>
            <label className="mb-1.5 block text-sm text-inkm">How long do you need?</label>
            <div className="flex flex-wrap gap-2">
              {DUR_CHOICES.map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHours(h)}
                  className={`rounded-md border px-3 py-1.5 text-sm transition ${
                    hours === h
                      ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.15)] text-ink'
                      : 'border-bordr bg-bgs text-inkm hover:text-ink'
                  }`}
                >
                  {h}h
                </button>
              ))}
            </div>
          </div>
          {service.pricing_unit === 'per_km' && (
            <Input
              label="Approximate distance (km)"
              type="number" min="0" step="0.5"
              value={distanceKm}
              onChange={(e) => setDistanceKm(e.target.value)}
              placeholder="e.g. 12"
            />
          )}
          <Textarea
            label="Notes for the provider (optional)"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Where, what, anything they should bring…"
          />
        </div>

        <div className="card space-y-4 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wider text-inkm">
            3 · Review & send
          </h2>
          <div className="space-y-1.5 text-sm">
            <p className="flex items-center gap-2 text-ink">
              <CalendarClock size={15} className="text-[rgb(var(--section-accent))]" />
              {startAt
                ? `${startAt.toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })} → ${endAt.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`
                : 'Pick a slot above'}
            </p>
            {estimate != null ? (
              <p className="text-ink">
                Estimated: <span className="font-semibold">${estimate.toFixed(2)}</span>
                {estimateNote && <span className="ml-1 text-xs text-inkm">({estimateNote})</span>}
              </p>
            ) : (
              <p className="text-inkm">
                Billed by distance — agree the final amount with your provider.
              </p>
            )}
          </div>
          <div className="flex items-start gap-2 rounded-lg border border-bordr bg-bgs2 p-3 text-xs text-inkm">
            <Info size={14} className="mt-0.5 shrink-0 text-[rgb(var(--section-highlight))]" />
            This sends a request — nothing is booked until {data.provider.name} confirms.
            Rates are indicative; payment happens directly between you, off-platform.
          </div>
          <Button
            className="w-full"
            loading={busy}
            disabled={!startAt || !hours}
            onClick={submit}
          >
            Send booking request
          </Button>
        </div>
      </section>
    </div>
  );
}
