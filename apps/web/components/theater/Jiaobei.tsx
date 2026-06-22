"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

/**
 * 擲筊 — the divination ritual that gates the verdict. Two crescent moon-blocks
 * (筊杯) are tossed (rotate + arc up, spring) and settle to 聖筊 (a holy cast:
 * one block flat-side up, one round-side up — meaning "yes, the gods approve").
 * A gold burst flashes, then the verdict (children) is revealed beneath.
 *
 * Plays once, when the verdict first appears. Respects prefers-reduced-motion:
 * skips the toss entirely and fades the verdict straight in.
 */

type Phase = "toss" | "settle" | "reveal";

function Crescent({
  flat,
  side,
}: {
  flat: boolean; // settled face: true = 陰(flat up), false = 陽(round up)
  side: "left" | "right";
}) {
  // 聖筊 = one of each. The block face is hinted by gradient + a notch.
  return (
    <div className={`jiaobei__block jiaobei__block--${side}`} data-flat={flat} aria-hidden>
      <div className="jiaobei__block-face" />
    </div>
  );
}

export function Jiaobei({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  const [phase, setPhase] = useState<Phase>(reduce ? "reveal" : "toss");

  useEffect(() => {
    // Reduced motion already initialises phase to "reveal" — nothing to schedule.
    if (reduce) return;
    const t1 = setTimeout(() => setPhase("settle"), 950);
    const t2 = setTimeout(() => setPhase("reveal"), 1750);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [reduce]);

  // Reduced motion: no theater, just the verdict.
  if (reduce) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
        {children}
      </motion.div>
    );
  }

  const tossing = phase === "toss";
  const settled = phase !== "toss";

  return (
    <div className="jiaobei">
      <AnimatePresence>
        {phase !== "reveal" && (
          <motion.div
            className="jiaobei__stage"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ duration: 0.45, ease: "easeIn" }}
          >
            <span className="jiaobei__kicker">土地公擲筊問神…</span>

            <div className="jiaobei__pair">
              {/* Left block: settles round-up (陽) */}
              <motion.div
                className="jiaobei__toss"
                animate={
                  tossing
                    ? { y: [-4, -120, 0], rotate: [0, -380, -360] }
                    : { y: 0, rotate: -360 }
                }
                transition={
                  tossing
                    ? { duration: 0.95, ease: "easeOut" }
                    : { type: "spring", stiffness: 300, damping: 14 }
                }
              >
                <Crescent flat={false} side="left" />
              </motion.div>

              {/* Right block: settles flat-up (陰) → together = 聖筊 */}
              <motion.div
                className="jiaobei__toss"
                animate={
                  tossing
                    ? { y: [-4, -150, 0], rotate: [0, 420, 360] }
                    : { y: 0, rotate: 360 }
                }
                transition={
                  tossing
                    ? { duration: 0.95, ease: "easeOut", delay: 0.06 }
                    : { type: "spring", stiffness: 300, damping: 14, delay: 0.06 }
                }
              >
                <Crescent flat={true} side="right" />
              </motion.div>
            </div>

            {/* Gold burst on the holy cast */}
            <AnimatePresence>
              {settled && (
                <motion.span
                  className="jiaobei__burst"
                  aria-hidden
                  initial={{ opacity: 0, scale: 0.3 }}
                  animate={{ opacity: [0, 0.9, 0], scale: [0.3, 1.7, 2.3] }}
                  transition={{ duration: 0.9, ease: "easeOut" }}
                />
              )}
            </AnimatePresence>

            <AnimatePresence>
              {settled && (
                <motion.span
                  className="jiaobei__verdict-word"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.18, duration: 0.5 }}
                >
                  聖筊 · 神准
                </motion.span>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>

      {phase === "reveal" && (
        <motion.div
          initial={{ opacity: 0, y: 18, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 180, damping: 22 }}
        >
          {children}
        </motion.div>
      )}
    </div>
  );
}

export default Jiaobei;
