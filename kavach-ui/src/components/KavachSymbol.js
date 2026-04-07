import React from 'react';
import { motion } from 'framer-motion';

/**
 * KavachSymbol — the official KAVACH brand emblem
 * A layered shield with an inner "K" mark and animated glow
 * size: number (px)
 * glow: boolean — whether to animate the glow
 * animated: boolean — whether to pulse
 */
export default function KavachSymbol({ size = 40, glow = true, animated = true }) {
  const s = size;

  const symbol = (
    <svg
      width={s} height={s}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="kg1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#a78bfa" />
          <stop offset="50%"  stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>
        <linearGradient id="kg2" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
        <filter id="kglow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Outer shield */}
      <path
        d="M50 6 L88 20 L88 52 C88 72 70 88 50 94 C30 88 12 72 12 52 L12 20 Z"
        fill="url(#kg2)"
        opacity="0.9"
      />

      {/* Inner shield highlight */}
      <path
        d="M50 14 L80 25 L80 52 C80 68 65 81 50 86 C35 81 20 68 20 52 L20 25 Z"
        fill="none"
        stroke="url(#kg1)"
        strokeWidth="1.5"
        opacity="0.6"
      />

      {/* Inner fill */}
      <path
        d="M50 14 L80 25 L80 52 C80 68 65 81 50 86 C35 81 20 68 20 52 L20 25 Z"
        fill="rgba(255,255,255,0.06)"
      />

      {/* K lettermark */}
      <g filter="url(#kglow)">
        {/* Vertical bar of K */}
        <rect x="36" y="32" width="6" height="36" rx="2" fill="url(#kg1)" />
        {/* Upper diagonal of K */}
        <path d="M42 50 L62 32" stroke="url(#kg1)" strokeWidth="6" strokeLinecap="round" />
        {/* Lower diagonal of K */}
        <path d="M42 50 L62 68" stroke="url(#kg1)" strokeWidth="6" strokeLinecap="round" />
      </g>

      {/* Top shimmer line on shield */}
      <path
        d="M50 6 L88 20"
        stroke="rgba(255,255,255,0.35)"
        strokeWidth="1"
        strokeLinecap="round"
      />
      <path
        d="M50 6 L12 20"
        stroke="rgba(255,255,255,0.15)"
        strokeWidth="1"
        strokeLinecap="round"
      />
    </svg>
  );

  if (!animated) return symbol;

  return (
    <motion.div
      animate={glow ? {
        filter: [
          'drop-shadow(0 0 6px rgba(139,92,246,0.6))',
          'drop-shadow(0 0 14px rgba(139,92,246,0.9)) drop-shadow(0 0 28px rgba(56,189,248,0.4))',
          'drop-shadow(0 0 6px rgba(139,92,246,0.6))',
        ],
      } : {}}
      transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
    >
      {symbol}
    </motion.div>
  );
}
