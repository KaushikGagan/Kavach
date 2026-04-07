import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { User, Image, RefreshCw, Cpu } from 'lucide-react';
import { runDemoScenario } from '../api';

const SCENARIOS = [
  { key: 'real_user',    label: 'Real User',     icon: User,       color: '#00f5a0', desc: 'Legitimate KYC → SAFE' },
  { key: 'photo_spoof',  label: 'Photo Spoof',   icon: Image,      color: '#ffd93d', desc: 'Static photo attack → FRAUD' },
  { key: 'video_replay', label: 'Video Replay',  icon: RefreshCw,  color: '#ffd93d', desc: 'Replay attack → FRAUD' },
  { key: 'deepfake',     label: 'Deepfake',      icon: Cpu,        color: '#ff4d6d', desc: 'AI-generated face → FRAUD' },
];

export default function DemoPanel({ onResult }) {
  const [loading, setLoading] = useState(null);

  async function run(key) {
    setLoading(key);
    try {
      const result = await runDemoScenario(key);
      onResult(result);
    } catch {
      // fallback mock if backend offline
      onResult(MOCK_RESULTS[key]);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="glass" style={{ padding: '20px 22px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: '#a78bfa',
          boxShadow: '0 0 8px #a78bfa',
        }} />
        <span style={{ fontSize: '0.78rem', fontWeight: 700, letterSpacing: '0.1em', color: 'rgba(240,244,255,0.6)', textTransform: 'uppercase' }}>
          Demo Scenarios
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {SCENARIOS.map(({ key, label, icon: Icon, color, desc }, i) => (
          <motion.button
            key={key}
            whileHover={{ scale: 1.03, y: -2 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => run(key)}
            disabled={loading !== null}
            style={{
              background: `${color}0d`,
              border: `1px solid ${color}30`,
              borderRadius: 12, padding: '12px 14px',
              cursor: loading ? 'not-allowed' : 'pointer',
              textAlign: 'left', transition: 'border-color 0.2s',
              opacity: loading && loading !== key ? 0.5 : 1,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
              {loading === key ? (
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}>
                  <RefreshCw size={14} color={color} />
                </motion.div>
              ) : (
                <Icon size={14} color={color} />
              )}
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color }}>{label}</span>
            </div>
            <p style={{ fontSize: '0.7rem', color: 'rgba(240,244,255,0.45)', lineHeight: 1.3 }}>{desc}</p>
          </motion.button>
        ))}
      </div>
    </div>
  );
}

// Offline fallback mock results
const MOCK_RESULTS = {
  real_user: {
    verdict: 'SAFE', risk_score: 8, confidence: 94, weighted_score: 92,
    action: 'Approve KYC',
    reason: 'All checks passed — identity verified',
    layers: {
      face_match: { score: 91, status: 'PASS', detail: 'ArcFace similarity 91.2%', weight: '30%' },
      liveness:   { score: 95, status: 'PASS', detail: 'Liveness score 95/100', weight: '30%', signals: { rppg: { detail: 'BPM=72, pulse detected' }, glare: { detail: 'Glare 0.8% — normal' }, replay: { detail: 'Duplicate ratio 4% — normal' } } },
      deepfake:   { score: 94, status: 'PASS', detail: '0/4 signals triggered', weight: '25%', signals: { frequency: { detail: 'HF ratio 0.41 — normal' }, landmark_jitter: { detail: 'Jitter 0.82px — smooth' }, optical_flow: { detail: 'Flow 1.23 — natural' }, facial_warping: { detail: 'Edge 0.06 — clean' } } },
      behavior:   { score: 92, status: 'PASS', detail: 'Behavioral score 92/100', weight: '15%', signals: { speed: { detail: '12.3s — normal' }, user_agent: { detail: 'Real browser' }, ip: { detail: 'Public IP' } } },
    },
  },
  photo_spoof: {
    verdict: 'FRAUD', risk_score: 88, confidence: 91, weighted_score: 12,
    action: 'Block — do not approve',
    reason: 'Issues detected: No blood flow signal (rPPG) — possible photo or screen spoof; Screen glare detected; Video replay attack detected',
    layers: {
      face_match: { score: 78, status: 'PASS', detail: 'ArcFace similarity 78.4%', weight: '30%' },
      liveness:   { score: 10, status: 'FAIL', detail: 'Liveness score 10/100 — FAIL', weight: '30%', signals: { rppg: { detail: 'BPM=0, SNR=0.02 — no pulse' }, glare: { detail: 'Glare 7.1% — screen detected' }, replay: { detail: 'Duplicate ratio 89% — REPLAY DETECTED' } } },
      deepfake:   { score: 70, status: 'PASS', detail: '1/4 signals triggered', weight: '25%', signals: { frequency: { detail: 'HF ratio 0.45 — normal' }, landmark_jitter: { detail: 'Jitter 0.12px — smooth' }, optical_flow: { detail: 'Flow 0.08 — suspicious (static)' }, facial_warping: { detail: 'Edge 0.07 — clean' } } },
      behavior:   { score: 85, status: 'PASS', detail: 'Behavioral score 85/100', weight: '15%', signals: { speed: { detail: '9.1s — normal' }, user_agent: { detail: 'Real browser' }, ip: { detail: 'Public IP' } } },
    },
  },
  video_replay: {
    verdict: 'FRAUD', risk_score: 100, confidence: 99, weighted_score: 0,
    action: 'Block and log incident',
    reason: 'HARD BLOCK: Cryptographic session nonce failed — replay attack prevented',
    layers: {
      face_match: { score: 82, status: 'PASS', detail: 'ArcFace similarity 82.1%', weight: '30%' },
      liveness:   { score: 0,  status: 'FAIL', detail: 'Session nonce invalid — replay attack blocked', weight: '30%', signals: {} },
      deepfake:   { score: 65, status: 'WARN', detail: '2/4 signals triggered', weight: '25%', signals: { frequency: { detail: 'HF ratio 0.52 — normal' }, landmark_jitter: { detail: 'Jitter 0.31px — smooth' }, optical_flow: { detail: 'Flow 0.11 — suspicious' }, facial_warping: { detail: 'Edge 0.09 — clean' } } },
      behavior:   { score: 75, status: 'PASS', detail: 'Behavioral score 75/100', weight: '15%', signals: { speed: { detail: '7.8s — normal' }, user_agent: { detail: 'Real browser' }, ip: { detail: 'VPN-range IP flagged' } } },
    },
  },
  deepfake: {
    verdict: 'FRAUD', risk_score: 95, confidence: 92, weighted_score: 5,
    action: 'Block — deepfake media detected',
    reason: 'HARD BLOCK: 3+ deepfake signals triggered — GAN frequency artifacts; Unnatural landmark jitter 3.74px/f²; Suspicious optical flow',
    layers: {
      face_match: { score: 74, status: 'PASS', detail: 'ArcFace similarity 74.3%', weight: '30%' },
      liveness:   { score: 40, status: 'WARN', detail: 'Liveness score 40/100 — WARN', weight: '30%', signals: { rppg: { detail: 'BPM=38, SNR=0.09 — no pulse' }, glare: { detail: 'Glare 2.1% — normal' }, replay: { detail: 'Duplicate ratio 12% — normal' } } },
      deepfake:   { score: 18, status: 'FAIL', detail: '3/4 signals triggered — FAIL', weight: '25%', signals: { frequency: { detail: 'HF ratio 0.81 — GAN artifacts detected' }, landmark_jitter: { detail: 'Jitter 3.74px — unnatural movement' }, optical_flow: { detail: 'Flow 0.19 — suspicious' }, facial_warping: { detail: 'Edge 0.08 — clean' } } },
      behavior:   { score: 60, status: 'WARN', detail: 'Behavioral score 60/100 — WARN', weight: '15%', signals: { speed: { detail: '6.2s — slightly fast' }, user_agent: { detail: 'Real browser' }, ip: { detail: 'VPN-range IP flagged' } } },
    },
  },
};
