import React from 'react';
import { motion } from 'framer-motion';
import KavachSymbol from './KavachSymbol';

/**
 * KavachLogoAnimated — large hero logo with:
 *  - Particle orbit ring
 *  - Scan line sweep across the iris
 *  - Pulse rings on verification start
 *  - Rotating outer ring
 *
 * Use on: hero section, analyzing screen, loading screen
 */
export default function KavachLogoAnimated({ size = 120, scanning = false }) {
  return (
    <div style={{ position: 'relative', width: size, height: size, display: 'inline-flex',
      alignItems: 'center', justifyContent: 'center' }}>

      {/* Outer rotating ring */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute', inset: -10,
          borderRadius: '50%',
          border: '1px solid transparent',
          borderTopColor: 'rgba(139,92,246,0.6)',
          borderRightColor: 'rgba(6,182,212,0.3)',
        }}
      />

      {/* Counter-rotating inner ring */}
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        style={{
          position: 'absolute', inset: -4,
          borderRadius: '50%',
          border: '1px dashed rgba(6,182,212,0.25)',
        }}
      />

      {/* Orbiting particle dots */}
      {[0, 120, 240].map((deg, i) => (
        <motion.div
          key={i}
          animate={{ rotate: 360 }}
          transition={{ duration: 6 + i * 1.5, repeat: Infinity, ease: 'linear', delay: i * 0.5 }}
          style={{ position: 'absolute', inset: -8, borderRadius: '50%' }}
        >
          <div style={{
            position: 'absolute',
            top: '50%', left: '50%',
            width: 5, height: 5,
            borderRadius: '50%',
            background: i === 0 ? '#8b5cf6' : i === 1 ? '#06b6d4' : '#34d399',
            boxShadow: `0 0 8px ${i === 0 ? '#8b5cf6' : i === 1 ? '#06b6d4' : '#34d399'}`,
            transform: `rotate(${deg}deg) translateX(${size / 2 + 8}px) translateY(-50%)`,
          }} />
        </motion.div>
      ))}

      {/* Pulse rings — always on */}
      {[0, 1].map(i => (
        <motion.div key={i}
          animate={{ scale: [1, 1.8], opacity: [0.35, 0] }}
          transition={{ duration: 2.5, delay: i * 1.2, repeat: Infinity, ease: 'easeOut' }}
          style={{
            position: 'absolute', inset: 0,
            borderRadius: '50%',
            border: '1.5px solid rgba(139,92,246,0.5)',
          }}
        />
      ))}

      {/* Scan line sweep — active during scanning */}
      {scanning && (
        <motion.div
          initial={{ top: '15%', opacity: 0 }}
          animate={{ top: ['15%', '85%', '15%'], opacity: [0, 1, 1, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute', left: '10%', right: '10%',
            height: 2,
            background: 'linear-gradient(90deg, transparent, rgba(6,182,212,0.9), rgba(139,92,246,0.9), transparent)',
            borderRadius: 1,
            filter: 'blur(1px)',
            zIndex: 2,
          }}
        />
      )}

      {/* The actual logo */}
      <KavachSymbol size={size} glow animated />
    </div>
  );
}
