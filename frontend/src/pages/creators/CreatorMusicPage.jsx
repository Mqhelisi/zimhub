import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2, ArrowLeft } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { TrackList, accentRgb } from '../../modules/creator_platform/components/index.jsx';

export default function CreatorMusicPage() {
  const { slug } = useParams();
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    creatorApi.getCreator(slug).then((r) => setCreator(r.creator)).catch(() => {}).finally(() => setLoading(false));
  }, [slug]);
  if (loading) return <div className="container-page flex items-center gap-2 py-20 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>;
  if (!creator) return <div className="container-page py-20 text-inkm">Creator not found.</div>;
  return (
    <main className="container-page py-10" style={{ '--section-accent': accentRgb(creator.accent_color) }}>
      <Link to={`/creators/${slug}`} className="inline-flex items-center gap-1 text-sm text-inkm hover:text-ink"><ArrowLeft size={14} /> {creator.display_name}</Link>
      <h1 className="accent-rule mt-3 font-display text-4xl text-ink">Music</h1>
      <div className="mt-6"><TrackList tracks={creator.tracks || []} creator={creator} /></div>
    </main>
  );
}
