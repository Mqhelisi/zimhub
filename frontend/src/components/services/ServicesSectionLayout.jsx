// Services section chrome + small shared components.
// Wraps /services/*, /my/bookings/* (Stage 4 §6.2 theme scope); the provider
// admin nests its own sidebar inside this wrapper.
import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Wrench, ChevronLeft, CalendarClock } from 'lucide-react';
import '../../styles/theme-services.css';

export default function ServicesSectionLayout() {
  const { pathname } = useLocation();
  const onLanding = pathname === '/services' || pathname === '/services/';
  return (
    <div data-section="services" className="services-bg min-h-screen">
      <div className="bg-bgs2/60 border-b border-bordr/60">
        <div className="container-page py-2 flex items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-3 min-w-0">
            {!onLanding && (
              <Link to="/" className="text-inkm hover:text-ink inline-flex items-center gap-1">
                <ChevronLeft size={14} /> Hub
              </Link>
            )}
            <Link to="/services" className="text-ink inline-flex items-center gap-2 font-medium min-w-0">
              <Wrench size={16} className="text-brand shrink-0" />
              <span className="truncate">ZimHub Services</span>
            </Link>
          </div>
          <Link
            to="/my/bookings"
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-inkm hover:text-ink hover:bg-bgs2"
          >
            <CalendarClock size={16} /> My bookings
          </Link>
        </div>
      </div>
      <div className="container-page py-8 sm:py-10">
        <Outlet />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
export function TradeBadge({ trade, className = '' }) {
  if (!trade) return null;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border border-[rgb(var(--section-accent)/0.4)] bg-[rgb(var(--section-accent)/0.1)] px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wider text-[rgb(var(--section-accent))] ${className}`}>
      {trade}
    </span>
  );
}

// ---------------------------------------------------------------------------
export function PricingUnitChip({ unit, rate, className = '' }) {
  const text = {
    flat: `$${rate} flat`,
    per_hour: `$${rate}/hour`,
    per_day: `$${rate}/day`,
    per_km: `$${rate}/km — by distance`,
  }[unit] || `$${rate}`;
  return (
    <span className={`inline-flex items-center rounded-md border border-bordr bg-bgs2 px-2 py-0.5 text-xs font-medium text-ink ${className}`}>
      {text}
    </span>
  );
}

// ---------------------------------------------------------------------------
export function ProviderCard({ provider }) {
  return (
    <Link
      to={provider.slug ? `/services/providers/${provider.slug}` : '#'}
      className="card card-hover block p-5"
    >
      <div className="flex items-start gap-3.5">
        <div className="h-14 w-14 shrink-0 overflow-hidden rounded-xl border border-bordr bg-bgs2">
          {provider.photo_url ? (
            <img src={provider.photo_url} alt={provider.name}
                 className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-lg font-bold text-[rgb(var(--section-accent))]">
              {provider.name?.[0] || '?'}
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate font-display text-lg text-ink">{provider.name}</h3>
            <TradeBadge trade={provider.trade} />
          </div>
          <p className="mt-0.5 line-clamp-2 text-sm text-inkm">{provider.bio}</p>
        </div>
      </div>
      <div className="mt-3.5 flex flex-wrap items-center gap-2 text-xs text-inkm">
        <span>{provider.service_count} service{provider.service_count === 1 ? '' : 's'}</span>
        {provider.completed_30d > 0 && (
          <span className="trust-badge rounded-full px-2 py-0.5 font-medium">
            {provider.completed_30d} completed · 30 days
          </span>
        )}
        {(provider.suburbs_served || []).length > 0 && (
          <span className="truncate">· {provider.suburbs_served.join(', ')}</span>
        )}
      </div>
    </Link>
  );
}

// ---------------------------------------------------------------------------
export function ServiceCard({ service, slug }) {
  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="font-medium text-ink">{service.name}</h4>
          <p className="mt-1 line-clamp-2 text-sm text-inkm">{service.description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <PricingUnitChip unit={service.pricing_unit} rate={service.rate_usd} />
            {service.default_duration_minutes && (
              <span className="text-xs text-inkm">
                ~{service.default_duration_minutes} min
              </span>
            )}
          </div>
        </div>
        {slug && (
          <Link to={`/services/providers/${slug}/book/${service.id}`} className="btn-primary">
            Request booking →
          </Link>
        )}
      </div>
    </div>
  );
}
