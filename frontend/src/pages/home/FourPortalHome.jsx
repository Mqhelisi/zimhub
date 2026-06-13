import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShoppingBag, Ticket, Wrench, Palette, Sparkles } from 'lucide-react';
import { Modal } from '../../components/ui/Modal.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';

const SECTIONS = [
  {
    key: 'salesman',
    title: 'Shop',
    accent: 'shop',
    accentVar: '--shop-accent',
    icon: ShoppingBag,
    description: 'Buy from local Bulawayo sellers — clothing, electronics, pantry, home.',
    stage: 'Stage 2',
    href: '/shop',
    live: true,
  },
  {
    key: 'promoter',
    title: 'Events',
    accent: 'events',
    accentVar: '--events-accent',
    icon: Ticket,
    description: 'Find live music, festivals, sundowners, and cultural nights in Bulawayo.',
    stage: 'Stage 3',
    href: '/events',
    live: true,
  },
  {
    key: 'provider',
    title: 'Services',
    accent: 'services',
    accentVar: '--services-accent',
    icon: Wrench,
    description: 'Book trusted local trades — plumbers, electricians, hairdressers, mechanics.',
    stage: 'Stage 4',
    href: '/services',
    live: true,
  },
  {
    key: 'creator',
    title: 'Creators',
    accent: 'creators',
    accentVar: '--creators-accent',
    icon: Palette,
    description: 'Discover Bulawayo musicians, photographers, artists, and storytellers.',
    stage: 'Stage 5',
    href: '/creators',
    live: true,
  },
];

function PortalTile({ section, onClick }) {
  const Icon = section.icon;
  const isLive = section.live;
  const sharedStyle = { '--section': `var(${section.accentVar})` };
  const sharedClass = `group relative overflow-hidden rounded-2xl border border-bordr bg-bgs p-7 text-left
                 transition hover:border-[rgb(var(--section)/0.6)] hover:bg-bgs2`;
  const inner = (
    <>
      {/* gradient overlay */}
      <div
        className="absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100 pointer-events-none"
        style={{
          background: `radial-gradient(400px 200px at 20% 0%, rgb(var(--section) / 0.18), transparent 70%)`,
        }}
      />
      {/* corner accent */}
      <div
        className="absolute -right-12 -top-12 h-32 w-32 rounded-full blur-3xl opacity-20 pointer-events-none transition-opacity group-hover:opacity-40"
        style={{ background: 'rgb(var(--section))' }}
      />
      <div className="relative flex items-start justify-between">
        <span
          className="inline-flex h-11 w-11 items-center justify-center rounded-xl border"
          style={{
            borderColor: 'rgb(var(--section) / 0.4)',
            background: 'rgb(var(--section) / 0.12)',
            color: 'rgb(var(--section))',
          }}
        >
          <Icon size={22} />
        </span>
        <span
          className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider"
          style={{
            borderColor: 'rgb(var(--section) / 0.4)',
            background: 'rgb(var(--section) / 0.1)',
            color: 'rgb(var(--section))',
          }}
        >
          {isLive ? `${section.stage} • Now live` : `${section.stage} • Coming soon`}
        </span>
      </div>
      <h3 className="relative mt-6 font-display text-3xl text-ink">{section.title}</h3>
      <p className="relative mt-2 text-sm text-inkm">{section.description}</p>
      <div className="relative mt-6 flex items-center gap-1.5 text-xs text-inkm group-hover:text-ink transition">
        {isLive ? 'Open Shop' : 'Tap for details'} <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" />
      </div>
    </>
  );
  if (isLive && section.href) {
    return (
      <Link to={section.href} style={sharedStyle} className={sharedClass + ' block'}>
        {inner}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} style={sharedStyle} className={sharedClass}>
      {inner}
    </button>
  );
}

export default function FourPortalHome() {
  const { user } = useAuth();
  const [active, setActive] = useState(null);

  return (
    <div>
      {/* Hero */}
      <section className="relative pb-12 pt-4 sm:pt-8">
        <div className="absolute -left-20 top-10 hidden md:block h-72 w-72 rounded-full bg-brand/10 blur-3xl pointer-events-none" />
        <div className="absolute -right-10 top-32 hidden md:block h-56 w-56 rounded-full bg-creators/10 blur-3xl pointer-events-none" />
        <div className="relative max-w-3xl">
          <span className="pill border-brand/40 text-brand">
            <Sparkles size={11} /> One Bulawayo, one marketplace
          </span>
          <h1 className="mt-4 font-display text-5xl sm:text-6xl md:text-7xl text-ink leading-[1.05]">
            Bulawayo's <em className="font-medium not-italic text-brand">marketplace</em>,<br className="hidden sm:inline" />
            <span className="text-inkm/90"> in one place.</span>
          </h1>
          <p className="mt-5 max-w-xl text-base text-inkm sm:text-lg">
            Shop, book services, find events, and follow local creators —
            all under one trusted roof. Built in Bulawayo, for Bulawayo.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            {user ? (
              <Link to="/notifications" className="btn-primary">
                Open your account <ArrowRight size={16} />
              </Link>
            ) : (
              <Link to="/signup" className="btn-primary">
                Sign up to buy <ArrowRight size={16} />
              </Link>
            )}
            <Link to="/sell" className="btn-secondary">Sell on ZimHub</Link>
          </div>
        </div>
      </section>

      {/* Four tiles */}
      <section className="mt-4">
        <div className="mb-5 flex items-baseline justify-between">
          <h2 className="font-display text-2xl text-ink">The four portals</h2>
          <Link to="/sell" className="text-sm text-inkm hover:text-brand">Sell on ZimHub →</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {SECTIONS.map((s) => (
            <PortalTile key={s.key} section={s} onClick={() => setActive(s)} />
          ))}
        </div>
      </section>

      {/* Coming soon modal */}
      <Modal
        open={Boolean(active)}
        onClose={() => setActive(null)}
        title={active ? `${active.title} — coming soon` : ''}
        footer={
          active && (
            <>
              <Button variant="ghost" onClick={() => setActive(null)}>Close</Button>
              <Link
                to={`/sell/${active.key}`}
                onClick={() => setActive(null)}
                className="btn-primary"
              >
                Apply to sell here <ArrowRight size={16} />
              </Link>
            </>
          )
        }
      >
        {active && (
          <div>
            <p className="text-sm text-inkm">
              <span className="text-ink font-semibold">{active.title}</span> is launching in {active.stage}. {active.description}
            </p>
            <p className="mt-3 text-sm text-inkm">
              Want to sell here? Apply now — we'll review your application and reach out within 48 hours.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
