'use client';

import { useState } from 'react';
import { Bot, X, Send, Sparkles, HelpCircle, BookOpen, Lightbulb } from 'lucide-react';
import { api } from '@/lib/api';
import type { APIResponse } from '@/lib/types';

interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
}

const QUICK_PROMPTS = [
  { icon: Lightbulb, label: 'Ethical Hacking', prompt: 'What is ethical hacking and how do I start learning it safely?' },
  { icon: BookOpen, label: 'Port Scanning', prompt: 'Explain port scanning and how it is used defensively.' },
  { icon: HelpCircle, label: 'SQLi Defense', prompt: 'How do I defend an application against SQL injection?' },
  { icon: Bot, label: 'Mission Help', prompt: 'Guide me through the Cyber Network Raid game step by step.' },
];

export default function AIMentorWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: 'Greetings Agent! I am your CyberVerse AI Mentor. Ask me any cybersecurity concept, request mission hints, or ask for study guidance — I am wired into the CyberVerse project itself!',
    },
  ]);

  async function handleSend(promptText?: string) {
    const textToSend = promptText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = { id: String(Date.now()), sender: 'user', text: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    if (!promptText) setInput('');
    setLoading(true);

    try {
      const history = [...messages, userMsg]
        .slice(-12)
        .map((m) => ({ role: m.sender === 'user' ? 'user' : 'assistant', content: m.text }));
      const res = await api.post<APIResponse<{ reply: string }>>('/ai/chat', { 
        messages: history,
        current_page: window.location.href
      });
      const reply = res.data?.reply || 'Keep pushing forward! Practice in the virtual sandbox to master this concept.';
      setMessages((prev) => [...prev, { id: String(Date.now() + 1), sender: 'ai', text: reply }]);
    } catch (err) {
      const fallback = err instanceof Error ? err.message : 'The AI mentor is temporarily unavailable.';
      setMessages((prev) => [...prev, { id: String(Date.now() + 1), sender: 'ai', text: fallback }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 rounded-full border border-cyber-primary bg-cyber-dark/95 px-4 py-3 text-cyber-primary shadow-[0_0_20px_rgba(0,229,255,0.4)] transition-all hover:scale-105 hover:bg-cyber-primary hover:text-black"
        >
          <Bot className="h-5 w-5 animate-pulse" />
          <span className="font-mono text-sm font-semibold tracking-wider uppercase">AI Mentor</span>
        </button>
      )}

      {isOpen && (
        <div className="flex h-[480px] w-[350px] flex-col rounded-lg border border-cyber-primary/60 bg-cyber-dark/95 p-4 shadow-[0_0_30px_rgba(0,229,255,0.25)] backdrop-blur-md sm:w-[400px]">
          {/* Header */}
          <div className="mb-3 flex items-center justify-between border-b border-cyber-border pb-3">
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-cyber-primary" />
              <h3 className="font-semibold text-cyber-primary">CyberVerse AI Mentor</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-cyber-muted hover:text-cyber-danger"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Quick Prompt Chips */}
          <div className="mb-2 flex flex-wrap gap-1.5 border-b border-cyber-border/40 pb-2 text-[11px]">
            {QUICK_PROMPTS.map(({ icon: Icon, label, prompt }) => (
              <button
                key={label}
                onClick={() => void handleSend(prompt)}
                className="flex items-center gap-1 rounded border border-cyber-primary/40 bg-cyber-primary/10 px-2 py-1 text-cyber-primary hover:bg-cyber-primary/20"
              >
                <Icon className="h-3 w-3" />
                {label}
              </button>
            ))}
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-2 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.sender === 'ai' && <Bot className="h-4 w-4 shrink-0 text-cyber-primary mt-1" />}
                <div
                  className={`rounded-lg px-3 py-2 max-w-[85%] leading-relaxed ${
                    m.sender === 'user'
                      ? 'bg-cyber-primary/20 text-cyber-text border border-cyber-primary/40'
                      : 'bg-cyber-surface/80 text-cyber-muted border border-cyber-border'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-cyber-primary text-xs font-mono">
                <Sparkles className="h-3.5 w-3.5 animate-spin" />
                <span>AI Mentor thinking...</span>
              </div>
            )}
          </div>

          {/* Input Box */}
          <div className="mt-3 flex gap-2 border-t border-cyber-border pt-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void handleSend()}
              placeholder="Ask AI Mentor anything..."
              className="flex-1 rounded border border-cyber-border bg-black/50 px-3 py-1.5 text-xs text-cyber-text placeholder:text-cyber-muted focus:border-cyber-primary focus:outline-none"
            />
            <button
              onClick={() => void handleSend()}
              disabled={loading || !input.trim()}
              className="rounded bg-cyber-primary px-3 py-1.5 text-black hover:bg-cyber-primary/80 disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
