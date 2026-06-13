import React from 'react';
import { QRCodeCanvas } from 'qrcode.react';

export function QRCodeView({ value, size = 240, label }) {
  return (
    <div className="inline-flex flex-col items-center gap-2">
      <div className="qr-card">
        <QRCodeCanvas value={value} size={size} level="M" includeMargin />
      </div>
      {label && <div className="text-xs text-inkm">{label}</div>}
    </div>
  );
}

export default QRCodeView;
