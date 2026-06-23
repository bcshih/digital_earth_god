import React from "react";

interface ChatBubbleProps {
  children: React.ReactNode;
}

export function ChatBubble({ children }: ChatBubbleProps) {
  return (
    <div className="chat-bubble-wrapper">
      <div className="chat-avatar">
        <span>神</span>
      </div>
      <div className="chat-bubble">
        {children}
      </div>
    </div>
  );
}
