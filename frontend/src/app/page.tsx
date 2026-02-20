"use client";
import { useState, useRef, useEffect } from "react";

type Message = {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: Date;
};

export default function ChatClient() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setIsTyping(true);

    try {
      const res = await fetch(`/api/chat?question=${encodeURIComponent(input)}`);
      const data = await res.json();
      
      setIsTyping(false);
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "bot",
        text: data.answer || "I couldn't process that request.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      setIsTyping(false);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: "bot",
        text: "Error fetching response. Please check if the backend server is running.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div>
      {/* Top Bar */}
      <div className="top-bar">
        <div className="logo">IIT BHILAI RAG</div>
        <div className="info-text">Powered by Ollama • Gemini Embeddings</div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Chat Container - Main area */}
        <div className="chat-container">
          {/* Messages Area */}
          <div className="messages-area">
            {messages.length === 0 ? (
              <div style={{ 
                display: "flex", 
                flexDirection: "column", 
                alignItems: "center", 
                justifyContent: "center", 
                height: "100%",
                color: "#7a7a8a",
                textAlign: "center",
                padding: "40px"
              }}>
                <div style={{ fontSize: "48px", marginBottom: "16px" }}>💬</div>
                <h3 style={{ fontSize: "16px", marginBottom: "8px", color: "#c0c0d0" }}>Welcome to IIT Bhilai RAG</h3>
                <p style={{ fontSize: "13px" }}>Ask me anything about IIT Bhilai</p>
                <p style={{ fontSize: "11px", marginTop: "8px" }}>Courses • Admissions • Campus • Faculty</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`message-row ${msg.sender}`}>
                  <div className="message-bubble">
                    <div className="message-header">
                      <span>{msg.sender === "user" ? "You" : "Assistant"}</span>
                    </div>
                    {msg.text}
                  </div>
                </div>
              ))
            )}
            {isTyping && (
              <div className="message-row bot">
                <div className="typing-indicator">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="input-area">
            <div className="input-wrapper">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask something about IIT Bhilai..."
                disabled={loading}
                className="input-field"
                rows={1}
                style={{ resize: "none" }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = Math.min(target.scrollHeight, 120) + "px";
                }}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="send-button"
              >
                {loading ? "..." : "Send"}
              </button>
            </div>
          </div>
        </div>

        {/* Side Panel */}
        <div className="side-panel">
          {/* Stats Panel */}
          <div className="panel-section">
            <div className="panel-title">SYSTEM STATUS</div>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">Model</span>
                <span className="stat-value">Gemini 2.5 Flash</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Embeddings</span>
                <span className="stat-value">3072-dim</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Chunks</span>
                <span className="stat-value">470 indexed</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Cache</span>
                <span className="stat-value">Active ✓</span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="panel-section">
            <div className="panel-title">QUICK QUESTIONS</div>
            <div className="quick-actions">
              {[
                "What BTech programs are offered?",
                "Tell me about PhD programs",
                "What are the admission requirements?",
                "List all courses in CSE",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="quick-btn"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="bottom-nav">
        <div className="info-text">© 2024 IIT Bhilai RAG System</div>
        <div className="info-text">v1.0.0 • Production Ready</div>
      </div>
    </div>
  );
}