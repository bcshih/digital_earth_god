"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Wraps a 地基主 bid card. On mount the card is "stamped" onto the surface like a
 * vermillion temple seal (印): it slams in from scale ~1.35 → 1 with a slight
 * counter-rotation and a brief glow flash, settling on a spring. Entrances are
 * staggered by `index` so the three street-agents' bids land one after another.
 *
 * Respects prefers-reduced-motion: falls back to a simple opacity fade with no
 * scale/rotation slam and no flash.
 */
export function SealStamp({
  index,
  children,
}: {
  index: number;
  children: React.ReactNode;
}) {
  const reduce = useReducedMotion();
  const delay = index * 0.18;

  if (reduce) {
    return (
      <motion.div
        className="seal-stamp"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: Math.min(delay, 0.4) }}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <motion.div
      className="seal-stamp"
      initial={{ opacity: 0, scale: 1.35, rotate: -6 }}
      animate={{ opacity: 1, scale: 1, rotate: 0 }}
      transition={{
        type: "spring",
        stiffness: 420,
        damping: 18,
        mass: 0.7,
        delay,
      }}
    >
      {/* Vermillion ink-flash that blooms as the seal bites the paper */}
      <motion.span
        className="seal-stamp__flash"
        aria-hidden
        initial={{ opacity: 0, scale: 0.4 }}
        animate={{ opacity: [0, 0.85, 0], scale: [0.4, 1.25, 1.6] }}
        transition={{ duration: 0.55, delay: delay + 0.04, ease: "easeOut" }}
      />
      {children}
    </motion.div>
  );
}

export default SealStamp;
