import React from 'react';
import { useFormContext } from 'react-hook-form';
import { ApplyShared } from './ApplyShared.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Select } from '../../components/ui/Select.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';

function SalesmanFields() {
  const { register, formState: { errors } } = useFormContext();
  return (
    <>
      <Input
        label="Shop name"
        error={errors.shop_name?.message}
        {...register('shop_name', { required: 'Required' })}
      />
      <Select
        label="Primary product category"
        error={errors.primary_category?.message}
        {...register('primary_category', { required: 'Required' })}
      >
        <option value="">Select a category</option>
        <option>Clothing & accessories</option>
        <option>Electronics & accessories</option>
        <option>Home & living</option>
        <option>Beauty & personal care</option>
        <option>Food & pantry</option>
        <option>Toys & kids</option>
        <option>Books & stationery</option>
        <option>Other</option>
      </Select>
      <Textarea
        label="Sample products"
        rows={3}
        placeholder="A few examples of what you sell."
        error={errors.sample_products?.message}
        {...register('sample_products', { required: 'Required' })}
      />
      <Select
        label="Pickup / delivery preference"
        error={errors.pickup_delivery_preference?.message}
        {...register('pickup_delivery_preference', { required: 'Required' })}
      >
        <option value="">Choose one</option>
        <option>Pickup only</option>
        <option>Pickup + Bulawayo delivery</option>
        <option>Pickup + nationwide courier</option>
        <option>Delivery only</option>
      </Select>
    </>
  );
}

export default function ApplySalesman() {
  return (
    <ApplyShared
      category="salesman"
      title="Apply as a Salesman"
      lede="Sell products on ZimHub Shop — from a CBD storefront, a home studio, or a small warehouse."
      businessNameLabel="Shop / business name (optional)"
      buildPayload={(d) => ({
        shop_name: d.shop_name,
        primary_category: d.primary_category,
        sample_products: d.sample_products,
        pickup_delivery_preference: d.pickup_delivery_preference,
      })}
    >
      <SalesmanFields />
    </ApplyShared>
  );
}
