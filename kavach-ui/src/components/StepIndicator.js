import React from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';

const STEPS = [
  { id: 0, label: 'Upload ID',  icon: '🪪' },
  { id: 1, label: 'Liveness',   icon: '👁' },
  { id: 2, label: 'Analysis',   icon: '🧠' },
  { id: 3, label: 'Result',     icon: '✦' },
];

export default function StepIndicator({ current }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 36 }}>
      {STEPS.map((step, i) => {
        const done   = current > step.id;
        const active = current === step.id;
        return (
          <React.Fragment key={step.id}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
              <motion.div
                animate={active ? { scale: [1, 1.08, 1] } : {}}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                style={{
                  width: 40, height: 40, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  position: 'relative',
                  background: done
                    ? 'linear-gradient(135deg, #059669, #00f5a0)'
                    : active
                    ? 'linear-gradient(135deg, #7c3aed, #0891b2)'
                    : 'rgba(255,255,255,0.04)',
                  border: done
                    ? '1.5px solid rgba(0,245,160,0.5)'
                    : active
                    ? '1.5px solid rgba(139,92,246,0.6)'
                    : '1.5px solid rgba(255,255,255,0.1)',
                  boxShadow: active
                    ? '0 0 0 4px rgba(139,92,246,0.12), 0 0 20px rgba(139,92,246,0.4)'
                    : done
                    ? '0 0 12px rgba(0,245,160,0.3)'
                    : 'none',
                  transition: 'all 0.4s ease',
                }}
              >
                {/* Outer pulse ring for active */}
                {active && (
                  <motion.div
                    animate={{ scale: [1, 1.8], opacity: [0.4, 0] }}
                    transition={{ duration: 1.8, repeat: Infinity }}
                    style={{
                      position: 'absolute', inset: -4,
                      borderRadius: '50%',
                      border: '1px solid rgba(139,92,246,0.5)',
                    }}
                  />
                )}
                {done
                  ? <Check size={15} color="#fff" strokeWidth={3} />
                  : <span style={{
                      fontSize: active ? '1rem' : '0.75rem',
                      color: active ? '#fff' : 'rgba(241,245,255,0.25)',
                      lineHeight: 1,
                    }}>
                      {active ? step.icon : step.id + 1}
                    </span>
                }
              </motion.div>
              <span style={{
                fontSize: '0.67rem',
                fontWeight: active ? 700 : done ? 500 : 400,
                color: active ? '#c4b5fd' : done ? '#6ee7b7' : 'rgba(241,245,255,0.28)',
                letterSpacing: '0.04em',
                whiteSpace: 'nowrap',
              }}>
                {step.label}
              </span>
            </div>

            {i < STEPS.length - 1 && (
              <div style={{ width: 52, height: 1, marginBottom: 24, position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute', inset: 0,
                  background: done
                    ? 'linear-gradient(90deg, #00f5a0, #059669)'
                    : 'rgba(255,255,255,0.07)',
                  transition: 'background 0.5s ease',
                }} />
                {done && (
                  <motion.div
                    initial={{ x: '-100%' }}
                    animate={{ x: '200%' }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: i * 0.3 }}
                    style={{
                      position: 'absolute', inset: 0,
                      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)',
                      width: '40%',
                    }}
                  />
                )}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
