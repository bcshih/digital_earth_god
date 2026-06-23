"use client";

import Link from "next/link";

/**
 * A small temple-plaque header that lets the demo flow between the three halls:
 * 探索 (explore) · 許願 (wish) · 儀表板 (dashboard). Styled like a carved gold
 * sign-board hung above the sanctum gate; the active hall glows.
 */
const HALLS: { key: string; href: string; label: string; glyph: string }[] = [
  { key: "explore", href: "/", label: "探索", glyph: "探" },
  { key: "wish", href: "/wish", label: "許願", glyph: "願" },
  { key: "ask", href: "/ask", label: "問土地公", glyph: "問" },
  { key: "council", href: "/council", label: "里長大會", glyph: "會" },
  { key: "dashboard", href: "/dashboard", label: "儀表板", glyph: "卦" },
];

export function TempleNav({ active }: { active: "explore" | "wish" | "ask" | "council" | "dashboard" }) {
  return (
    <nav className="temple-nav" aria-label="土地公廟 · 三殿">
      <span className="temple-nav__plaque" aria-hidden>
        土地公廟
      </span>
      <ul className="temple-nav__halls">
        {HALLS.map((h) => (
          <li key={h.key}>
            <Link
              href={h.href}
              className="temple-nav__hall"
              data-active={h.key === active}
              aria-current={h.key === active ? "page" : undefined}
            >
              <span className="temple-nav__glyph">{h.glyph}</span>
              <span className="temple-nav__label">{h.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export default TempleNav;
