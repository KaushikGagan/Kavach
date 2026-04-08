import React, { useId } from 'react';
import { motion } from 'framer-motion';

export default function KavachSymbol({ size = 40, glow = true, animated = true }) {
  const uid = useId().replace(/:/g, '');

  const svg = (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id={`${uid}a`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#8b5cf6" />
          <stop offset="50%"  stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>
        <linearGradient id={`${uid}b`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#1a0a3a" />
          <stop offset="100%" stopColor="#071525" />
        </linearGradient>
        <linearGradient id={`${uid}c`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%"   stopColor="#c4b5fd" />
          <stop offset="100%" stopColor="#67e8f9" />
        </linearGradient>
        <filter id={`${uid}f`} x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <clipPath id={`${uid}clip`}>
          <path d="M50 9 L85 23 L85 51 C85 69 69 84 50 91 C31 84 15 69 15 51 L15 23 Z" />
        </clipPath>
      </defs>

      {/* ── Shield ── */}
      {/* Outer glow border */}
      <path d="M50 6 L88 21 L88 51 C88 72 71 88 50 95 C29 88 12 72 12 51 L12 21 Z"
        fill="none" stroke={`url(#${uid}a)`} strokeWidth="0.6" opacity="0.35" />

      {/* Shield body */}
      <path d="M50 9 L85 23 L85 51 C85 69 69 84 50 91 C31 84 15 69 15 51 L15 23 Z"
        fill={`url(#${uid}b)`} />

      {/* Shield border */}
      <path d="M50 9 L85 23 L85 51 C85 69 69 84 50 91 C31 84 15 69 15 51 L15 23 Z"
        fill="none" stroke={`url(#${uid}a)`} strokeWidth="1.8" opacity="0.9" />

      {/* Top gloss */}
      <path d="M50 9 L85 23 L78 21 L50 11 L22 21 L15 23 Z"
        fill="rgba(255,255,255,0.09)" />

      {/* ── Eye / Iris inside shield ── */}
      <g clipPath={`url(#${uid}clip)`}>

        {/* Eye whites / outer glow */}
        <ellipse cx="50" cy="51" rx="26" ry="17"
          fill="rgba(139,92,246,0.08)"
          stroke={`url(#${uid}c)`} strokeWidth="0.8" opacity="0.5" />

        {/* Iris outer ring */}
        <circle cx="50" cy="51" r="13"
          fill="rgba(6,182,212,0.1)"
          stroke={`url(#${uid}c)`} strokeWidth="1.4" opacity="0.9" />

        {/* Iris mid ring */}
        <circle cx="50" cy="51" r="9"
          fill="rgba(139,92,246,0.15)"
          stroke={`url(#${uid}c)`} strokeWidth="0.8" opacity="0.7" />

        {/* Iris texture lines */}
        {[0,30,60,90,120,150,180,210,240,270,300,330].map((deg, i) => {
          const r = deg * Math.PI / 180;
          return (
            <line key={i}
              x1={50 + 9.5 * Math.cos(r)}  y1={51 + 9.5 * Math.sin(r)}
              x2={50 + 12.5 * Math.cos(r)} y2={51 + 12.5 * Math.sin(r)}
              stroke={`url(#${uid}c)`} strokeWidth="0.7" opacity="0.55"
            />
          );
        })}

        {/* Neural dots around iris */}
        {[0,45,90,135,180,225,270,315].map((deg, i) => {
          const r = deg * Math.PI / 180;
          return (
            <circle key={i}
              cx={50 + 17 * Math.cos(r)} cy={51 + 17 * Math.sin(r)}
              r="1.3" fill={`url(#${uid}c)`} opacity="0.6"
            />
          );
        })}

        {/* Neural connection lines */}
        {[0,45,90,135,180,225,270,315].map((deg, i) => {
          const r = deg * Math.PI / 180;
          const next = ((i + 1) % 8) * 45 * Math.PI / 180;
          return (
            <line key={i}
              x1={50 + 17 * Math.cos(r)}    y1={51 + 17 * Math.sin(r)}
              x2={50 + 17 * Math.cos(next)} y2={51 + 17 * Math.sin(next)}
              stroke={`url(#${uid}c)`} strokeWidth="0.35" opacity="0.2"
            />
          );
        })}

        {/* Pupil */}
        <circle cx="50" cy="51" r="5"
          fill={`url(#${uid}a)`} opacity="1" filter={`url(#${uid}f)`} />

        {/* Pupil core */}
        <circle cx="50" cy="51" r="3" fill="#0a0520" />

        {/* Pupil specular */}
        <circle cx="52" cy="49" r="1.2" fill="rgba(255,255,255,0.85)" />

        {/* Scan line across eye */}
        <line x1="24" y1="51" x2="76" y2="51"
          stroke={`url(#${uid}c)`} strokeWidth="0.6"
          strokeDasharray="3 2" opacity="0.4" />
      </g>

      {/* ── Corner accent dots ── */}
      <circle cx="50" cy="11" r="1.8" fill={`url(#${uid}a)`} opacity="0.9" />
      <circle cx="84" cy="24" r="1.1" fill={`url(#${uid}a)`} opacity="0.6" />
      <circle cx="16" cy="24" r="1.1" fill={`url(#${uid}a)`} opacity="0.6" />
    </svg>
  );

  if (!animated) return svg;

  return (
    <motion.div
      animate={glow ? {
        filter: [
          'drop-shadow(0 0 5px rgba(139,92,246,0.6)) drop-shadow(0 0 10px rgba(6,182,212,0.25))',
          'drop-shadow(0 0 12px rgba(139,92,246,1)) drop-shadow(0 0 24px rgba(6,182,212,0.6)) drop-shadow(0 0 40px rgba(52,211,153,0.25))',
          'drop-shadow(0 0 5px rgba(139,92,246,0.6)) drop-shadow(0 0 10px rgba(6,182,212,0.25))',
        ],
      } : {}}
      transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
    >
      {svg}
    </motion.div>
  );
}
