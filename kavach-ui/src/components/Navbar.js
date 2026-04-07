import React from 'react';
import { motion } from 'framer-motion';
import { Cpu } from 'lucide-react';
import KavachSymbol from './KavachSymbol';

export default function Navbar() {
  return (
    <motion.nav
      initial={{ y: -70, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        height: 62,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 28px',
        background: 'rgba(3,5,15,0.75)',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        backdropFilter: 'blur(32px) saturate(180%)',
        WebkitBackdropFilter: 'blur(32px) saturate(180%)',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <KavachSymbol size={36} glow animated />
        <div>
          <div style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 800, fontSize: '1.05rem', lineHeight: 1,
            background: 'linear-gradient(135deg, #c4b5fd, #67e8f9)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            letterSpacing: '0.04em',
          }}>
            KAVACH
          </div>
          <div style={{ fontSize: '0.6rem', color: 'rgba(241,245,255,0.35)', marginTop: 2, letterSpacing: '0.08em' }}>
            AI-POWERED KYC
          </div>
        </div>
      </div>

      {/* Center pill */}
      <div style={{
        position: 'absolute', left: '50%', transform: 'translateX(-50%)',
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'rgba(139,92,246,0.08)',
        border: '1px solid rgba(139,92,246,0.18)',
        borderRadius: 999, padding: '4px 14px',
      }}>
        <Cpu size={11} color="#a78bfa" />
        <span style={{ fontSize: '0.67rem', color: '#a78bfa', fontWeight: 600, letterSpacing: '0.1em' }}>
          5-LAYER PROTECTION
        </span>
      </div>

      {/* Right — status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 7,
          background: 'rgba(0,245,160,0.07)',
          border: '1px solid rgba(0,245,160,0.18)',
          borderRadius: 999, padding: '5px 13px',
        }}>
          <div style={{ position: 'relative', width: 7, height: 7 }}>
            <motion.div
              animate={{ scale: [1, 2.2], opacity: [0.6, 0] }}
              transition={{ duration: 1.8, repeat: Infinity }}
              style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: '#00f5a0' }}
            />
            <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: '#00f5a0' }} />
          </div>
          <span style={{ fontSize: '0.68rem', color: '#00f5a0', fontWeight: 600, letterSpacing: '0.06em' }}>
            ONLINE
          </span>
        </div>
        <div style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 7, padding: '4px 10px',
        }}>
          <span style={{ fontSize: '0.63rem', color: 'rgba(241,245,255,0.3)', fontWeight: 500 }}>v2.0</span>
        </div>
      </div>
    </motion.nav>
  );
}
