import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShoppingBag, Ticket, Wrench, Palette } from 'lucide-react';

const TYPES = [
  {
    key: 'salesman',
    title: 'Salesman',
    icon: ShoppingBag,
    accent: '--shop-accent',
    blurb: 'Sell products from a shop — anything from clothing to electronics to pantry.',
    bullets: ['Phone shop in the CBD', 'Independent fashion label', 'Grocery delivery service'],
  },
  {
    key: 'promoter',
    title: 'Promoter',
    icon: Ticket,
    accent: '--events-accent',
    blurb: 'Run events with QR-coded tickets, attendee lists, and a public event page.',
    bullets: ['Live music nights', 'Festivals & fairs', 'Sundowner sessions'],
  },
  {
    key: 'provider',
    title: 'Service Provider',
    icon: Wrench,
    accent: '--services-accent',
    blurb: 'Take bookings for any trade — plumbing, electrical, hair, mechanics, tutoring.',
    bullets: ['Plumber serving Hillside', 'Mobile car-wash', 'Hairdresser making house calls'],
  },
  {
    key: 'creator',
    title: 'Creator',
    icon: Palette,
    accent: '--creators-accent',
    blurb: 'A single home for your creative work — music, photography, art, writing.',
    bullets: ['Musician releasing singles', 'Wedding photographer', 'Visual artist with a portfolio'],
  },
];

function ApplyCard({ t }) {
  const Icon = t.icon;
  return (
    <div
      style={{ '--section': `var(${t.accent})` }}
      className="group relative overflow-hidden rounded-2xl border border-bordr bg-bgs p-7 transition hover:border-[rgb(var(--section)/0.6)] hover:bg-bgs2"
    >
      <div
        className="absolute -right-12 -top-12 h-32 w-32 rounded-full blur-3xl opacity-20 pointer-events-none transition-opacity group-hover:opacity-40"
        style={{ background: 'rgb(var(--section))' }}
      />
      <span
        className="relative inline-flex h-11 w-11 items-center justify-center rounded-xl border"
        style={{
          borderColor: 'rgb(var(--section) / 0.4)',
          background: 'rgb(var(--section) / 0.12)',
          color: 'rgb(var(--section))',
        }}
      >
        <Icon size={22} />
      </span>
      <h3 className="relative mt-5 font-display text-2xl text-ink">{t.title}</h3>
      <p className="relative mt-2 text-sm text-inkm">{t.blurb}</p>
      <ul className="relative mt-4 space-y-1">
        {t.bullets.map((b) => (
          <li key={b} className="flex items-start gap-2 text-xs text-inkm">
            <span className="mt-1 inline-block h-1 w-1 shrink-0 rounded-full" style={{ background: 'rgb(var(--section))' }} />
            {b}
          </li>
        ))}
      </ul>
      <Link
        to={`/sell/${t.key}`}
        className="relative mt-5 inline-flex items-center gap-1.5 text-sm font-semibold transition"
        style={{ color: 'rgb(var(--section))' }}
      >
        Apply as {t.title.toLowerCase()} <ArrowRight size={14} />
      </Link>
    </div>
  );
}

export default function SellIndex() {
  return (
    <div>
      <div className="max-w-2xl">
        <h1 className="font-display text-5xl sm:text-6xl text-ink leading-[1.05]">Sell on <em className="not-italic text-brand font-medium">ZimHub</em></h1>
        <p className="mt-4 text-base text-inkm sm:text-lg">
          Apply once. We review every application personally — usually within 48 hours.
        </p>
      </div>
      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {TYPES.map((t) => <ApplyCard key={t.key} t={t} />)}
      </div>
      <p className="mt-10 text-center text-xs text-inkm">
        Already approved? <Link to="/login" className="text-brand">Sign in →</Link>
      </p>
    </div>
  );
}
