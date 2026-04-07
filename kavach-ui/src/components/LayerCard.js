import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Shield, Eye, Scan, Activity } from 'lucide-react';
import ScoreRing from './ScoreRing';

const ICONS  = { face_match: Shield, liveness: Eye, deepfake: Scan, behavior: Activity };
const LABELS = { face_match: 'Face Match', liveness: 'Liveness', deepfake: 'Deepfake', behavior: 'Behavior' };
const DESCS  = {
  face_match: 'ArcFace identity verification',
  liveness:   'rPPG + challenge-response',
  deepfake:   'FFT + landmark + optical flow',
  behavior:   'Device + IP + timing',
};

const STATUS_COLORS = {
  PASS: { color: '#00f5a0', bg: 'rgba(0,245,160,0.08)',  border: 'rgba(0,245,160,0.2)',  bar: 'linear-gradient(90deg,#059669,#00f5a0)' },
  WARN: { color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.2)', bar: 'linear-gradient(90deg,#d97706,#f59e0b)' },
  FAIL: { color: '#f43f5e', bg: 'rgba(244,63,94,0.08)',  border: 'rgba(244,63,94,0.2)',  bar: 'linear-gradient(90deg,#be123c,#f43f5e)' },
};

function StatusDot({ status }) {
  const c = STATUS_COLORS[status] || STATUS_COLORS.WARN;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: c.bg, border: `1px solid ${c.border}`,
      borderRadius: 999, padding: '2px 9px',
      fontSize: '0.63rem', fontWeight: 700, letterSpacing: '0.08em',
      color: c.color, textTransform: 'uppercase',
    }}>
      <motion.span
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 1.8, repeat: Infinity }}
        style={{ width: 5, height: 5, borderRadius: '50%', background: c.color, display: 'inline-block' }}
      />
      {status}
    </span>
  );
}

export default function LayerCard({ layerKey, data, delay = 0 }) {
  const [open, setOpen] = useState(false);
  const Icon    = ICONS[layerKey]  || Shield;
  const label   = LABELS[layerKey] || layerKey;
  const desc    = DESCS[layerKey]  || '';
  const status  = data?.status || 'WARN';
  const score   = data?.score  || 0;
  const weight  = data?.weight || '0%';
  const sc      = STATUS_COLORS[status] || STATUS_COLORS.WARN;
  const signals = data?.signals || {};
  const hasSigs = Object.keys(signals).length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      onClick={() => hasSigs && setOpen(o => !o)}
      style={{
        background: sc.bg,
        border: `1px solid ${sc.border}`,
        borderRadius: 16,
        padding: '16px 18px',
        cursor: hasSigs ? 'pointer' : 'default',
        transition: 'box-shadow 0.2s ease, border-color 0.2s ease',
        boxShadow: open ? `0 0 24px ${sc.color}20` : 'none',
        position: 'relative', overflow: 'hidden',
      }}
    >
      {/* Top shimmer */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${sc.color}30, transparent)`,
      }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
        {/* Icon box */}
        <div style={{
          width: 44, height: 44, borderRadius: 13, flexShrink: 0,
          background: `${sc.color}10`,
          border: `1px solid ${sc.color}25`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={18} color={sc.color} strokeWidth={1.8} />
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, fontSize: '0.88rem', letterSpacing: '-0.01em' }}>{label}</span>
            <StatusDot status={status} />
            <span style={{ fontSize: '0.63rem', color: 'rgba(241,245,255,0.28)', marginLeft: 'auto' }}>
              {weight}
            </span>
          </div>
          <div className="progress-track" style={{ marginBottom: 5 }}>
            <div className="progress-fill" style={{ width: `${score}%`, background: sc.bar }} />
          </div>
          <p style={{
            fontSize: '0.7rem', color: 'rgba(241,245,255,0.4)', lineHeight: 1.4,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {data?.detail || desc}
          </p>
        </div>

        {/* Score ring */}
        <ScoreRing score={score} status={status} size={52} strokeWidth={4} />

        {/* Chevron */}
        {hasSigs && (
          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25 }}>
            <ChevronDown size={15} color="rgba(241,245,255,0.3)" />
          </motion.div>
        )}
      </div>

      {/* Expanded signals */}
      <AnimatePresence>
        {open && hasSigs && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              marginTop: 14, paddingTop: 14,
              borderTop: `1px solid ${sc.color}15`,
            }}>
              {Object.entries(signals).map(([k, v]) => (
                <div key={k} className="signal-row">
                  <span style={{ fontSize: '0.72rem', color: 'rgba(241,245,255,0.4)', minWidth: 100, textTransform: 'capitalize' }}>
                    {k.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'rgba(241,245,255,0.75)', textAlign: 'right', lineHeight: 1.4 }}>
                    {typeof v === 'object' ? v.detail || JSON.stringify(v) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
