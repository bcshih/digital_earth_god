"use client";

import { useMemo } from "react";
import { motion, useReducedMotion } from "motion/react";

/**
 * Ambient ritual layer. Drifting incense smoke rising from the temple floor,
 * over the gold/vermillion radial glows already painted on the ink base in
 * globals.css. This *complements* those glows (it does not repaint them): it
 * adds slow vertical smoke wisps + two breathing censer halos so the sanctum
 * feels alive without competing with foreground content.
 *
 * Sits behind everything (z-index 0); children render above on z-index 1.
 * Respects prefers-reduced-motion: smoke + breathing halos freeze to a static,
 * faint haze.
 */

type Wisp = {
  left: number; // vw
  delay: number; // s
  duration: number; // s
  drift: number; // px lateral sway
  width: number; // px
  hue: "gold" | "vermillion";
};

// Deterministic pseudo-random so SSR markup matches the client (no hydration
// mismatch) — a tiny LCG seeded by index.
function makeWisps(count: number): Wisp[] {
  let seed = 0x2f9a3b1;
  const rnd = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  return Array.from({ length: count }, (_, i) => ({
    left: 4 + rnd() * 92,
    delay: rnd() * 14,
    duration: 13 + rnd() * 12,
    drift: (rnd() - 0.5) * 90,
    width: 60 + rnd() * 120,
    hue: i % 3 === 0 ? "vermillion" : "gold",
  }));
}

export function IncenseBackground({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  const wisps = useMemo(() => makeWisps(14), []);

  return (
    <div className="incense">
      <div className="incense__field" aria-hidden>
        {/* Two slow-breathing censer halos */}
        <motion.span
          className="incense__halo incense__halo--gold"
          animate={reduce ? undefined : { opacity: [0.18, 0.4, 0.18], scale: [1, 1.08, 1] }}
          transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.span
          className="incense__halo incense__halo--vermillion"
          animate={reduce ? undefined : { opacity: [0.12, 0.28, 0.12], scale: [1.05, 1, 1.05] }}
          transition={{ duration: 11, repeat: Infinity, ease: "easeInOut", delay: 2 }}
        />

        {/* Rising smoke wisps */}
        {!reduce &&
          wisps.map((w, i) => (
            <motion.span
              key={i}
              className={`incense__wisp incense__wisp--${w.hue}`}
              style={{ left: `${w.left}vw`, width: w.width }}
              initial={{ y: "12vh", x: 0, opacity: 0, scaleY: 0.6 }}
              animate={{
                y: "-96vh",
                x: [0, w.drift, w.drift * 0.4],
                opacity: [0, 0.5, 0.36, 0],
                scaleY: [0.6, 1.15, 1.5],
              }}
              transition={{
                duration: w.duration,
                delay: w.delay,
                repeat: Infinity,
                ease: "easeOut",
              }}
            />
          ))}
      </div>

      <div className="incense__content">{children}</div>
    </div>
  );
}

export default IncenseBackground;
