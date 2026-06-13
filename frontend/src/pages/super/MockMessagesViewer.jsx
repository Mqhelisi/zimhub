import React, { useEffect, useState } from 'react';
import { Mail, MessageCircle, Smartphone } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Modal } from '../../components/ui/Modal.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Badge } from '../../components/ui/Badge.jsx';
import { systemApi } from '../../api/system.js';
import { formatDateTime } from '../../utils/time.js';

const CHANNELS = [
  { key: '', label: 'All' },
  { key: 'email', label: 'Email', icon: Mail },
  { key: 'whatsapp', label: 'WhatsApp', icon: MessageCircle },
  { key: 'sms', label: 'SMS', icon: Smartphone },
];

const ICONS = { email: Mail, whatsapp: MessageCircle, sms: Smartphone };

export default function MockMessagesViewer() {
  const [channel, setChannel] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ messages: [], total: 0, page: 1, page_size: 50 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    setLoading(true);
    systemApi.listMockMessages({ channel: channel || undefined, page })
      .then((d) => { setData(d); setError(''); })
      .catch((e) => setError(e?.response?.data?.message || 'Could not load.'))
      .finally(() => setLoading(false));
  }, [channel, page]);

  return (
    <div>
      <h1 className="font-display text-4xl text-ink">Mock messages</h1>
      <p className="mt-1 text-sm text-inkm">
        Everything dispatched via the mock transport (email, WhatsApp, SMS). No real recipients are contacted.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {CHANNELS.map((c) => {
          const active = channel === c.key;
          return (
            <button
              key={c.key || 'all'}
              onClick={() => { setChannel(c.key); setPage(1); }}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                active ? 'border-brand bg-brand text-[rgb(20_15_8)]' : 'border-bordr bg-bgs text-inkm hover:text-ink'
              }`}
            >
              {c.icon && <c.icon size={12} />}
              {c.label}
            </button>
          );
        })}
      </div>

      {error && <div className="mt-4 text-danger">{error}</div>}

      <div className="mt-6">
        {loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : data.messages.length === 0 ? (
          <Card className="text-center text-inkm">No mock messages yet.</Card>
        ) : (
          <div className="card divide-y divide-bordr !p-0">
            {data.messages.map((m) => {
              const Icon = ICONS[m.channel] || Mail;
              return (
                <button
                  key={m.id}
                  onClick={() => setSelected(m)}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-bgs2"
                >
                  <Icon size={18} className="mt-0.5 text-inkm shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={m.channel === 'email' ? 'brand' : m.channel === 'whatsapp' ? 'success' : 'default'}>
                        {m.channel}
                      </Badge>
                      <span className="text-sm text-ink">{m.recipient}</span>
                    </div>
                    <div className="mt-0.5 truncate text-xs text-inkm">
                      {m.subject || m.body.slice(0, 80)}
                    </div>
                  </div>
                  <div className="shrink-0 text-[10px] uppercase tracking-wider text-inkm/70">
                    {formatDateTime(m.created_at)}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {Math.ceil(data.total / data.page_size) > 1 && (
        <div className="mt-4 flex items-center justify-between text-xs text-inkm">
          <span>Page {data.page} · {data.total} total</span>
          <div className="flex gap-2">
            <button disabled={data.page <= 1} onClick={() => setPage((p) => p - 1)} className="btn-secondary !py-1.5 disabled:opacity-40">← Prev</button>
            <button disabled={data.page * data.page_size >= data.total} onClick={() => setPage((p) => p + 1)} className="btn-secondary !py-1.5 disabled:opacity-40">Next →</button>
          </div>
        </div>
      )}

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="Mock message"
        size="lg"
        footer={<Button onClick={() => setSelected(null)}>Close</Button>}
      >
        {selected && (
          <div className="space-y-4 text-sm">
            <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-inkm">Channel</dt>
                <dd className="mt-0.5 text-ink">{selected.channel}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-inkm">Recipient</dt>
                <dd className="mt-0.5 text-ink">{selected.recipient}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-[10px] uppercase tracking-wider text-inkm">Sent at</dt>
                <dd className="mt-0.5 text-ink">{formatDateTime(selected.created_at)}</dd>
              </div>
              {selected.subject && (
                <div className="sm:col-span-2">
                  <dt className="text-[10px] uppercase tracking-wider text-inkm">Subject</dt>
                  <dd className="mt-0.5 text-ink">{selected.subject}</dd>
                </div>
              )}
            </dl>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-inkm">Body</div>
              <pre className="mt-1 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-bordr bg-bgs2 px-3 py-2 text-xs text-ink">{selected.body}</pre>
            </div>
            {selected.payload && Object.keys(selected.payload).length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-wider text-inkm">Payload</div>
                <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border border-bordr bg-bgs2 px-3 py-2 text-xs text-ink">
{JSON.stringify(selected.payload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
