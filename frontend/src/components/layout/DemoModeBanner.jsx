import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useDemoMode } from '../../contexts/DemoModeContext.jsx';

export function DemoModeBanner() {
  const { demoMode, loaded } = useDemoMode();
  if (!loaded || !demoMode) return null;
  return (
    <div className="border-b border-warning/30 bg-warning/10 text-warning">
      <div className="container-page flex items-center gap-2 py-1.5 text-[12px] font-medium">
        <AlertTriangle size={14} />
        <span>
          DEMO MODE — mock messages are not delivered to real recipients.
        </span>
      </div>
    </div>
  );
}
