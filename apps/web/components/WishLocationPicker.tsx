"use client";

import dynamic from "next/dynamic";

const Inner = dynamic(() => import("./WishLocationPickerInner"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        width: "100%",
        height: "220px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "12px",
        color: "var(--color-dim, #888)",
        border: "1px dashed currentColor",
      }}
    >
      展開地圖中…
    </div>
  ),
});

export function WishLocationPicker({
  lat,
  lng,
  onChange,
}: {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
}) {
  return <Inner lat={lat} lng={lng} onChange={onChange} />;
}

export default WishLocationPicker;
