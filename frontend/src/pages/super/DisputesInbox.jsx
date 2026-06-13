import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { formatRelative } from '../../utils/time.js';
import { purchaseInterfaceApi } from '../../modules/purchase_interface/api.js';

const TABS = [
  { key: 'open', label: 'Open', icon: AlertTriangle },
  { key: 'resolved', label: 'Resolved', icon: ShieldCheck },
];

export default function DisputesInbox() {
  const [tab, setTab] = useState('open');
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setRows(null); setError('');
    purchaseInterfaceApi.admin.listDisputes({ status: tab })
      .then((d) => alive && setRows(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load disputes.'));
    return () => { alive = false; };
  }, [tab]);

  return (
    <div>
      <h1 className="font-display text-4xl text-ink">Dispute desk</h1>
      <p className="mt-1 text-sm text-inkm">Open disputes need a ruling. Resolved ones are read-only.</p>

      <div className="mt-5 flex flex-wrap gap-2 border-b border-bordr pb-3">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm transition
              ${tab === t.key ? 'bg-brand text-bg' : 'text-inkm hover:bg-bgs2 hover:text-ink'}`}
          >
            <t.icon size={12} /> {t.label}
          </button>
        ))}
      </div>

      {error && <div className="mt-6 text-danger">{error}</div>}
      {!rows && !error && <div className="mt-10 flex justify-center"><Spinner size={22} /></div>}
      {rows && rows.length === 0 && (
        <Card className="mt-6 text-center text-inkm">
          {tab === 'open' ? 'No open disputes — all clear.' : 'No resolved disputes yet.'}
        </Card>
      )}
      {rows && rows.length > 0 && (
        <ul className="mt-5 space-y-3">
          {rows.map((d) => {
            const p = d.purchase || {};
            const item = (p.domain_payload?.items || [])[0];
            return (
              <li key={d.id}>
                <Link
                  to={`/super/disputes/${d.id}`}
                  className="card flex items-start gap-3 !p-4 hover:border-brand/60"
                >
                  <div className={`mt-0.5 ${d.status === 'open' ? 'text-danger' : 'text-inkm'}`}>
                    {d.status === 'open'
                      ? <AlertTriangle size={18} />
                      : <ShieldCheck size={18} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="font-medium text-ink">
                        {item?.name || 'Purchase'}{p.quantity > 1 ? ` (×${p.quantity})` : ''}
                      </span>
                      <span className="text-xs text-inkm">
                        raised {formatRelative(d.created_at)} by {d.raised_by_role}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-inkm line-clamp-2">{d.reason}</p>
                    {d.status === 'resolved' && (
                      <div className="mt-1 text-xs text-inkm">
                        Resolved as <span className="text-ink">{d.resolution}</span>
                        {d.resolved_at ? ` • ${formatRelative(d.resolved_at)}` : ''}
                      </div>
                    )}
                  </div>
                  <div className="text-right text-sm whitespace-nowrap">
                    <div className="font-display text-lg text-ink">${p.total_usd ?? '—'}</div>
                    <div className="text-xs text-inkm">{p.status}</div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
