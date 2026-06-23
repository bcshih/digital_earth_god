"use client";

import { useEffect, useState } from "react";
import { SealStamp } from "./theater/SealStamp";
import { motion, AnimatePresence } from "motion/react";

interface Bid {
  street: string;
  fitness_score: string;
  reasoning: string;
}

interface Debate {
  street: string;
  debate_text: string;
}

interface Props {
  bids: Bid[];
  debates: Debate[];
}

export function NegotiationBoard({ bids = [], debates = [] }: Props) {
  const [currentRound, setCurrentRound] = useState<1 | 2>(1);

  // Auto-switch to round 2 when debates arrive
  useEffect(() => {
    if (debates.length > 0) {
      setCurrentRound(2);
    }
  }, [debates.length]);

  if (bids.length === 0 && debates.length === 0) {
    return (
      <div className="negotiation-board a2-card">
        <span className="a2-card__corner a2-card__corner--tl" aria-hidden />
        <span className="a2-card__corner a2-card__corner--tr" aria-hidden />
        <span className="a2-card__corner a2-card__corner--bl" aria-hidden />
        <span className="a2-card__corner a2-card__corner--br" aria-hidden />
        <div className="a2-card__body">
          <p className="a2-text" style={{ textAlign: "center", opacity: 0.5 }}>正在等候地基主投標...</p>
        </div>
      </div>
    );
  }

  const isRound2 = currentRound === 2 && debates.length > 0;
  const items = isRound2 ? debates : bids;
  const maxRounds = debates.length > 0 ? 2 : 1;

  return (
    <div className="negotiation-board a2-card">
      <span className="a2-card__corner a2-card__corner--tl" aria-hidden />
      <span className="a2-card__corner a2-card__corner--tr" aria-hidden />
      <span className="a2-card__corner a2-card__corner--bl" aria-hidden />
      <span className="a2-card__corner a2-card__corner--br" aria-hidden />
      
      <div className="a2-card__body negotiation-board__body">
        <div className="negotiation-board__list">
          <AnimatePresence mode="popLayout">
            {items.map((item: any, i) => (
              <motion.div
                key={`${isRound2 ? "debate" : "bid"}-${item.street}`}
                className="negotiation-row"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <div className="negotiation-row__left">
                  <SealStamp index={i}>
                    <div className="negotiation-row__name">{item.street}</div>
                    {!isRound2 && item.fitness_score && (
                      <div className="negotiation-row__score">
                        <span className="negotiation-row__score-bar" />
                        {item.fitness_score}
                      </div>
                    )}
                  </SealStamp>
                </div>
                <div className="negotiation-row__right">
                  <p className="a2-text">
                    {isRound2 ? item.debate_text : item.reasoning}
                  </p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {maxRounds > 1 && (
          <div className="negotiation-board__pagination">
            <button
              className="negotiation-board__btn"
              onClick={() => setCurrentRound(1)}
              disabled={currentRound === 1}
            >
              {"<"}
            </button>
            <span className="negotiation-board__page-text">
              輪次 {currentRound}/{maxRounds}
            </span>
            <button
              className="negotiation-board__btn"
              onClick={() => setCurrentRound(2)}
              disabled={currentRound === 2}
            >
              {">"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
