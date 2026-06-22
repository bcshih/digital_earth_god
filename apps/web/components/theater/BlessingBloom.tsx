"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Wraps the 土地公 blessing card. Where the exploration 擲筊 is a tense contest,
 * a blessing is calm grace: the card rises softly and a warm golden bloom
 * breathes out from behind it, like incense catching the light. No slam, no
 * burst — just a slow, reassuring glow that settles.
 *
 * Respects prefers-reduced-motion: a plain opacity fade, no bloom animation.
 */
export function BlessingBloom({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();

  if (reduce) {
    return (
      <motion.div
        className="blessing-bloom"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      >
        <span className="blessing-bloom__glow blessing-bloom__glow--static" aria-hidden />
        {children}
      </motion.div>
    );
  }

  return (
    <motion.div
      className="blessing-bloom"
      initial={{ opacity: 0, y: 16, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 120, damping: 24, mass: 0.9 }}
    >
      {/* Warm golden bloom breathing out from behind the card */}
      <motion.span
        className="blessing-bloom__glow"
        aria-hidden
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: [0, 0.85, 0.5], scale: [0.6, 1.25, 1.4] }}
        transition={{ duration: 2.2, ease: "easeOut", times: [0, 0.55, 1] }}
      />
      {/* A second, slower breathing halo so the grace lingers */}
      <motion.span
        className="blessing-bloom__halo"
        aria-hidden
        animate={{ opacity: [0.18, 0.4, 0.18], scale: [1, 1.06, 1] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1.4 }}
      />
      {children}
    </motion.div>
  );
}

export default BlessingBloom;
