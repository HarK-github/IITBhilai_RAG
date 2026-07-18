"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  id: string;
  sender: "user" | "bot";
  text: string;
  timestamp: Date;
  provider?: string;
  cacheLayer?: string;
};

type Chunk = {
  id: string;
  document: string;
  metadata: Record<string, any>;
  embedding: number[];
};

const QUICK_QUESTIONS = [
  "What BTech programs are offered?",
  "Tell me about PhD programs",
  "What are the admission requirements?",
  "List all courses in CSE",
];

// Cosine similarity function
function cosineSimilarity(a: number[], b: number[]) {
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  if (normA === 0 || normB === 0) return 0;
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [status, setStatus] = useState("Loading database...");
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_API_KEY || "";

  // Load the static vector database (JSON) on mount
  useEffect(() => {
    const loadDatabase = async () => {
      try {
        const response = await fetch("/embeddings.json");
        if (!response.ok) throw new Error("Failed to load embeddings");
        const data = await response.json();
        setChunks(data);
        setStatus("Client-Side Database Ready");
      } catch (err) {
        console.error(err);
        setStatus("Database unavailable");
      }
    };
    loadDatabase();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    if (!apiKey) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: "user",
          text: trimmed,
          timestamp: new Date(),
        },
        {
          id: (Date.now() + 1).toString(),
          sender: "bot",
          text: "API Key is missing. Please set NEXT_PUBLIC_GOOGLE_API_KEY in your environment.",
          timestamp: new Date(),
        },
      ]);
      setInput("");
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setIsTyping(true);

    try {
      // 1. Get embedding for user query
      const embedRes = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: "models/text-embedding-004",
            content: { parts: [{ text: trimmed }] },
          }),
        }
      );
      
      const embedData = await embedRes.json();
      if (!embedRes.ok) throw new Error(embedData.error?.message || "Failed to embed query");
      
      const queryEmbedding = embedData.embedding.values;

      // 2. Compute similarity and get top 3 chunks
      const similarities = chunks.map((chunk) => ({
        ...chunk,
        score: cosineSimilarity(queryEmbedding, chunk.embedding),
      }));
      
      similarities.sort((a, b) => b.score - a.score);
      const topChunks = similarities.slice(0, 3);
      const contextText = topChunks.map(c => c.document).join("\n\n---\n\n");

      // 3. Generate response using RAG context
      const prompt = `You are a helpful assistant for IIT Bhilai. Use the following extracted context to answer the user's question. If the answer is not in the context, say "I don't have enough information about that based on my current database."

Context:
${contextText}

Question:
${trimmed}

Answer:`;

      const generateRes = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
          }),
        }
      );

      const generateData = await generateRes.json();
      if (!generateRes.ok) throw new Error(generateData.error?.message || "Failed to generate answer");

      const answerText = generateData.candidates?.[0]?.content?.parts?.[0]?.text || "No answer generated.";

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "bot",
          text: answerText,
          timestamp: new Date(),
          provider: "Client-Side RAG",
          cacheLayer: "Browser",
        },
      ]);
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "bot",
          text: `Error: ${err.message}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
      setLoading(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app-shell">
      <div className="top-bar">
        <div className="brand-block">
          <div className="logo">IIT BHILAI RAG</div>
          <div className="info-text">100% Serverless / Client-Side Architecture</div>
        </div>

        <div className="status-chip">
          <span className={`status-dot ${status === "Client-Side Database Ready" ? "online" : ""}`} />
          <span>{status}</span>
        </div>
      </div>

      <div className="main-content">
        <div className="chat-container">
          <div className="messages-area">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-emoji">💬</div>
                <h3>Welcome to IIT Bhilai RAG</h3>
                <p>Ask about admissions, courses, campus life, or faculty.</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={`message-row ${message.sender}`}>
                  <div className="message-bubble">
                    <div className="message-header">
                      <span>{message.sender === "user" ? "You" : "Assistant"}</span>
                      {message.provider ? <span>• {message.provider}</span> : null}
                    </div>
                    <div className="message-text">{message.text}</div>
                  </div>
                </div>
              ))
            )}

            {isTyping ? (
              <div className="message-row bot">
                <div className="typing-indicator" aria-label="Assistant is typing">
                  <div className="dot" />
                  <div className="dot" />
                  <div className="dot" />
                </div>
              </div>
            ) : null}

            <div ref={messagesEndRef} />
          </div>

          <div className="input-area">
            <div className="input-wrapper">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask something about IIT Bhilai..."
                disabled={loading}
                className="input-field"
                rows={1}
                style={{ resize: "none" }}
                onInput={(event) => {
                  const target = event.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
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

        <div className="side-panel">
          <div className="panel-section">
            <div className="panel-title">SYSTEM STATUS</div>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">Architecture</span>
                <span className="stat-value">Static / Browser</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">LLM Provider</span>
                <span className="stat-value">Gemini API (Direct)</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Database Chunks</span>
                <span className="stat-value">{chunks.length}</span>
              </div>
            </div>
          </div>

          <div className="panel-section">
            <div className="panel-title">QUICK QUESTIONS</div>
            <div className="quick-actions">
              {QUICK_QUESTIONS.map((question) => (
                <button
                  key={question}
                  onClick={() => setInput(question)}
                  className="quick-btn"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bottom-nav">
        <div className="info-text">© 2024 IIT Bhilai RAG System</div>
        <div className="info-text">Static Serverless Edition</div>
      </div>
    </div>
  );
}
