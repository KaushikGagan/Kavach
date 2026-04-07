import React from 'react';
import { motion } from 'framer-motion';
import KavachSymbol from './KavachSymbol';

const LAYERS = [
  { label: 'Validating session nonce',      color: '#8b5cf6', icon: '🔐' },
  { label: 'Extracting video frames',       color: '#06b6d4', icon: '🎞' },
  { label: 'rPPG blood flow analysis',      color: '#00f5a0', icon: '💓' },
  { label: 'ArcFace identity matching',     color: '#8b5cf6', icon: '🪪' },
  { label: 'FFT frequency artifact scan',   color: '#06b6d4', icon: '📡' },
  { label: 'Landmark jitter analysis',      color: '#f59e0b', icon: '📍' },
  { label: 'Optical flow verification',     color: '#00f5a0', icon: '🌊' },
  { label: 'Behavioral context scoring',    color: '#8b5cf6', icon: '🧠' },
  { label: 'Risk engine computing verdict', color: '#06b6d4', icon: '⚖' },
];

export default function AnalyzingScreen() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{ padding: '36px 28px', textAlign: 'center' }}
    >
      {/* Orbital scanner */}
      <div style={{ position: 'relative', width: 130, height: 130, margin: '0 auto 32px' }}>
        {/* Outer rings */}
        {[0, 1, 2].map(i => (
          <motion.div key={i}
            style={{
              position: 'absolute',
              inset: i * 18,
              borderRadius: '50%',
              border: `1px solid rgba(${i === 0 ? '139,92,246' : i === 1 ? '6,182,212' : '0,245,160'},${0.5 - i * 0.1})`,
            }}
            animate={{ rotate: i % 2 === 0 ? 360 : -360 }}
            transition={{ duration: 4 + i * 1.5, repeat: Infinity, ease: 'linear' }}
          />
        ))}
        {/* Orbiting dot */}
        <motion.div
          style={{ position: 'absolute', inset: 0 }}
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <div style={{
            position: 'absolute', top: 0, left: '50%',
            transform: 'translateX(-50%)',
            width: 7, height: 7, borderRadius: '50%',
            background: '#8b5cf6',
            boxShadow: '0 0 10px rgba(139,92,246,0.9)',
          }} />
        </motion.div>
        {/* Center core */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <motion.div
            animate={{ scale: [1, 1.12, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <KavachSymbol size={44} glow animated />
          </motion.div>
        </div>
      </div>

      <motion.h3
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 2, repeat: Infinity }}
        style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: 5, letterSpacing: '-0.01em' }}
      >
        Analyzing Identity
      </motion.h3>
      <p style={{ fontSize: '0.8rem', color: 'rgba(241,245,255,0.45)', marginBottom: 28 }}>
        Running 5-layer security verification
      </p>

      {/* Layer list */}
      <div style={{ maxWidth: 360, margin: '0 auto', textAlign: 'left' }}>
        {LAYERS.map((layer, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.25, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 9 }}
          >
            <span style={{ fontSize: '0.75rem', width: 16, textAlign: 'center', flexShrink: 0 }}>{layer.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: '0.73rem', color: 'rgba(241,245,255,0.6)', fontWeight: 500 }}>{layer.label}</span>
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.25 + 0.6 }}
                  style={{ fontSize: '0.62rem', color: layer.color, fontWeight: 600 }}
                >
                  ✓
                </motion.span>
              </div>
              <div className="progress-track">
                <motion.div
                  className="progress-fill"
                  initial={{ width: '0%' }}
                  animate={{ width: '100%' }}
                  transition={{ delay: i * 0.25, duration: 0.7, ease: 'easeOut' }}
                  style={{ background: `linear-gradient(90deg, ${layer.color}55, ${layer.color})` }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
