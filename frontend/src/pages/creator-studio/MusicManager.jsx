import React, { useEffect, useState } from 'react';
import { Loader2, Upload, Trash2, Eye, EyeOff, Plus, Music2 } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { useToast } from '../../components/ui/Toast.jsx';
import { mediaUrl } from '../../utils/media.js';

export default function MusicManager() {
  const toast = useToast();
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', genre: '', featuring: '', album: '', audio_url: '', cover_art_url: '' });
  const [uploading, setUploading] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => creatorApi.listTracks().then((r) => setTracks(r.tracks)).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const upAudio = async (file) => {
    if (!file) return;
    setUploading('audio');
    try { const { url } = await creatorApi.uploadAudio(file); setForm((f) => ({ ...f, audio_url: url })); toast.success('Audio uploaded.'); }
    catch (e) { toast.error(e.message || 'Audio upload failed'); }
    finally { setUploading(''); }
  };
  const upCover = async (file) => {
    if (!file) return;
    setUploading('cover');
    try { const { url } = await creatorApi.uploadImage(file); setForm((f) => ({ ...f, cover_art_url: url })); }
    catch (e) { toast.error(e.message || 'Cover upload failed'); }
    finally { setUploading(''); }
  };

  const create = async () => {
    if (!form.title || !form.audio_url) { toast.error('Title and an audio file are required.'); return; }
    setSaving(true);
    try {
      await creatorApi.createTrack(form);
      toast.success('Track added.');
      setForm({ title: '', genre: '', featuring: '', album: '', audio_url: '', cover_art_url: '' });
      setShowForm(false);
      load();
    } catch (e) { toast.error(e.message || 'Could not add track'); }
    finally { setSaving(false); }
  };

  const toggleVis = async (t) => {
    try { await creatorApi.editTrack(t.id, { is_visible: !t.is_visible }); load(); }
    catch (e) { toast.error(e.message); }
  };
  const del = async (t) => {
    if (!window.confirm(`Delete "${t.title}"?`)) return;
    try { await creatorApi.deleteTrack(t.id); toast.success('Deleted.'); load(); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="accent-rule font-display text-4xl text-ink">Music</h1>
        <button className="btn-accent" onClick={() => setShowForm((s) => !s)}><Plus size={15} /> Add track</button>
      </div>

      {showForm && (
        <div className="mt-5 rounded-xl border border-bordr bg-bgs p-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <input className="input-base" placeholder="Title *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <input className="input-base" placeholder="Genre" value={form.genre} onChange={(e) => setForm({ ...form, genre: e.target.value })} />
            <input className="input-base" placeholder="Featuring" value={form.featuring} onChange={(e) => setForm({ ...form, featuring: e.target.value })} />
            <input className="input-base" placeholder="Album / EP" value={form.album} onChange={(e) => setForm({ ...form, album: e.target.value })} />
          </div>
          <div className="mt-3 flex flex-wrap gap-3">
            <label className="btn-secondary cursor-pointer">
              {uploading === 'audio' ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} {form.audio_url ? 'Audio ✓' : 'Upload audio (MP3) *'}
              <input type="file" accept="audio/*" hidden onChange={(e) => upAudio(e.target.files?.[0])} />
            </label>
            <label className="btn-secondary cursor-pointer">
              {uploading === 'cover' ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} {form.cover_art_url ? 'Cover ✓' : 'Upload cover art'}
              <input type="file" accept="image/*" hidden onChange={(e) => upCover(e.target.files?.[0])} />
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button className="btn-accent" onClick={create} disabled={saving}>{saving ? <Loader2 size={14} className="animate-spin" /> : 'Save track'}</button>
            <button className="btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="mt-6">
        {loading ? (
          <div className="flex items-center gap-2 py-10 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>
        ) : tracks.length === 0 ? (
          <p className="py-10 text-inkm">No tracks yet — add your first above.</p>
        ) : (
          <div className="divide-y divide-bordr/60 overflow-hidden rounded-xl border border-bordr">
            {tracks.map((t) => (
              <div key={t.id} className="flex items-center gap-3 px-4 py-3">
                <div className="flex h-10 w-10 items-center justify-center rounded bg-bgs2 text-inkm">
                  {t.cover_art_url ? <img src={mediaUrl(t.cover_art_url)} alt="" className="h-full w-full rounded object-cover" /> : <Music2 size={16} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-ink">{t.title}</div>
                  <div className="truncate text-xs text-inkm">{[t.genre, t.featuring && `feat. ${t.featuring}`].filter(Boolean).join(' · ')} · {t.play_count} plays</div>
                </div>
                {!t.is_visible && <span className="rounded-full bg-bgs2 px-2 py-0.5 text-[10px] text-inkm">Hidden</span>}
                <button onClick={() => toggleVis(t)} className="rounded p-2 text-inkm hover:text-ink" title={t.is_visible ? 'Hide' : 'Show'}>
                  {t.is_visible ? <Eye size={16} /> : <EyeOff size={16} />}
                </button>
                <button onClick={() => del(t)} className="rounded p-2 text-inkm hover:text-danger" title="Delete"><Trash2 size={16} /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
