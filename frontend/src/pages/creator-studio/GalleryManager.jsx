import React, { useEffect, useState } from 'react';
import { Loader2, Upload, Trash2, Plus, FolderPlus } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { useToast } from '../../components/ui/Toast.jsx';
import { mediaUrl } from '../../utils/media.js';

const CATEGORIES = ['photography', 'painting', 'sculpture', 'fabricated', 'digital'];

export default function GalleryManager() {
  const toast = useToast();
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newCol, setNewCol] = useState({ title: '', description: '' });
  const [creating, setCreating] = useState(false);
  const [uploadingTo, setUploadingTo] = useState('');

  const load = () => creatorApi.listGallery().then((r) => setCollections(r.collections)).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const createCol = async () => {
    if (!newCol.title) { toast.error('Collection title is required.'); return; }
    setCreating(true);
    try { await creatorApi.createCollection(newCol); setNewCol({ title: '', description: '' }); load(); toast.success('Collection created.'); }
    catch (e) { toast.error(e.message); }
    finally { setCreating(false); }
  };

  const uploadInto = async (col, file, category) => {
    if (!file) return;
    setUploadingTo(col.id);
    try {
      const { url } = await creatorApi.uploadImage(file);
      await creatorApi.createItem({ title: file.name.replace(/\.[^.]+$/, ''), image_url: url, collection_id: col.id, category });
      load();
    } catch (e) { toast.error(e.message || 'Upload failed'); }
    finally { setUploadingTo(''); }
  };

  const delItem = async (id) => {
    try { await creatorApi.deleteItem(id); load(); } catch (e) { toast.error(e.message); }
  };
  const delCol = async (id) => {
    if (!window.confirm('Delete this collection and all its images?')) return;
    try { await creatorApi.deleteCollection(id); load(); } catch (e) { toast.error(e.message); }
  };

  return (
    <div>
      <h1 className="accent-rule font-display text-4xl text-ink">Gallery</h1>

      <div className="mt-5 rounded-xl border border-bordr bg-bgs p-4">
        <div className="mb-2 flex items-center gap-2 text-sm text-ink"><FolderPlus size={15} /> New collection</div>
        <div className="flex flex-wrap gap-2">
          <input className="input-base flex-1" placeholder="Collection title" value={newCol.title} onChange={(e) => setNewCol({ ...newCol, title: e.target.value })} />
          <input className="input-base flex-1" placeholder="Description (optional)" value={newCol.description} onChange={(e) => setNewCol({ ...newCol, description: e.target.value })} />
          <button className="btn-accent" onClick={createCol} disabled={creating}>{creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Create</button>
        </div>
      </div>

      <div className="mt-6 space-y-6">
        {loading ? (
          <div className="flex items-center gap-2 py-10 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>
        ) : collections.length === 0 ? (
          <p className="py-10 text-inkm">No collections yet — create one above to start uploading images.</p>
        ) : collections.map((c) => (
          <div key={c.id} className="rounded-xl border border-bordr bg-bgs p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-2xl text-ink">{c.title}</h3>
                {c.description && <p className="text-xs text-inkm">{c.description}</p>}
              </div>
              <div className="flex items-center gap-2">
                <label className="btn-secondary cursor-pointer">
                  {uploadingTo === c.id ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Add image
                  <input type="file" accept="image/*" hidden onChange={(e) => uploadInto(c, e.target.files?.[0], 'photography')} />
                </label>
                <button onClick={() => delCol(c.id)} className="rounded p-2 text-inkm hover:text-danger"><Trash2 size={16} /></button>
              </div>
            </div>
            {c.items?.length > 0 && (
              <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
                {c.items.map((it) => (
                  <div key={it.id} className="group relative overflow-hidden rounded-lg border border-bordr">
                    <img src={mediaUrl(it.image_url)} alt={it.title} className="aspect-square w-full object-cover" />
                    <button onClick={() => delItem(it.id)} className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white opacity-0 transition group-hover:opacity-100"><Trash2 size={13} /></button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
