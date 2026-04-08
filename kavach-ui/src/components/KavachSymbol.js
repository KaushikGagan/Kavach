import React from 'react';
import { motion } from 'framer-motion';

/**
 * KAVACH Logo — "The Sentinel Eye"
 * Concept: Hexagonal shield + biometric iris + neural dot pattern
 *
 * Symbolism:
 *  - Hexagon  → military-grade structural protection
 *  - Iris/Eye → biometric identity verification, "sees through fakes"
 *  - Dot grid → AI neural intelligence
 *  - Scan arc → active real-time verification
 *
 * Variants:
 *  variant="default"  → full color glow (navbar, hero)
 *  variant="mono"     → single color (small sizes)
 *  variant="outline"  → stroke only (watermark use)
 */
export default function KavachSymbol({
  size = 40,
  glow = true,
  animated = true,
  variant = 'default',
}) {
  const id = `ks_${size}_${variant}`;

  const svg = (
    <svg
      width={size} height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Primary gradient — purple → cyan */}
        <linearGradient id={`${id}_g1`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#8b5cf6" />
          <stop offset="55%"  stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>

        {/* Shield fill gradient */}
        <linearGradient id={`${id}_g2`} x1="20%" y1="0%" x2="80%" y2="100%">
          <stop offset="0%"   stopColor="#1e1040" />
          <stop offset="100%" stopColor="#0c1a2e" />
        </linearGradient>

        {/* Iris ring gradient */}
        <linearGradient id={`${id}_g3`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#22d3ee" />
        </linearGradient>

        {/* Glow filter */}
        <filter id={`${id}_glow`} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Strong glow for iris */}
        <filter id={`${id}_iris_glow`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Clip to shield */}
        <clipPath id={`${id}_clip`}>
          <path d="M50 8 L86 22 L86 50 C86 70 70 86 50 93 C30 86 14 70 14 50 L14 22 Z" />
        </clipPath>
      </defs>

      {/* ── Hexagonal Shield Body ─────────────────────────────────── */}
      {/* Outer glow ring */}
      <path
        d="M50 5 L88 20 L88 50 C88 72 70 89 50 96 C30 89 12 72 12 50 L12 20 Z"
        fill="none"
        stroke={`url(#${id}_g1)`}
        strokeWidth="0.8"
        opacity="0.4"
      />

      {/* Shield body */}
      <path
        d="M50 8 L86 22 L86 50 C86 70 70 86 50 93 C30 86 14 70 14 50 L14 22 Z"
        fill={`url(#${id}_g2)`}
      />

      {/* Shield border */}
      <path
        d="M50 8 L86 22 L86 50 C86 70 70 86 50 93 C30 86 14 70 14 50 L14 22 Z"
        fill="none"
        stroke={`url(#${id}_g1)`}
        strokeWidth="1.5"
        opacity="0.85"
      />

      {/* Top shimmer highlight */}
      <path
        d="M50 8 L86 22 L80 20 L50 10 L20 20 L14 22 Z"
        fill="rgba(255,255,255,0.07)"
      />

      {/* ── Biometric Iris (clipped inside shield) ────────────────── */}
      <g clipPath={`url(#${id}_clip)`} filter={`url(#${id}_iris_glow)`}>

        {/* Outer iris ring */}
        <circle cx="50" cy="52" r="24"
          fill="none"
          stroke={`url(#${id}_g3)`}
          strokeWidth="1.2"
          opacity="0.7"
        />

        {/* Mid iris ring */}
        <circle cx="50" cy="52" r="18"
          fill="none"
          stroke={`url(#${id}_g3)`}
          strokeWidth="0.8"
          opacity="0.5"
        />

        {/* Iris detail arcs — biometric texture */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => {
          const rad = (angle * Math.PI) / 180;
          const r1 = 19, r2 = 23;
          const x1 = 50 + r1 * Math.cos(rad);
          const y1 = 52 + r1 * Math.sin(rad);
          const x2 = 50 + r2 * Math.cos(rad);
          const y2 = 52 + r2 * Math.sin(rad);
          return (
            <line key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={`url(#${id}_g3)`}
              strokeWidth="0.8"
              opacity="0.6"
            />
          );
        })}

        {/* Neural dot pattern — AI intelligence grid */}
        {[
          [50, 34], [42, 37], [58, 37],
          [36, 44], [50, 44], [64, 44],
          [33, 52], [50, 52], [67, 52],
          [36, 60], [50, 60], [64, 60],
          [42, 67], [58, 67], [50, 70],
        ].map(([cx, cy], i) => (
          <circle key={i}
            cx={cx} cy={cy} r="1.2"
            fill={`url(#${id}_g3)`}
            opacity={i === 7 ? 1 : 0.45}
          />
        ))}

        {/* Neural connection lines */}
        {[
          [50,34, 42,37], [50,34, 58,37],
          [42,37, 36,44], [42,37, 50,44],
          [58,37, 50,44], [58,37, 64,44],
          [36,44, 33,52], [50,44, 50,52],
          [64,44, 67,52], [33,52, 36,60],
          [50,52, 50,60], [67,52, 64,60],
          [36,60, 42,67], [64,60, 58,67],
          [42,67, 50,70], [58,67, 50,70],
        ].map(([x1,y1,x2,y2], i) => (
          <line key={i}
            x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={`url(#${id}_g3)`}
            strokeWidth="0.4"
            opacity="0.2"
          />
        ))}

        {/* Pupil — center verification dot */}
        <circle cx="50" cy="52" r="5"
          fill={`url(#${id}_g1)`}
          opacity="0.9"
        />
        <circle cx="50" cy="52" r="2.5"
          fill="#fff"
          opacity="0.9"
        />

        {/* Pupil specular highlight */}
        <circle cx="52" cy="50" r="1"
          fill="#fff"
          opacity="0.6"
        />

        {/* Active scan arc */}
        <path
          d="M 28 52 A 22 22 0 0 1 72 52"
          fill="none"
          stroke={`url(#${id}_g3)`}
          strokeWidth="1"
          opacity="0.5"
          strokeDasharray="4 3"
        />
      </g>

      {/* ── Corner accent dots ────────────────────────────────────── */}
      <circle cx="50" cy="10" r="1.5" fill={`url(#${id}_g1)`} opacity="0.8" />
      <circle cx="85" cy="23" r="1"   fill={`url(#${id}_g1)`} opacity="0.5" />
      <circle cx="15" cy="23" r="1"   fill={`url(#${id}_g1)`} opacity="0.5" />

    </svg>
  );

  if (!animated) return svg;

  return (
    <motion.div
      animate={glow ? {
        filter: [
          'drop-shadow(0 0 4px rgba(139,92,246,0.5)) drop-shadow(0 0 8px rgba(6,182,212,0.2))',
          'drop-shadow(0 0 10px rgba(139,92,246,0.9)) drop-shadow(0 0 20px rgba(6,182,212,0.5)) drop-shadow(0 0 35px rgba(52,211,153,0.2))',
          'drop-shadow(0 0 4px rgba(139,92,246,0.5)) drop-shadow(0 0 8px rgba(6,182,212,0.2))',
        ],
      } : {}}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
    >
      {svg}
    </motion.div>
  );
}
