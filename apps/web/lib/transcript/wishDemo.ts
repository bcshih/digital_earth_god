import type { A2uiMessage } from "@/lib/a2ui/types";

// Canned, contract-accurate transcript for the offline /wish ritual.
// Mirrors the gateway's /ws/wish/a2ui frame order:
//   createSurface(wish, sendDataModel) → updateComponents(wish input) →
//   /wish data → updateComponents(blessing) → /blessing data → a2uiDone.
// Component ids/paths match deg/a2ui/surfaces.py exactly. CJK preserved (UTF-8).
export const wishDemo: A2uiMessage[] = [
  {
    version: "v0.9.1",
    createSurface: {
      surfaceId: "wish",
      catalogId:
        "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
      sendDataModel: true,
    },
  },
  {
    version: "v0.9.1",
    updateComponents: {
      surfaceId: "wish",
      components: [
        {
          id: "root",
          component: "Column",
          children: ["wish-title", "wish-sub", "wish-field", "wish-submit"],
        },
        {
          id: "wish-title",
          component: "Text",
          text: "向土地公上香許願",
          variant: "h1",
        },
        {
          id: "wish-sub",
          component: "Text",
          text: "說出你對這座城市的心願，土地公會聽見",
          variant: "caption",
        },
        {
          id: "wish-field",
          component: "TextField",
          label: "你的心願（例如：希望海安路多裝路燈）",
          value: { path: "/wish/text" },
          textFieldType: "text",
        },
        { id: "wish-submit-label", component: "Text", text: "上香許願" },
        {
          id: "wish-submit",
          component: "Button",
          child: "wish-submit-label",
          variant: "primary",
          checks: [
            {
              condition: {
                call: "required",
                args: { value: { path: "/wish/text" } },
              },
              message: "請先說出你的心願",
            },
          ],
          action: {
            event: {
              name: "submit_wish",
              context: { text: { path: "/wish/text" } },
            },
          },
        },
      ],
    },
  },
  {
    version: "v0.9.1",
    updateDataModel: {
      surfaceId: "wish",
      path: "/wish",
      value: { text: "希望神農街的老房子可以被好好保存" },
    },
  },
  {
    version: "v0.9.1",
    updateComponents: {
      surfaceId: "wish",
      components: [
        { id: "root", component: "Column", children: ["blessing-card"] },
        { id: "blessing-card", component: "Card", child: "blessing-body" },
        {
          id: "blessing-body",
          component: "Column",
          children: [
            "blessing-title",
            "blessing-ack",
            "blessing-text",
            "blessing-cat",
          ],
        },
        {
          id: "blessing-title",
          component: "Text",
          text: "土地公的祝福",
          variant: "h1",
        },
        {
          id: "blessing-ack",
          component: "Text",
          text: { path: "/blessing/acknowledgment" },
        },
        {
          id: "blessing-text",
          component: "Text",
          text: { path: "/blessing/blessing" },
          variant: "h2",
        },
        {
          id: "blessing-cat",
          component: "Text",
          text: { path: "/blessing/category" },
          variant: "caption",
        },
      ],
    },
  },
  {
    version: "v0.9.1",
    updateDataModel: {
      surfaceId: "wish",
      path: "/blessing",
      value: {
        acknowledgment:
          "你的心願，土地公收下了。神農街的一磚一瓦，老街坊們也都掛在心上。",
        blessing:
          "願老屋的簷角繼續遮風擋雨，舊時光不被推土機驚醒；待你他日再訪，巷弄依舊飄著它原本的味道。土地公會替這條街多看顧幾分。",
        category: "分類：社區營造",
      },
    },
  },
  { a2uiDone: true },
] as A2uiMessage[];
