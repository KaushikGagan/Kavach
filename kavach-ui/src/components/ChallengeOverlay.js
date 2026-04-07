import React from 'react';
import { motion } from 'framer-motion';

const CHALLENGES = {
  blink_twice:        { emoji: '👁',  text: 'Blink Twice',       hint: 'Blink both eyes twice slowly' },
  turn_left:          { emoji: '←',   text: 'Turn Head Left',    hint: 'Slowly turn your head to the left' },
  turn_right:         { emoji: '→',   text: 'Turn Head Right',   hint: 'Slowly turn your head to the right' },
  open_mouth:         { emoji: '○',   text: 'Open Your Mouth',   hint: 'Open your mouth wide for 2 seconds' },
  look_up:            { emoji: '↑',   text: 'Look Up',           hint: 'Look upward for 2 seconds' },
  show_three_fingers: { emoji: '✋',  text: 'Show 3 Fingers',    hint: 'Hold up 3 fingers to the camera' },
  touch_nose:         { emoji: '↓',   text: 'Touch Your Nose',   hint: 'Touch the tip of your nose' },
  smile:              { emoji: '◡',   text: 'Smile Naturally',   hint: 'Give a relaxed, natural smile' },
};

export default function ChallengeOverlay({ challenge, timeLeft, isRecording }) {
  const info = CHALLENGES[challenge] || { emoji: '◎', text: challenge, hint: 'Follow the instruction' };
  const urgent = timeLeft !== null && timeLeft <= 5;

  return (
    <>
      {/* Face bounding box with glowing corners */}
      <div className="face-box">
        <div className="face-corner tl" />
        <div className="face-corner tr" />
        <div className="face-corner bl" />
        <div className="face-corner br" />
        {/* Center crosshair dot */}
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4], scale: [1, 1.3, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{
            position: 'absolute', top: '50%', left: '50%',
            transform: 'translate(-50%,-50%)',
            width: 6, height: 6, borderRadius: '50%',
            background: 'rgba(0,245,160,0.8)',
            boxShadow: '0 0 10px rgba(0,245,160,0.8)',
          }}
        />
      </div>

      {/* Bottom overlay */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: 'linear-gradient(to top, rgba(3,5,15,0.97) 0%, rgba(3,5,15,0.75) 60%, transparent 100%)',
        padding: '24px 16px 18px',
        borderRadius: '0 0 calc(var(--r-lg) - 1px) calc(var(--r-lg) - 1px)',
        zIndex: 4,
      }}>
        {/* Recording row */}
        {isRecording && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <motion.div
              animate={{ opacity: [1, 0.15, 1] }}
              transition={{ duration: 0.9, repeat: Infinity }}
              style={{ width: 7, height: 7, borderRadius: '50%', background: '#f43f5e', flexShrink: 0 }}
            />
            <span style={{ fontSize: '0.65rem', color: '#f43f5e', fontWeight: 700, letterSpacing: '0.14em' }}>
              REC
            </span>
            <div style={{ flex: 1 }} />
            {timeLeft !== null && (
              <motion.span
                animate={urgent ? { scale: [1, 1.1, 1] } : {}}
                transition={{ duration: 0.5, repeat: Infinity }}
                style={{
                  fontSize: '0.82rem', fontWeight: 800,
                  color: urgent ? '#f43f5e' : '#f1f5ff',
                  fontVariantNumeric: 'tabular-nums',
                  fontFamily: "'Space Grotesk', sans-serif",
                }}
              >
                {timeLeft}s
              </motion.span>
            )}
          </div>
        )}

        {/* Challenge instruction card */}
        <motion.div
          key={challenge}
          initial={{ opacity: 0, y: 12, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          style={{
            background: 'rgba(139,92,246,0.15)',
            border: '1px solid rgba(139,92,246,0.35)',
            borderRadius: 14,
            padding: '11px 16px',
            display: 'flex', alignItems: 'center', gap: 14,
            backdropFilter: 'blur(16px)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08)',
          }}
        >
          <motion.div
            animate={{ scale: [1, 1.12, 1] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
            style={{
              width: 38, height: 38, borderRadius: 10, flexShrink: 0,
              background: 'rgba(139,92,246,0.2)',
              border: '1px solid rgba(139,92,246,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.1rem', color: '#c4b5fd',
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
            }}
          >
            {info.emoji}
          </motion.div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: '0.88rem', color: '#c4b5fd', marginBottom: 2 }}>
              {info.text}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'rgba(241,245,255,0.45)', lineHeight: 1.4 }}>
              {info.hint}
            </div>
          </div>
          {/* AI indicator */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
            {[0,1,2].map(i => (
              <motion.div key={i}
                animate={{ scaleY: [0.4, 1, 0.4] }}
                transition={{ duration: 0.8, delay: i * 0.15, repeat: Infinity }}
                style={{ width: 3, height: 10, borderRadius: 2, background: '#8b5cf6', transformOrigin: 'center' }}
              />
            ))}
          </div>
        </motion.div>
      </div>

      {/* Top overlay — AI scanning label */}
      <div style={{
        position: 'absolute', top: 14, left: 0, right: 0,
        display: 'flex', justifyContent: 'center',
        zIndex: 4, pointerEvents: 'none',
      }}>
        <div style={{
          background: 'rgba(3,5,15,0.7)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 999, padding: '4px 14px',
          backdropFilter: 'blur(12px)',
          display: 'flex', alignItems: 'center', gap: 7,
        }}>
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{ width: 5, height: 5, borderRadius: '50%', background: '#67e8f9' }}
          />
          <span style={{ fontSize: '0.63rem', color: '#67e8f9', fontWeight: 600, letterSpacing: '0.1em' }}>
            AI SCANNING
          </span>
        </div>
      </div>
    </>
  );
}
