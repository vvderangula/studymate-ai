import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import AIAssistant from "../components/AIAssistant";
import PdfChat from "../components/PdfChat";
import StudyTools from "../components/StudyTools";
import YoutubeChat from "../components/YoutubeChat";
import { useAuth } from "../context/AuthContext";

const MODULES = [
  "Learn from PDF",
  "Learn from YouTube",
  "AI Study Tools",
  "AI Assistant",
] as const;

type Module = (typeof MODULES)[number];

const MODULE_INTRO: Record<Module, { title: string; subtitle: string }> = {
  "Learn from PDF": {
    title: "Learn from PDF",
    subtitle: "Study and chat with your uploaded PDF documents.",
  },
  "Learn from YouTube": {
    title: "Learn from YouTube",
    subtitle: "Learn from YouTube videos with AI-powered conversations.",
  },
  "AI Study Tools": {
    title: "AI Study Tools",
    subtitle: "Generate quizzes and notes from your uploaded study materials.",
  },
  "AI Assistant": {
    title: "AI Assistant",
    subtitle: "General AI chat and research assistant.",
  },
};

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
}

/** Landing page: full-width module tabs with a chat-style panel below. */
export default function HomePage() {
  const { user } = useAuth();
  const location = useLocation();
  const [selected, setSelected] = useState<Module>(MODULES[0]);
  const [mountedModules, setMountedModules] = useState<Set<Module>>(
    () => new Set([MODULES[0]]),
  );
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    const state = location.state as { module?: Module } | null;
    if (state?.module && MODULES.includes(state.module)) {
      setSelected(state.module);
      setMountedModules((prev) => {
        const next = new Set(prev);
        next.add(state.module as Module);
        return next;
      });
      setMessages([]);
      setInput("");
    }
  }, [location.state]);

  useEffect(() => {
    setSelected(MODULES[0]);
    setMountedModules(new Set([MODULES[0]]));
    setMessages([]);
    setInput("");
  }, [user?.user_id]);

  function handleSelect(module: Module) {
    setSelected(module);
    setMountedModules((prev) => {
      const next = new Set(prev);
      next.add(module);
      return next;
    });
    setMessages([]);
    setInput("");
  }

  function handleSend() {
    const text = input.trim();
    if (!text) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", text },
      {
        id: Date.now() + 1,
        role: "assistant",
        text: `"${selected}" is coming soon.`,
      },
    ]);
    setInput("");
  }

  return (
    <section>
      <h1 className="text-center text-2xl font-bold tracking-tight text-slate-800">
        Study Modules
      </h1>

      {/* Full-width module selector */}
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {MODULES.map((name) => {
          const isActive = name === selected;
          return (
            <button
              key={name}
              type="button"
              onClick={() => handleSelect(name)}
              className={
                "w-full rounded-lg border px-4 py-3 text-sm font-medium transition-colors " +
                (isActive
                  ? "border-orange-500 bg-orange-500 text-white shadow-sm"
                  : "border-slate-200 bg-white text-slate-700 hover:border-orange-300 hover:text-orange-600")
              }
            >
              {name}
            </button>
          );
        })}
      </div>

      {/* Module content */}
      <div className="mt-8">
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-slate-800">{MODULE_INTRO[selected].title}</h2>
          <p className="mt-1 text-sm text-slate-500">{MODULE_INTRO[selected].subtitle}</p>
        </div>

        {mountedModules.has("Learn from PDF") && (
          <div
            className={selected === "Learn from PDF" ? "" : "hidden"}
            aria-hidden={selected !== "Learn from PDF"}
          >
            <PdfChat key={`pdf-${user?.user_id ?? "anon"}`} />
          </div>
        )}

        {mountedModules.has("Learn from YouTube") && (
          <div
            className={selected === "Learn from YouTube" ? "" : "hidden"}
            aria-hidden={selected !== "Learn from YouTube"}
          >
            <YoutubeChat key={`youtube-${user?.user_id ?? "anon"}`} />
          </div>
        )}

        {mountedModules.has("AI Study Tools") && (
          <div
            className={selected === "AI Study Tools" ? "" : "hidden"}
            aria-hidden={selected !== "AI Study Tools"}
          >
            <StudyTools key={`tools-${user?.user_id ?? "anon"}`} />
          </div>
        )}

        {mountedModules.has("AI Assistant") && (
          <div
            className={selected === "AI Assistant" ? "" : "hidden"}
            aria-hidden={selected !== "AI Assistant"}
          >
            <AIAssistant key={`assistant-${user?.user_id ?? "anon"}`} />
          </div>
        )}

        {!MODULES.includes(selected) && (
          <PlaceholderChat
            module={selected}
            input={input}
            messages={messages}
            onInput={setInput}
            onSend={handleSend}
          />
        )}
      </div>
    </section>
  );
}

interface PlaceholderChatProps {
  module: Module;
  input: string;
  messages: Message[];
  onInput: (value: string) => void;
  onSend: () => void;
}

/** Temporary chat panel for modules not yet implemented. */
function PlaceholderChat({
  module,
  input,
  messages,
  onInput,
  onSend,
}: PlaceholderChatProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
          placeholder={`Ask ${module}...`}
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
        />
        <button
          type="button"
          onClick={onSend}
          className="rounded-lg bg-orange-500 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-orange-600"
        >
          Send
        </button>
      </div>

      <div className="mt-5 space-y-3">
        {messages.length === 0 ? (
          <p className="text-center text-sm text-slate-400">
            Responses will appear here.
          </p>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={
                "max-w-[80%] rounded-lg px-4 py-2 text-sm " +
                (msg.role === "user"
                  ? "ml-auto bg-orange-50 text-slate-800"
                  : "mr-auto bg-slate-100 text-slate-700")
              }
            >
              {msg.text}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
