// /services/providers/:slug — public provider profile: identity, services,
// embedded availability calendar (busy slots opaque), suburbs served.
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MapPin } from 'lucide-react';
import { providerBySlug } from '../../components/services/api.js';
import {
  TradeBadge, ServiceCard,
} from '../../components/services/ServicesSectionLayout.jsx';
import AvailabilityCalendar from '../../components/services/AvailabilityCalendar.jsx';

export default function ProviderProfilePage() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setData(null);
    providerBySlug(slug).then(setData).catch(() => setMissing(true));
  }, [slug]);

  if (missing) {
    return (
      <div className="card p-8 text-center text-inkm">
        Provider not found. <Link to="/services/providers" className="text-brand">Browse providers →</Link>
      </div>
    );
  }
  if (!data) return <p className="text-sm text-inkm">Loading…</p>;

  const { provider, services } = data;
  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start gap-5">
        <div className="h-24 w-24 shrink-0 overflow-hidden rounded-2xl border border-bordr bg-bgs2">
          {provider.photo_url ? (
            <img src={provider.photo_url} alt={provider.name} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-3xl font-bold text-[rgb(var(--section-accent))]">
              {provider.name?.[0]}
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-display text-2xl text-ink">{provider.name}</h1>
            <TradeBadge trade={provider.trade} />
            {provider.completed_30d > 0 && (
              <span className="trust-badge rounded-full px-2.5 py-0.5 text-xs font-medium">
                {provider.completed_30d} completed in the last 30 days
              </span>
            )}
          </div>
          {provider.bio && <p className="mt-2 max-w-2xl text-inkm">{provider.bio}</p>}
          {(provider.suburbs_served || []).length > 0 && (
            <p className="mt-2 flex items-center gap-1.5 text-sm text-inkm">
              <MapPin size={14} className="text-[rgb(var(--section-accent))]" />
              Serves: {provider.suburbs_served.join(', ')}
            </p>
          )}
        </div>
      </header>

      <div className="services-divider" aria-hidden="true" />

      <section>
        <h2 className="mb-3 font-display text-lg text-ink">Services</h2>
        {services.length === 0 && (
          <div className="card p-6 text-sm text-inkm">No active services right now.</div>
        )}
        <div className="grid gap-3 lg:grid-cols-2">
          {services.map((s) => <ServiceCard key={s.id} service={s} slug={slug} />)}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-display text-lg text-ink">Availability</h2>
        <p className="mb-3 text-sm text-inkm">
          Open slots over the next few weeks. Pick a service above to request a time.
        </p>
        <AvailabilityCalendar slug={slug} />
      </section>
    </div>
  );
}
