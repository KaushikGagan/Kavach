import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, ShieldX, Info } from 'lucide-react';

const CFG = {
  SAFE: {
    Icon: ShieldCheck, color: '#00f5a0', dimColor: '#059669',
    bg: 'rgba(0,245,160,0.06)', border: 'rgba(0,245,160,0.22)',
    glow: '0 0 80px rgba(0,245,160,0.15), 0 0 160px rgba(0,245,160,0.06)',
    label: 'Identity Verified', sub: 'KYC Approved',
    particle: '#00f5a0',
  },
  SUSPICIOUS: {
    Icon: ShieldAlert, color: '#f59e0b', dimColor: '#d97706',
    bg: 'rgba(245,158,11,0.06)', border: 'rgba(245,158,11,0.22)',
    glow: '0 0 80px rgba(245,158,11,0.15), 0 0 160px rgba(245,158,11,0.06)',
    label: 'Suspicious Activity', sub: 'Manual Review Required',
    particle: '#f59e0b',
  },
  FRAUD: {
    Icon: ShieldX, color: '#f43f5e', dimColor: '#be123c',
    bg: 'rgba(244,63,94,0.06)', border: 'rgba(244,63,94,0.22)',
    glow: '0 0 80px rgba(244,63,94,0.15), 0 0 160px rgba(244,63,94,0.06)',
    label: 'Fraud Detected', sub: 'KYC Blocked',
    particle: '#f43f5e',
  },
};

function MetricCard({ label, value, unit, color }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.09)',
        borderRadius: 14, padding: '12px 18px', textAlign: 'center',
        position: 'relative', overflow: 'hidden', minWidth: 90,
      }}
    >
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${color}40, transparent)` }} />
      <div style={{
        fontSize: '1.5rem', fontWeight: 800, color, lineHeight: 1,
        fontFamily: "'Space Grotesk', sans-serif",
        fontVariantNumeric: 'tabular-nums',
      }}>
        {value}<span style={{ fontSize: '0.75rem', opacity: 0.55, fontWeight: 600 }}>{unit}</span>
      </div>
      <div style={{ fontSize: '0.65rem', color: 'rgba(241,245,255,0.38)', marginTop: 4, letterSpacing: '0.06em' }}>
        {label}
      </div>
    </motion.div>
  );
}

export default function VerdictBanner({ result }) {
  const verdict = result?.verdict || 'SUSPICIOUS';
  const cfg = CFG[verdict] || CFG.SUSPICIOUS;
  const { Icon } = cfg;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94, y: 16 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      style={{
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderRadius: 24,
        boxShadow: cfg.glow,
        padding: '32px 28px 24px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Top shimmer line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${cfg.color}60, transparent)`,
      }} />

      {/* Radial background glow */}
      <div style={{
        position: 'absolute', top: '30%', left: '50%',
        transform: 'translate(-50%,-50%)',
        width: 320, height: 320, borderRadius: '50%',
        background: `radial-gradient(circle, ${cfg.color}10 0%, transparent 65%)`,
        pointerEvents: 'none',
      }} />

      {/* Ripple rings */}
      {[0, 1].map(i => (
        <motion.div key={i}
          style={{
            position: 'absolute', top: '28%', left: '50%',
            width: 70, height: 70, borderRadius: '50%',
            border: `1.5px solid ${cfg.color}`,
            transform: 'translate(-50%,-50%)',
            pointerEvents: 'none',
          }}
          animate={{ scale: [1, 3], opacity: [0.4, 0] }}
          transition={{ duration: 2.5, delay: i * 1.1, repeat: Infinity, ease: 'easeOut' }}
        />
      ))}

      {/* Icon */}
      <motion.div
        animate={{ y: [0, -5, 0] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        style={{ display: 'inline-flex', marginBottom: 18, position: 'relative' }}
      >
        <div style={{
          width: 76, height: 76, borderRadius: '50%',
          background: `${cfg.color}12`,
          border: `1.5px solid ${cfg.color}40`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: `0 0 32px ${cfg.color}30`,
        }}>
          <Icon size={34} color={cfg.color} strokeWidth={1.5} />
        </div>
      </motion.div>

      {/* Sub label */}
      <div style={{ marginBottom: 5 }}>
        <span style={{
          fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.18em',
          textTransform: 'uppercase', color: cfg.color, opacity: 0.75,
        }}>{cfg.sub}</span>
      </div>

      {/* Main verdict */}
      <motion.h2
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        style={{
          fontSize: '2rem', fontWeight: 900, color: cfg.color,
          marginBottom: 20, lineHeight: 1,
          fontFamily: "'Space Grotesk', sans-serif",
          letterSpacing: '-0.02em',
        }}
      >
        {cfg.label}
      </motion.h2>

      {/* Metrics */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <MetricCard label="Risk Score"  value={result?.risk_score ?? '--'}     unit="/100" color={cfg.color} />
        <MetricCard label="Confidence"  value={result?.confidence ?? '--'}     unit="%"    color={cfg.color} />
        <MetricCard label="Trust Score" value={result?.weighted_score ?? '--'} unit="/100" color={cfg.color} />
        {result?.layers?.liveness?.spoof_risk !== undefined && (
          <MetricCard label="Spoof Risk" value={result.layers.liveness.spoof_risk} unit="%" color={result.layers.liveness.spoof_risk > 60 ? '#f43f5e' : result.layers.liveness.spoof_risk > 30 ? '#f59e0b' : '#00f5a0'} />
        )}
      </div>

      {/* Reason panel */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        style={{
          background: 'rgba(0,0,0,0.25)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 12, padding: '12px 16px',
          display: 'flex', gap: 10, alignItems: 'flex-start', textAlign: 'left',
          marginBottom: 14,
        }}
      >
        <Info size={14} color={cfg.color} style={{ flexShrink: 0, marginTop: 1, opacity: 0.8 }} />
        <p style={{ fontSize: '0.78rem', color: 'rgba(241,245,255,0.65)', lineHeight: 1.55 }}>
          {result?.reason || 'Analysis complete.'}
        </p>
      </motion.div>

      {/* Action pill */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.4 }}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 7,
          background: `${cfg.color}12`,
          border: `1px solid ${cfg.color}28`,
          borderRadius: 999, padding: '6px 16px',
        }}
      >
        <motion.div
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          style={{ width: 5, height: 5, borderRadius: '50%', background: cfg.color }}
        />
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: cfg.color }}>
          {result?.action}
        </span>
      </motion.div>
    </motion.div>
  );
}
