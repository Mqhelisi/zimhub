import React, { useEffect, useRef, useState } from 'react';
import { Upload, ExternalLink, Lock } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Input } from '../../../components/ui/Input.jsx';
import { Textarea } from '../../../components/ui/Textarea.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { useToast } from '../../../components/ui/Toast.jsx';
import { shopApi } from '../../shop/api.js';

export default function Profile() {
  const toast = useToast();
  const photoRef = useRef(null);
  const bannerRef = useRef(null);
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(null);

  useEffect(() => {
    shopApi.admin.getProfile().then((p) => {
      setProfile(p);
      setForm({
        shop_name: p.shop_name || '',
        bio: p.bio || '',
        photo_url: p.photo_url || '',
        banner_url: p.banner_url || '',
        pickup_delivery_policy: p.pickup_delivery_policy || '',
      });
    });
  }, []);

  if (!form) return <div className="flex justify-center py-10"><Spinner size={22} /></div>;

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function upload(kind) {
    const ref = kind === 'photo' ? photoRef : bannerRef;
    const file = ref.current?.files?.[0];
    if (!file) return;
    setUploading(kind);
    try {
      const url = await shopApi.admin.uploadImage(file);
      set(kind === 'photo' ? 'photo_url' : 'banner_url', url);
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Upload failed.');
    } finally {
      setUploading(null);
      if (ref.current) ref.current.value = '';
    }
  }

  async function save() {
    setSaving(true);
    try {
      const p = await shopApi.admin.updateProfile(form);
      setProfile(p);
      toast.success('Profile saved.');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not save.');
    } finally { setSaving(false); }
  }

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl text-ink">Shop profile</h1>
          <p className="mt-1 text-sm text-inkm">How your shop appears to buyers.</p>
        </div>
        {profile.shop_slug && (
          <Link to={`/shop/salesman/${profile.shop_slug}`} className="text-sm text-brand hover:underline inline-flex items-center gap-1">
            <ExternalLink size={12} /> View public page
          </Link>
        )}
      </div>

      <Card className="mt-6 space-y-4">
        <Input
          label="Shop name"
          value={form.shop_name}
          onChange={(e) => set('shop_name', e.target.value)}
        />
        <div>
          <div className="label inline-flex items-center gap-1"><Lock size={11} /> Shop URL slug</div>
          <div className="mt-1 input-base !bg-bgp !text-inkm">{profile.shop_slug}</div>
          <p className="mt-1 text-xs text-inkm">Locked after first save to keep links stable.</p>
        </div>
        <Textarea
          label="Bio"
          rows={3}
          placeholder="A line or two about your shop, your style, and what you stock."
          value={form.bio}
          onChange={(e) => set('bio', e.target.value)}
        />
        <Textarea
          label="Pickup & delivery policy"
          rows={3}
          placeholder="Where buyers can collect, what couriers you use, any fees, hours."
          value={form.pickup_delivery_policy}
          onChange={(e) => set('pickup_delivery_policy', e.target.value)}
        />
      </Card>

      <Card className="mt-4">
        <h3 className="font-display text-lg text-ink">Shop photo (avatar)</h3>
        <div className="mt-3 flex items-center gap-4">
          {form.photo_url ? (
            <img src={form.photo_url} alt=""
                 className="h-20 w-20 rounded-full object-cover ring-1 ring-bordr" />
          ) : (
            <div className="h-20 w-20 rounded-full bg-bgs2 ring-1 ring-bordr" />
          )}
          <div>
            <input ref={photoRef} type="file" accept="image/*"
                   onChange={() => upload('photo')} className="hidden" />
            <Button
              variant="secondary"
              onClick={() => photoRef.current?.click()}
              disabled={uploading === 'photo'}
            >
              <Upload size={14} /> {uploading === 'photo' ? 'Uploading…' : 'Upload photo'}
            </Button>
          </div>
        </div>
      </Card>

      <Card className="mt-4">
        <h3 className="font-display text-lg text-ink">Banner</h3>
        <div className="mt-3">
          {form.banner_url ? (
            <div
              className="h-32 w-full rounded-md bg-cover bg-center ring-1 ring-bordr"
              style={{ backgroundImage: `url(${form.banner_url})` }}
            />
          ) : (
            <div className="h-32 w-full rounded-md bg-bgs2 ring-1 ring-bordr flex items-center justify-center text-inkm text-sm">
              No banner yet
            </div>
          )}
          <input ref={bannerRef} type="file" accept="image/*"
                 onChange={() => upload('banner')} className="hidden" />
          <Button
            variant="secondary"
            onClick={() => bannerRef.current?.click()}
            disabled={uploading === 'banner'}
            className="mt-3"
          >
            <Upload size={14} /> {uploading === 'banner' ? 'Uploading…' : 'Upload banner'}
          </Button>
        </div>
      </Card>

      <div className="mt-6 flex justify-end">
        <Button variant="primary" onClick={save} disabled={saving}>
          {saving ? 'Saving…' : 'Save profile'}
        </Button>
      </div>
    </div>
  );
}
