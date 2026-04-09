'use client';

import { motion } from 'framer-motion';

interface RegimeBeaconProps {
  regime: 'Bull' | 'Bear' | 'Neutral';
  weeksInRegime: number;
}

const REGIME_CONFIG = {
  Bull:    { text: 'text-success',     bg: 'bg-success',     rgb: 'rgb(var(--success))' },
  Bear:    { text: 'text-destructive', bg: 'bg-destructive', rgb: 'rgb(var(--destructive))' },
  Neutral: { text: 'text-warning',     bg: 'bg-warning',     rgb: 'rgb(var(--warning))' },
} as const;

export default function RegimeBeacon({ regime, weeksInRegime }: RegimeBeaconProps) {
  const cfg = REGIME_CONFIG[regime];

  return (
    <div className="flex items-center gap-2.5">
      {/* Beacon square with pulse */}
      <motion.div
        className={`w-9 h-9 rounded-lg flex items-center justify-center relative overflow-hidden ${cfg.bg}`}
        animate={{ scale: [1, 1.03, 1] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        {/* Outer pulse ring */}
        <motion.div
          className="absolute inset-0 rounded-lg"
          style={{ border: `2px solid ${cfg.rgb}` }}
          animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeOut' }}
        />
        <span className="text-[14px] font-bold text-white relative z-10 leading-none">
          {regime[0]}
        </span>
      </motion.div>

      {/* Label + duration */}
      <div className="flex flex-col">
        <motion.span
          key={regime}
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className={`text-[15px] font-bold uppercase tracking-wide leading-none ${cfg.text}`}
        >
          {regime}
        </motion.span>
        <span className="text-[11.5px] font-mono text-muted-foreground/40 mt-0.5 leading-none">
          WK {weeksInRegime}
        </span>
      </div>
    </div>
  );
}
