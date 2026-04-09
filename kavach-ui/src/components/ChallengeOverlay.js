import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

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

export default function ChallengeOverlay({
  challenge, challenges, completedGestures = [],
  currentIdx = 0, timeLeft, isRecording
}) {
  const allChallenges = challenges || [challenge];
  const currentKey    = allChallenges[currentIdx] || challenge;
  const info          = CHALLENGES[currentKey] || { emoji: '◎', text: currentKey, hint: 'Follow the instruction' };
  const urgent        = timeLeft !== null && timeLeft <= 10;

  // Time left for current gesture (each gets 10s)
  const gestureTimeLeft = timeLeft !== null
    ? Math.max(0, 10 - (((45 - timeLeft)) % 10))
    : null;

  return (
    <>
      {/* Face bounding box */}
      <div className="face-box">
        <div className="face-corner tl" /><div className="face-corner tr" />
        <div className="face-corner bl" /><div className="face-corner br" />
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
        background: 'linear-gradient(to top, rgba(3,5,15,0.98) 0%, rgba(3,5,15,0.8) 65%, transparent 100%)',
        padding: '16px 14px 14px',
        borderRadius: '0 0 calc(var(--r-lg) - 1px) calc(var(--r-lg) - 1px)',
        zIndex: 4,
      }}>

        {/* Recording + timer row */}
        {isRecording && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <motion.div
              animate={{ opacity: [1, 0.15, 1] }}
              transition={{ duration: 0.9, repeat: Infinity }}
              style={{ width: 7, height: 7, borderRadius: '50%', background: '#f43f5e', flexShrink: 0 }}
            />
            <span style={{ fontSize: '0.65rem', color: '#f43f5e', fontWeight: 700, letterSpacing: '0.14em' }}>REC</span>
            <div style={{ flex: 1 }} />
            {timeLeft !== null && (
              <span style={{
                fontSize: '0.75rem', fontWeight: 700,
                color: urgent ? '#f43f5e' : 'rgba(241,245,255,0.6)',
              }}>
                Total: {timeLeft}s
              </span>
            )}
          </div>
        )}

        {/* Sequential gesture progress steps */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
          {allChallenges.map((c, i) => {
            const ci        = CHALLENGES[c] || { emoji: '◎', text: c };
            const isDone    = i < currentIdx;
            const isCurrent = i === currentIdx;
            return (
              <React.Fragment key={i}>
                <motion.div
                  animate={isCurrent ? { scale: [1, 1.05, 1] } : {}}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 5, flex: isCurrent ? 2 : 1,
                    background: isDone
                      ? 'rgba(0,245,160,0.15)'
                      : isCurrent
                      ? 'rgba(139,92,246,0.25)'
                      : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${isDone ? 'rgba(0,245,160,0.4)' : isCurrent ? 'rgba(139,92,246,0.5)' : 'rgba(255,255,255,0.08)'}`,
                    borderRadius: 8, padding: '5px 8px',
                    transition: 'all 0.4s ease',
                  }}
                >
                  <span style={{ fontSize: '0.8rem' }}>
                    {isDone ? '✓' : ci.emoji}
                  </span>
                  <span style={{
                    fontSize: '0.62rem',
                    fontWeight: isCurrent ? 700 : 400,
                    color: isDone ? '#00f5a0' : isCurrent ? '#c4b5fd' : 'rgba(241,245,255,0.3)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {isDone ? 'Done' : isCurrent ? ci.text : `${i + 1}. ${ci.text}`}
                  </span>
                </motion.div>
                {i < allChallenges.length - 1 && (
                  <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.7rem', flexShrink: 0 }}>›</span>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Current active challenge card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentKey}
            initial={{ opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            style={{
              background: 'rgba(139,92,246,0.18)',
              border: '1px solid rgba(139,92,246,0.4)',
              borderRadius: 14, padding: '10px 14px',
              display: 'flex', alignItems: 'center', gap: 12,
              backdropFilter: 'blur(16px)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
            }}
          >
            {/* Gesture icon with countdown ring */}
            <div style={{ position: 'relative', flexShrink: 0 }}>
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                style={{
                  width: 42, height: 42, borderRadius: 12,
                  background: 'rgba(139,92,246,0.25)',
                  border: '1.5px solid rgba(139,92,246,0.5)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '1.2rem',
                }}
              >
                {info.emoji}
              </motion.div>
              {/* Gesture timer badge */}
              {gestureTimeLeft !== null && (
                <div style={{
                  position: 'absolute', top: -6, right: -6,
                  width: 18, height: 18, borderRadius: '50%',
                  background: gestureTimeLeft <= 3 ? '#f43f5e' : '#8b5cf6',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.55rem', fontWeight: 800, color: '#fff',
                }}>
                  {gestureTimeLeft}
                </div>
              )}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                <span style={{
                  fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.1em',
                  color: '#a78bfa', textTransform: 'uppercase',
                }}>
                  Step {currentIdx + 1} of {allChallenges.length}
                </span>
              </div>
              <div style={{ fontWeight: 700, fontSize: '0.92rem', color: '#f1f5ff', marginBottom: 2 }}>
                {info.text}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'rgba(241,245,255,0.5)', lineHeight: 1.4 }}>
                {info.hint}
              </div>
            </div>

            {/* AI bars */}
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
        </AnimatePresence>
      </div>

      {/* Top label */}
      <div style={{
        position: 'absolute', top: 14, left: 0, right: 0,
        display: 'flex', justifyContent: 'center', zIndex: 4, pointerEvents: 'none',
      }}>
        <div style={{
          background: 'rgba(3,5,15,0.75)', border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: 999, padding: '4px 14px', backdropFilter: 'blur(12px)',
          display: 'flex', alignItems: 'center', gap: 7,
        }}>
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{ width: 5, height: 5, borderRadius: '50%', background: '#67e8f9' }}
          />
          <span style={{ fontSize: '0.63rem', color: '#67e8f9', fontWeight: 600, letterSpacing: '0.1em' }}>
            AI SCANNING — STEP {currentIdx + 1}/{allChallenges.length}
          </span>
        </div>
      </div>
    </>
  );
}
