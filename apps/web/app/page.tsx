import Link from "next/link";

export default function Home() {
  return (
    <main className="sanctum">
      <div className="sanctum__brand">
        <span className="sanctum__seal">土</span>
        <span className="sanctum__kicker">數位土地公 · Divine-Tech A2UI</span>
      </div>

      <h1 className="sanctum__hero">夜廟之中，眾街擲筊</h1>
      <p className="sanctum__lede">
        凡人的一句心願，化作土地公的招標令；三方地基主競標獻策，土地公擲筊裁決。
        這是一個 A2UI 標準串流的參考渲染器——可被任何第三方前端替換。神・科技。
      </p>

      <Link className="sanctum__cta" href="/demo">
        進入展演 · ENTER THE DEMO →
      </Link>

      <p
        className="a2-text--caption"
        style={{ marginTop: "2.6rem", lineHeight: 1.9 }}
      >
        Live mode (WebSocket /ws/explore/a2ui) arrives in Task 4. The /demo route
        replays a canned, contract-accurate transcript fully offline.
      </p>
    </main>
  );
}
