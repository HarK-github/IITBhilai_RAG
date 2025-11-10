"use client"
import { useState } from "react";

type Message = {
  sender: "user" | "bot";
  text: string;
};

export default function ChatClient() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`/api/chat?question=${encodeURIComponent(input)}`);
      const data = await res.json();
      console.log(data);
const botMessage: Message = { sender: "bot", text: data.answer };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      const errorMessage: Message = { sender: "bot", text: "Error fetching response" };
      setMessages((prev) => [...prev, errorMessage]);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 p-4">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-12">
        <h1 className="text-5xl font-bold text-white mb-2 text-center">IIT Bhilai RAG</h1>
        <p className="text-center text-blue-300 text-lg mb-12">Built using Ollama</p>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Feature 1 */}
          <div className="backdrop-blur-xl bg-black bg-opacity-10 border border-white border-opacity-20 rounded-2xl p-6 hover:bg-opacity-15 transition">
            <div className="w-8 h-8 bg-blue-400 bg-opacity-80 rounded-lg flex items-center justify-center mb-3">
              <span className="text-white font-bold text-sm">🧠</span>
            </div>
            <h3 className="text-white font-semibold mb-2">Intelligent RAG</h3>
            <p className="text-gray-300 text-sm">Retrieval-Augmented Generation for accurate, context-aware responses</p>
          </div>

          {/* Feature 2 */}
          <div className="backdrop-blur-xl bg-black bg-opacity-10 border border-white border-opacity-20 rounded-2xl p-6 hover:bg-opacity-15 transition">
            <div className="w-8 h-8 bg-purple-400 bg-opacity-80 rounded-lg flex items-center justify-center mb-3">
              <span className="text-white font-bold text-sm">⚡</span>
            </div>
            <h3 className="text-white font-semibold mb-2">Fast Processing</h3>
            <p className="text-gray-300 text-sm">Lightning-fast query responses powered by Ollama</p>
          </div>

          {/* Feature 3 */}
          <div className="backdrop-blur-xl bg-black bg-opacity-10 border border-white border-opacity-20 rounded-2xl p-6 hover:bg-opacity-15 transition">
            <div className="w-8 h-8 bg-green-400 bg-opacity-80 rounded-lg flex items-center justify-center mb-3">
              <span className="text-white font-bold text-sm">📚</span>
            </div>
            <h3 className="text-white font-semibold mb-2">Knowledge Base</h3>
            <p className="text-gray-300 text-sm">Access comprehensive IIT Bhilai information instantly</p>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex justify-center">
        <div className="w-full max-w-2xl backdrop-blur-2xl bg-black bg-opacity-10 border border-white border-opacity-20 rounded-3xl shadow-2xl overflow-hidden">
          
          {/* Chat Area */}
          <div className="flex flex-col h-96">
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`p-4 rounded-2xl max-w-xs backdrop-blur-lg ${
                    msg.sender === "user"
                      ? "bg-blue-500 bg-opacity-40 border border-blue-400 border-opacity-30 text-white"
                      : "bg-black bg-opacity-10 border border-white border-opacity-20 text-gray-100"
                  }`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-black bg-opacity-10 border border-white border-opacity-20 p-4 rounded-2xl backdrop-blur-lg">
                    <div className="flex space-x-2">
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></span>
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }}></span>
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="border-t border-white border-opacity-10 p-4 bg-black bg-opacity-5 backdrop-blur-xl">
              <div className="flex gap-3">
                <input
                  type="text"
                  className="flex-1 px-4 py-3 bg-black bg-opacity-10 border border-white border-opacity-20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-blue-400 focus:border-opacity-50 focus:bg-opacity-15 transition"
                  placeholder="Ask something..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                />
                <button
                  onClick={sendMessage}
                  disabled={loading}
                  className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 text-white rounded-xl transition font-medium"
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}