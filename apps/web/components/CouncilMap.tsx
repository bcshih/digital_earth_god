"use client";

import dynamic from "next/dynamic";

export type CouncilBoundary = {
  agent_id: string;
  street_name: string;
  centroid: { lat: number; lng: number };
  polygon: [number, number][]; // [lat, lng] ring
};

export type CouncilStatementRow = {
  agent_id: string;
  street_name: string;
  round: number;
  stance: "support" | "oppose" | "question" | "inform" | "silent";
  responds_to: string | null;
  statement_text: string;
};

export type CouncilAlignmentRow = {
  agent_id: string;
  street_name: string;
  final_stance: "support" | "oppose" | "question" | "inform" | "silent";
};

/**
 * Reactive 里長大會 map. Leaflet touches `window` at module scope, so the real
 * map (CouncilMapInner) loads ONLY on the client via next/dynamic { ssr: false }.
 */
const MapInner = dynamic(() => import("./CouncilMapInner"), {
  ssr: false,
  loading: () => (
    <div className="result-map result-map--loading" aria-hidden>
      <span className="result-map__loading-text">展開神界輿圖…</span>
    </div>
  ),
});

export function CouncilMap({
  boundaries,
  statements,
  alignments,
}: {
  boundaries: CouncilBoundary[];
  statements: CouncilStatementRow[];
  alignments: CouncilAlignmentRow[];
}) {
  if (!boundaries || boundaries.length === 0) return null;
  return (
    <MapInner
      boundaries={boundaries}
      statements={statements}
      alignments={alignments}
    />
  );
}

export default CouncilMap;
