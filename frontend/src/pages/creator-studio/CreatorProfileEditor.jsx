import React, { useEffect, useState } from 'react';
import { Loader2, Upload, Save } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { useToast } from '../../components/ui/Toast.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { mediaUrl } from '../../utils/media.js';
import { accentRgb } from '../../modules/creator_platform/components/index.jsx';

const TYPES = [
  { key: 'musician', label: 'Musician' },
  { key: 'photographer', label: 'Photographer' },
  { key: 'visual_artist', label: 'Visual Artist' },
];
const SOCIAL = ['instagram', 'facebook', 'whatsapp', 'tiktok'];
const EXTERNAL = ['spotify', 'soundcloud', 'youtube', 'behance'];

export default function CreatorProfileEditor() {
  const toast = useToast();
  const { refresh } = useAuth();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState('');

  useEffect(() => {
    creatorApi.getProfile().then((r) => setP(r.profile)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center gap-2 py-16 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>;
  if (!p) return <p className="text-inkm">Could not load your profile.</p>;

  const set = (k, v) => setP((prev) => ({ ...prev, [k]: v }));
  const setLink = (group, k, v) => setP((prev) => ({ ...prev, [group]: { ...(prev[group] || {}), [k]: v } }));

  const toggleType = (k) => {
    const types = p.creator_types || [];
    set('creator_types', types.includes(k) ? types.filter((t) => t !== k) : [...types, k]);
  };

  const uploadImage = async (field, file) => {
    if (!file) return;
    setUploading(field);
    try {
      const { url } = await creatorApi.uploadImage(file);
      set(field, url);
    } catch (e) { toast.error(e.message || 'Upload failed'); }
    finally { setUploading(''); }
  };

  const save = async () => {
    setSaving(true);
    try {
      await creatorApi.updateProfile({
        display_name: p.display_name, bio: p.bio, accent_color: p.accent_color,
        hero_image_url: p.hero_image_url, photo_url: p.photo_url,
        discipline_tags: p.discipline_tags, creator_types: p.creator_types,
        social_links: p.social_links, external_links: p.external_links,
        contact_email: p.contact_email, contact_email_public: p.contact_email_public,
      });
      toast.success('Profile saved.');
      refresh();
    } catch (e) { toast.error(e.message || 'Could not save'); }
    finally { setSaving(false); }
  };

  return (
    <div style={{ '--section-accent': accentRgb(p.accent_color) }}>
      <h1 className="accent-rule font-display text-4xl text-ink">Profile & page</h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <div>
            <label className="label">Display name</label>
            <input className="input-base" value={p.display_name || ''} onChange={(e) => set('display_name', e.target.value)} />
          </div>
          <div>
            <label className="label">Page address (read-only)</label>
            <input className="input-base opacity-60" value={`/creators/${p.creator_slug}`} readOnly />
          </div>
          <div>
            <label className="label">Bio</label>
            <textarea className="input-base min-h-[100px]" maxLength={1000} value={p.bio || ''} onChange={(e) => set('bio', e.target.value)} />
          </div>
          <div>
            <label className="label">Discipline tags (comma-separated)</label>
            <input className="input-base" value={(p.discipline_tags || []).join(', ')} onChange={(e) => set('discipline_tags', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))} />
          </div>
          <div>
            <label className="label">Creator types</label>
            <div className="flex flex-wrap gap-2">
              {TYPES.map((t) => {
                const on = (p.creator_types || []).includes(t.key);
                return (
                  <button key={t.key} type="button" onClick={() => toggleType(t.key)}
                    className={`rounded-full border px-3 py-1.5 text-sm ${on ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.14)] text-[rgb(var(--section-accent))]' : 'border-bordr text-inkm'}`}>
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">Accent colour</label>
            <div className="flex items-center gap-3">
              <input type="color" value={p.accent_color || '#7c3aed'} onChange={(e) => set('accent_color', e.target.value)} className="h-10 w-14 cursor-pointer rounded border border-bordr bg-bgs2" />
              <input className="input-base" value={p.accent_color || ''} onChange={(e) => set('accent_color', e.target.value)} placeholder="#7c3aed" />
            </div>
          </div>
          <div>
            <label className="label">Hero image</label>
            <div className="flex items-center gap-3">
              {p.hero_image_url && <img src={mediaUrl(p.hero_image_url)} alt="" className="h-14 w-24 rounded object-cover" />}
              <label className="btn-secondary cursor-pointer">
                {uploading === 'hero_image_url' ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Upload
                <input type="file" accept="image/*" hidden onChange={(e) => uploadImage('hero_image_url', e.target.files?.[0])} />
              </label>
            </div>
          </div>
          <div>
            <label className="label">Profile photo</label>
            <div className="flex items-center gap-3">
              {p.photo_url && <img src={mediaUrl(p.photo_url)} alt="" className="h-14 w-14 rounded-full object-cover" />}
              <label className="btn-secondary cursor-pointer">
                {uploading === 'photo_url' ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Upload
                <input type="file" accept="image/*" hidden onChange={(e) => uploadImage('photo_url', e.target.files?.[0])} />
              </label>
            </div>
          </div>
          <div>
            <label className="label">Social links</label>
            <div className="space-y-2">
              {SOCIAL.map((k) => (
                <input key={k} className="input-base" placeholder={k === 'whatsapp' ? 'WhatsApp number e.g. +263…' : `${k} URL`}
                  value={(p.social_links || {})[k] || ''} onChange={(e) => setLink('social_links', k, e.target.value)} />
              ))}
            </div>
          </div>
          <div>
            <label className="label">External platform links</label>
            <div className="space-y-2">
              {EXTERNAL.map((k) => (
                <input key={k} className="input-base" placeholder={`${k} URL`}
                  value={(p.external_links || {})[k] || ''} onChange={(e) => setLink('external_links', k, e.target.value)} />
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <button className="btn-accent" onClick={save} disabled={saving}>
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save changes
        </button>
      </div>
    </div>
  );
}
