import React from 'react';

const toneClasses = {
  default: 'border-bordr bg-bgs2 text-inkm',
  brand: 'border-brand/40 bg-brand/10 text-brand',
  shop: 'border-shop/40 bg-shop/10 text-shop',
  events: 'border-events/40 bg-events/10 text-events',
  services: 'border-services/40 bg-services/10 text-services',
  creators: 'border-creators/40 bg-creators/10 text-creators',
  success: 'border-success/40 bg-success/10 text-success',
  warning: 'border-warning/40 bg-warning/10 text-warning',
  danger: 'border-danger/40 bg-danger/10 text-danger',
};

const categoryToTone = {
  salesman: 'shop',
  promoter: 'events',
  provider: 'services',
  creator: 'creators',
  is_salesman: 'shop',
  is_promoter: 'events',
  is_provider: 'services',
  is_creator: 'creators',
  is_super_admin: 'brand',
  is_buyer: 'default',
};

export function Badge({ tone = 'default', category, className = '', children, ...rest }) {
  const resolved = category ? categoryToTone[category] || tone : tone;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wider ${toneClasses[resolved]} ${className}`}
      {...rest}
    >
      {children}
    </span>
  );
}
