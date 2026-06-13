import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ArrowLeft, Upload, X, Trash2, AlertTriangle } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Input } from '../../../components/ui/Input.jsx';
import { Select } from '../../../components/ui/Select.jsx';
import { Textarea } from '../../../components/ui/Textarea.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { Modal } from '../../../components/ui/Modal.jsx';
import { useToast } from '../../../components/ui/Toast.jsx';
import { shopApi } from '../../shop/api.js';

const STATUSES = ['active', 'draft', 'archived'];

export default function ProductEditor() {
  const { id } = useParams();
  const isNew = !id || id === 'new';
  const navigate = useNavigate();
  const toast = useToast();
  const fileRef = useRef(null);

  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    name: '', description: '', category: '', price_usd: '',
    stock_quantity: 0, photos: [], status: 'active',
  });
  const [original, setOriginal] = useState(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [uploading, setUploading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    shopApi.admin.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (isNew) return;
    let alive = true;
    shopApi.admin.getProduct(id)
      .then((p) => {
        if (!alive) return;
        const f = {
          name: p.name || '',
          description: p.description || '',
          category: p.category || '',
          price_usd: String(p.price_usd ?? ''),
          stock_quantity: Number(p.stock_quantity ?? 0),
          photos: p.photos || [],
          status: p.status || 'active',
        };
        setForm(f);
        setOriginal({ ...p, ...f });
        setLoading(false);
      })
      .catch((e) => {
        toast.error(e?.response?.data?.message || 'Could not load product.');
        navigate('/salesman/products');
      });
    return () => { alive = false; };
  }, [id, isNew, navigate, toast]);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
    setErrors((e) => ({ ...e, [k]: undefined }));
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const url = await shopApi.admin.uploadImage(file);
      set('photos', [...(form.photos || []), url]);
    } catch (err) {
      toast.error(err?.response?.data?.message || 'Upload failed.');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  function removePhoto(idx) {
    set('photos', form.photos.filter((_, i) => i !== idx));
  }

  async function save() {
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        ...form,
        price_usd: form.price_usd,
        stock_quantity: Number(form.stock_quantity),
      };
      const product = isNew
        ? await shopApi.admin.createProduct(payload)
        : await shopApi.admin.updateProduct(id, payload);
      toast.success(isNew ? 'Product created.' : 'Product updated.');
      navigate(`/salesman/products/${product.id}`);
    } catch (err) {
      const data = err?.response?.data;
      if (data?.field_errors) {
        setErrors(data.field_errors);
      }
      toast.error(data?.message || 'Could not save.');
    } finally {
      setSaving(false);
    }
  }

  async function doDelete() {
    try {
      await shopApi.admin.deleteProduct(id);
      toast.success('Product deleted.');
      navigate('/salesman/products');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not delete.');
    }
  }

  if (loading) return <div className="flex justify-center py-10"><Spinner size={22} /></div>;

  return (
    <div>
      <Link to="/salesman/products" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> Products
      </Link>
      <h1 className="mt-2 font-display text-3xl text-ink">
        {isNew ? 'New product' : 'Edit product'}
      </h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <Card className="space-y-4">
            <Input
              label="Name *" placeholder="e.g. Samsung Galaxy A15"
              value={form.name} error={errors.name}
              onChange={(e) => set('name', e.target.value)}
            />
            <Textarea
              label="Description *" rows={5}
              placeholder="Include condition, warranty, what's in the box, sizing…"
              value={form.description} error={errors.description}
              onChange={(e) => set('description', e.target.value)}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Select
                label="Category *"
                value={form.category} error={errors.category}
                onChange={(e) => set('category', e.target.value)}
              >
                <option value="">Select category</option>
                {categories.map((c) => <option key={c}>{c}</option>)}
              </Select>
              <Select
                label="Status"
                value={form.status}
                onChange={(e) => set('status', e.target.value)}
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </Select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Price (USD) *" type="number" step="0.01" min="0"
                value={form.price_usd} error={errors.price_usd}
                onChange={(e) => set('price_usd', e.target.value)}
              />
              <Input
                label="Stock quantity *" type="number" min="0"
                value={form.stock_quantity} error={errors.stock_quantity}
                onChange={(e) => set('stock_quantity', e.target.value)}
                hint={original ? `${original.stock_held || 0} held • ${original.stock_sold || 0} sold` : null}
              />
            </div>
          </Card>

          <Card>
            <h3 className="font-display text-lg text-ink">Photos</h3>
            <p className="mt-1 text-sm text-inkm">
              At least one photo is required for active products. JPG/PNG/WEBP under 5MB.
            </p>
            {form.photos?.length > 0 && (
              <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">
                {form.photos.map((url, i) => (
                  <div key={i} className="relative aspect-square overflow-hidden rounded-md ring-1 ring-bordr">
                    <img src={url} alt="" className="h-full w-full object-cover" />
                    <button
                      type="button"
                      onClick={() => removePhoto(i)}
                      className="absolute top-1 right-1 rounded-full bg-bgp/80 p-1 text-danger ring-1 ring-bordr hover:bg-bgp"
                      title="Remove"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-3">
              <input
                ref={fileRef} type="file" accept="image/*"
                onChange={handleUpload} className="hidden"
              />
              <Button
                variant="secondary" onClick={() => fileRef.current?.click()}
                disabled={uploading}
              >
                <Upload size={14} /> {uploading ? 'Uploading…' : 'Add photo'}
              </Button>
              {errors.photos && <p className="mt-1 text-xs text-danger">{errors.photos}</p>}
            </div>
          </Card>
        </div>

        <div className="space-y-3">
          <Card>
            <h3 className="font-display text-lg text-ink">Actions</h3>
            <div className="mt-3 space-y-2">
              <Button variant="primary" onClick={save} disabled={saving} className="w-full justify-center">
                {saving ? 'Saving…' : isNew ? 'Create product' : 'Save changes'}
              </Button>
              {!isNew && (
                <Button
                  variant="secondary"
                  onClick={() => setConfirmDelete(true)}
                  className="w-full justify-center !text-danger !border-danger/30 hover:!bg-danger/5"
                >
                  <Trash2 size={14} /> Delete
                </Button>
              )}
            </div>
          </Card>
          {!isNew && original && (original.stock_held || 0) > 0 && (
            <Card className="!bg-warning/10 !border-warning/30">
              <div className="flex gap-2">
                <AlertTriangle size={16} className="text-warning shrink-0 mt-0.5" />
                <p className="text-sm text-ink">
                  {original.stock_held} unit{original.stock_held !== 1 ? 's' : ''} held by in-flight purchases.
                  Price edits are locked until those settle.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete this product?">
        <p className="text-sm text-inkm">
          Products with past sales get archived (kept for buyer records). Otherwise they are hard-deleted.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button variant="primary" onClick={doDelete} className="!bg-danger !border-danger">
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
