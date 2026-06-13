import React, { useState, useEffect, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { mediaUrl } from '../../../utils/media.js';

/**
 * CSS-columns masonry gallery + a self-contained lightbox. No external library —
 * keeps the dependency surface to just `howler` per Stage 5 §3.
 *
 * `collections` is an array of { id, title, description, items: [{id,title,image_url,...}] }.
 */
export default function GalleryGrid({ collections = [] }) {
  const flat = collections.flatMap((c) =>
    (c.items || []).map((it) => ({ ...it, _collection: c.title })),
  );
  const [lightboxIdx, setLightboxIdx] = useState(-1);

  const close = useCallback(() => setLightboxIdx(-1), []);
  const go = useCallback(
    (delta) => setLightboxIdx((i) => {
      const n = i + delta;
      if (n < 0) return flat.length - 1;
      if (n >= flat.length) return 0;
      return n;
    }),
    [flat.length],
  );

  useEffect(() => {
    if (lightboxIdx < 0) return;
    const onKey = (e) => {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowLeft') go(-1);
      else if (e.key === 'ArrowRight') go(1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightboxIdx, close, go]);

  if (!flat.length) {
    return <p className="text-sm text-inkm">No gallery items yet.</p>;
  }

  return (
    <div className="space-y-8">
      {collections.map((c) => (
        <div key={c.id}>
          <h3 className="font-display text-2xl text-ink">{c.title}</h3>
          {c.description && <p className="mt-1 text-sm text-inkm">{c.description}</p>}
          <div className="gallery-masonry mt-4">
            {(c.items || []).map((it) => {
              const gi = flat.findIndex((f) => f.id === it.id);
              return (
                <button
                  key={it.id}
                  onClick={() => setLightboxIdx(gi)}
                  className="block w-full overflow-hidden rounded-lg border border-bordr bg-bgs2 transition hover:border-[rgb(var(--section-accent)/0.6)]"
                >
                  <img
                    src={mediaUrl(it.image_url)}
                    alt={it.title}
                    loading="lazy"
                    className="w-full object-cover"
                  />
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {lightboxIdx >= 0 && flat[lightboxIdx] && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4"
          onClick={close}
        >
          <button className="absolute right-4 top-4 rounded-full p-2 text-white/80 hover:text-white" onClick={close}>
            <X size={26} />
          </button>
          <button
            className="absolute left-2 rounded-full p-3 text-white/70 hover:text-white sm:left-6"
            onClick={(e) => { e.stopPropagation(); go(-1); }}
          >
            <ChevronLeft size={30} />
          </button>
          <figure className="max-h-[88vh] max-w-[92vw]" onClick={(e) => e.stopPropagation()}>
            <img
              src={mediaUrl(flat[lightboxIdx].image_url)}
              alt={flat[lightboxIdx].title}
              className="max-h-[80vh] w-auto rounded-lg object-contain"
            />
            <figcaption className="mt-3 text-center text-sm text-white/80">
              {flat[lightboxIdx].title}
              {flat[lightboxIdx].category && (
                <span className="text-white/50"> · {flat[lightboxIdx].category}</span>
              )}
            </figcaption>
          </figure>
          <button
            className="absolute right-2 rounded-full p-3 text-white/70 hover:text-white sm:right-6"
            onClick={(e) => { e.stopPropagation(); go(1); }}
          >
            <ChevronRight size={30} />
          </button>
        </div>
      )}
    </div>
  );
}
