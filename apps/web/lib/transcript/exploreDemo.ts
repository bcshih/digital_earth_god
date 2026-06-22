import type { A2uiMessage } from "@/lib/a2ui/types";

// Canned, contract-accurate transcript (12 messages) sourced from
// docs/explore-demo-transcript.json. CJK text preserved verbatim (UTF-8).
export const exploreDemo: A2uiMessage[] = [
  {
    "version": "v0.9.1",
    "createSurface": {
      "surfaceId": "explore",
      "catalogId": "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
      "sendDataModel": true
    }
  },
  {
    "version": "v0.9.1",
    "updateComponents": {
      "surfaceId": "explore",
      "components": [
        {
          "id": "root",
          "component": "Column",
          "children": [
            "intent-title",
            "intent-sub",
            "intent-field",
            "intent-submit"
          ]
        },
        {
          "id": "intent-title",
          "component": "Text",
          "text": "向土地公稟報你的心願",
          "variant": "h1"
        },
        {
          "id": "intent-sub",
          "component": "Text",
          "text": "五營兵將會將你的凡人語言轉成招標令",
          "variant": "caption"
        },
        {
          "id": "intent-field",
          "component": "TextField",
          "label": "你想找什麼？（例如：安靜的老宅咖啡）",
          "value": {
            "path": "/intent/text"
          },
          "textFieldType": "text"
        },
        {
          "id": "intent-submit-label",
          "component": "Text",
          "text": "上香稟報"
        },
        {
          "id": "intent-submit",
          "component": "Button",
          "child": "intent-submit-label",
          "variant": "primary",
          "checks": [
            {
              "condition": {
                "call": "required",
                "args": {
                  "value": {
                    "path": "/intent/text"
                  }
                }
              },
              "message": "請先說出你的心願"
            }
          ],
          "action": {
            "event": {
              "name": "submit_intent",
              "context": {
                "text": {
                  "path": "/intent/text"
                }
              }
            }
          }
        }
      ]
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/intent",
      "value": {
        "text": "找一間安靜的老宅咖啡"
      }
    }
  },
  {
    "version": "v0.9.1",
    "updateComponents": {
      "surfaceId": "explore",
      "components": [
        {
          "id": "root",
          "component": "Column",
          "children": [
            "broadcast-card",
            "bids-row",
            "verdict-card"
          ]
        },
        {
          "id": "broadcast-card",
          "component": "Card",
          "child": "broadcast-body"
        },
        {
          "id": "broadcast-body",
          "component": "Column",
          "children": [
            "broadcast-title",
            "broadcast-intent"
          ]
        },
        {
          "id": "broadcast-title",
          "component": "Text",
          "text": "土地公發出招標令",
          "variant": "h2"
        },
        {
          "id": "broadcast-intent",
          "component": "Text",
          "text": {
            "path": "/broadcast/intent"
          }
        },
        {
          "id": "bids-row",
          "component": "List",
          "children": {
            "path": "/bids",
            "componentId": "bid-card"
          }
        },
        {
          "id": "bid-card",
          "component": "Card",
          "child": "bid-card-body"
        },
        {
          "id": "bid-card-body",
          "component": "Column",
          "children": [
            "bid-card-street",
            "bid-card-score",
            "bid-card-reason"
          ]
        },
        {
          "id": "bid-card-street",
          "component": "Text",
          "text": {
            "path": "street"
          },
          "variant": "h2"
        },
        {
          "id": "bid-card-score",
          "component": "Text",
          "text": {
            "path": "fitness_score"
          }
        },
        {
          "id": "bid-card-reason",
          "component": "Text",
          "text": {
            "path": "reasoning"
          }
        },
        {
          "id": "verdict-card",
          "component": "Card",
          "child": "verdict-wait"
        },
        {
          "id": "verdict-wait",
          "component": "Text",
          "text": "等待土地公擲筊裁決…",
          "variant": "caption"
        }
      ]
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/broadcast",
      "value": {
        "task_id": "demo01",
        "intent": "find_quiet_cafe",
        "constraints": [
          "安靜",
          "老宅",
          "咖啡"
        ],
        "lat": 22.9971,
        "lng": 120.201
      }
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/bids",
      "value": []
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/bids/0",
      "value": {
        "agent_id": "street_shennong_node",
        "street": "神農街",
        "fitness_score": 9.1,
        "reasoning": "神農街老屋林立，午後人稀，最適合安靜品一杯老宅咖啡。巷弄裡的時光彷彿靜止。",
        "tags": [
          "安靜",
          "老宅",
          "咖啡"
        ],
        "sensor": "人流稀少，晴天28°C",
        "social": "#神農街咖啡 近七日熱搜38次",
        "candidate_pois": [
          {
            "name": "未艾公寓",
            "category": "cafe",
            "lat": 22.9971,
            "lng": 120.201,
            "tags": [
              "安靜",
              "老宅",
              "咖啡"
            ],
            "note": "老屋改建，二樓採光極佳"
          }
        ]
      }
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/bids/1",
      "value": {
        "agent_id": "street_haian_node",
        "street": "海安路",
        "fitness_score": 7.4,
        "reasoning": "海安路藝術氣息濃厚，雖然傍晚人潮漸增，但白日仍有靜謐角落可坐。",
        "tags": [
          "藝術",
          "咖啡"
        ],
        "sensor": "人流中等，晴天29°C",
        "social": "#海安路藝術 熱搜61次",
        "candidate_pois": [
          {
            "name": "藍晒圖咖啡",
            "category": "cafe",
            "lat": 22.9925,
            "lng": 120.1985,
            "tags": [
              "藝術",
              "咖啡"
            ],
            "note": "藝術街區旁，工業風"
          }
        ]
      }
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/bids/2",
      "value": {
        "agent_id": "street_zhengxing_node",
        "street": "正興街",
        "fitness_score": 6.2,
        "reasoning": "正興街美食雲集熱鬧滾滾，雖非最安靜，但人情味十足，咖啡香處處。",
        "tags": [
          "美食",
          "熱鬧",
          "咖啡"
        ],
        "sensor": "人流較多，多雲27°C",
        "social": "#正興街 必吃熱搜52次",
        "candidate_pois": [
          {
            "name": "蜷尾家",
            "category": "cafe",
            "lat": 22.9938,
            "lng": 120.1972,
            "tags": [
              "美食",
              "熱鬧",
              "咖啡"
            ],
            "note": "排隊名店，氣氛熱絡"
          }
        ]
      }
    }
  },
  {
    "version": "v0.9.1",
    "updateComponents": {
      "surfaceId": "explore",
      "components": [
        {
          "id": "verdict-card",
          "component": "Card",
          "child": "verdict-body"
        },
        {
          "id": "verdict-body",
          "component": "Column",
          "children": [
            "verdict-title",
            "verdict-street",
            "verdict-text"
          ]
        },
        {
          "id": "verdict-title",
          "component": "Text",
          "text": "土地公的裁決",
          "variant": "h1"
        },
        {
          "id": "verdict-street",
          "component": "Text",
          "text": {
            "path": "/verdict/winner_street"
          },
          "variant": "h2"
        },
        {
          "id": "verdict-text",
          "component": "Text",
          "text": {
            "path": "/verdict/recommendation"
          }
        }
      ]
    }
  },
  {
    "version": "v0.9.1",
    "updateDataModel": {
      "surfaceId": "explore",
      "path": "/verdict",
      "value": {
        "winner_agent_id": "street_shennong_node",
        "winner_street": "神農街",
        "recommendation": "土地公掐指一算，擲筊三聖——就是神農街了！去未艾公寓二樓，揀個窗邊位，讓老屋的光陪你把整個下午都泡進咖啡裡。",
        "reasoning": "三方投標，神農街分數最高(9.1)，安靜與老宅意象最合心願，人情味亦足。海安、正興各有風采，留待他日。",
        "ranked_agent_ids": [
          "street_shennong_node",
          "street_haian_node",
          "street_zhengxing_node"
        ],
        "recommended_pois": [
          {
            "name": "未艾公寓",
            "category": "cafe",
            "lat": 22.9971,
            "lng": 120.201,
            "tags": [
              "安靜",
              "老宅"
            ],
            "note": "老屋改建，二樓採光極佳"
          }
        ]
      }
    }
  },
  {
    "a2uiDone": true
  }
] as A2uiMessage[];
