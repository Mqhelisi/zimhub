import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Loader2, ImagePlus, Save } from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import {
  promoterProfile, promoterUpdateProfile, promoterUploadImage,
} from '../../../modules/ticket_generator/api/index.js';

export default function PromoterProfileEditor() {
  const toast = useToast();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    promoterProfile().then((r) => setProfile(r.profile)).finally(() => setLoading(false));
  }, []);

  function upd(k, v) { setProfile((p) => ({ ...p, [k]: v })); }

  async function onUpload(file) {
    if (!file) return;
    try {
      toast.info('Uploading…');
      const url = await promoterUploadImage(file);
      upd('photo_url', url);
      toast.success('Photo updated');
    } catch (e) {
      toast.error(e.message || 'Upload failed');
    }
  }

  async function onSave() {
    setSaving(true);
    try {
      const r = await promoterUpdateProfile({
        organisation_name: profile.organisation_name,
        bio: profile.bio, photo_url: profile.photo_url,
      });
      setProfile(r.profile);
      toast.success('Saved.');
    } catch (e) {
      toast.error(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  if (loading || !profile) {
    return (
      <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
        <Loader2 className="animate-spin" size={16} /> Loading…
      </div>
    );
  }

  return (
    <main className="container-page py-8 max-w-2xl space-y-5">
      <Link to="/promoter" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> Dashboard
      </Link>
      <h1 className="font-display text-3xl text-ink heading-accent">Promoter profile</h1>
      <div className="card p-5 space-y-4">
        <div>
          <label className="label">Photo</label>
          <div className="flex items-center gap-3">
            <div className="h-20 w-20 rounded-full bg-bgs2 overflow-hidden">
              {profile.photo_url && <img src={profile.photo_url} className="h-full w-full object-cover" />}
            </div>
            <label className="btn-secondary cursor-pointer">
              <ImagePlus size={14} /> Upload
              <input type="file" accept="image/*" className="hidden"
                     onChange={(e) => onUpload(e.target.files?.[0])} />
            </label>
          </div>
        </div>
        <div>
          <label className="label">Organisation name</label>
          <input className="input-base" value={profile.organisation_name || ''}
                 onChange={(e) => upd('organisation_name', e.target.value)} />
        </div>
        <div>
          <label className="label">Bio</label>
          <textarea className="input-base" rows={5} value={profile.bio || ''}
                    onChange={(e) => upd('bio', e.target.value)} />
        </div>
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> : <><Save size={14} /> Save</>}
        </button>
      </div>
    </main>
  );
}
