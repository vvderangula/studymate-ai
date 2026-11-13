import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import AIAssistant from "../components/AIAssistant";
import PdfChat from "../components/PdfChat";
import Segmented from "../components/Segmented";
import StudyTools from "../components/StudyTools";
import YoutubeChat from "../components/YoutubeChat";
import { PageBody, PageHeader } from "../components/workspace";
import { useAuth } from "../context/AuthContext";

const MODULES = [
  "Learn from PDF",
  "Learn from YouTube",
  "AI Study Tools",
  "AI Assistant",
] as const;

type Module = (typeof MODULES)[number];

const MODULE_DESCRIPTION: Record<Module, string> = {
  "Learn from PDF": "Upload a PDF, then ask questions and get answers with page references.",
  "Learn from YouTube": "Paste a video link, then ask questions with timestamps to the moment.",
  "AI Study Tools": "Turn a processed PDF or video into a quiz or study notes.",
  "AI Assistant": "Ask anything, or search academic papers and question them.",
};

/**
 * Learn page: a frozen header with the module tabs, and the active module
 * filling the rest of the screen. Modules stay mounted once opened so their
 * conversations survive switching tabs.
 */
export default function HomePage() {
  const { user } = useAuth();
  const location = useLocation();
  const [selected, setSelected] = useState<Module>(MODULES[0]);
  const [mountedModules, setMountedModules] = useState<Set<Module>>(
    () => new Set([MODULES[0]]),
  );
  const previousUserId = useRef<string | null | undefined>(undefined);

  // +1 when moving right through the tabs, -1 when moving left.
  const [direction, setDirection] = useState(1);

  function open(module: Module) {
    setDirection(MODULES.indexOf(module) >= MODULES.indexOf(selected) ? 1 : -1);
    setSelected(module);
    setMountedModules((prev) => (prev.has(module) ? prev : new Set(prev).add(module)));
  }

  useEffect(() => {
    const state = location.state as { module?: Module } | null;
    if (state?.module && MODULES.includes(state.module)) {
      open(state.module);
    }
  }, [location.state]);

  useEffect(() => {
    const currentUserId = user?.user_id ?? null;
    // Skip the initial mount so navigation state (a requested module) is
    // honored; only reset when the authenticated user actually changes.
    if (previousUserId.current === undefined) {
      previousUserId.current = currentUserId;
      return;
    }
    if (previousUserId.current !== currentUserId) {
      previousUserId.current = currentUserId;
      setSelected(MODULES[0]);
      setMountedModules(new Set([MODULES[0]]));
    }
  }, [user?.user_id]);

  const key = user?.user_id ?? "anon";

  function panel(module: Module, node: React.ReactNode) {
    if (!mountedModules.has(module)) return null;
    const active = selected === module;
    return (
      <div
        className={active ? "view-enter lg:h-full" : "hidden"}
        style={{ "--enter-x": `${direction * 24}px` } as React.CSSProperties}
        aria-hidden={!active}
      >
        {node}
      </div>
    );
  }

  return (
    <>
      <PageHeader title="Learn" description={MODULE_DESCRIPTION[selected]}>
        <Segmented
          label="Study modules"
          options={MODULES.map((name) => ({ value: name, label: name }))}
          value={selected}
          onChange={open}
          className="grid w-full grid-cols-2 sm:inline-grid sm:w-auto sm:grid-cols-4"
        />
      </PageHeader>

      <PageBody fill>
        {panel("Learn from PDF", <PdfChat key={`pdf-${key}`} />)}
        {panel("Learn from YouTube", <YoutubeChat key={`youtube-${key}`} />)}
        {panel(
          "AI Study Tools",
          <StudyTools key={`tools-${key}`} active={selected === "AI Study Tools"} />,
        )}
        {panel("AI Assistant", <AIAssistant key={`assistant-${key}`} />)}
      </PageBody>
    </>
  );
}
