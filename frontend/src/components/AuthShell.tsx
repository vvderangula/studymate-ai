import type { ReactNode } from "react";
import { BrandMark } from "./icons";

/** Centered frame shared by the login and register screens. */
export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div
      className="flex min-h-screen flex-col bg-canvas px-4 py-8 sm:py-12"
      style={{
        backgroundImage:
          "radial-gradient(900px 480px at 50% -8%, #FFE7D6 0%, rgba(255,231,214,0) 70%), linear-gradient(180deg, #FFFAF6 0%, #FBF8F5 100%)",
      }}
    >
      <div className="mx-auto flex w-full max-w-[25rem] flex-1 flex-col justify-center">
        <div className="mb-8 flex flex-col items-center text-center">
          <BrandMark className="h-11 w-11 drop-shadow-[0_6px_14px_rgba(234,88,12,0.25)]" />
          <span className="mt-4 text-2xl font-semibold tracking-[-0.02em] text-ink">
            StudyMate AI
          </span>
          <p className="mt-1 text-sm text-muted">Your AI-powered personal tutor</p>
        </div>

        <div className="rounded-card border border-line bg-surface p-6 shadow-raised sm:p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
