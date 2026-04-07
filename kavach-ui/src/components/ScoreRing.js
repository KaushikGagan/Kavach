import React from 'react';

const COLOR_MAP = {
  PASS: '#00f5a0', WARN: '#ffd93d', FAIL: '#ff4d6d',
  SAFE: '#00f5a0', SUSPICIOUS: '#ffd93d', FRAUD: '#ff4d6d',
};

export default function ScoreRing({ score = 0, status = 'PASS', size = 80, strokeWidth = 6, label }) {
  const r = (size - strokeWidth * 2) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = COLOR_MAP[status] || '#a78bfa';
  const cx = size / 2;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} className="score-ring">
          <circle className="score-ring-track" cx={cx} cy={cx} r={r} strokeWidth={strokeWidth} />
          <circle
            className="score-ring-fill"
            cx={cx} cy={cx} r={r}
            strokeWidth={strokeWidth}
            stroke={color}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ filter: `drop-shadow(0 0 6px ${color}88)` }}
          />
        </svg>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{ fontSize: size * 0.22, fontWeight: 700, color, lineHeight: 1 }}>{score}</span>
          <span style={{ fontSize: size * 0.13, color: 'rgba(240,244,255,0.5)', lineHeight: 1 }}>/100</span>
        </div>
      </div>
      {label && <span style={{ fontSize: '0.72rem', color: 'rgba(240,244,255,0.55)', textAlign: 'center' }}>{label}</span>}
    </div>
  );
}
