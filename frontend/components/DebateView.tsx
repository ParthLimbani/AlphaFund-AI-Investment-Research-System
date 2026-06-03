"use client";
import { useState } from "react";

type DebateResult = {
  bull_case?: string;
  bear_case?: string;
  bull_rebuttal?: string;
  bear_rebuttal?: string;
  winner?: string;
  winner_reasoning?: string;
  confidence?: number;
  investment_lean?: string;
};

type Props = { debateResult: DebateResult };

export function DebateView({ debateResult: d }: Props) {
  const [openSections, setOpenSections] = useState<Set<string>>(new Set(["cases"]));

  function toggle(key: string) {
    setOpenSections((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  const winner = d.winner?.toLowerCase();
  const winnerBanner = {
    bull: { bg: "bg-emerald-950/40 border-emerald-700/40", label: "text-emerald-400", icon: "▲", text: "Bull Case Prevails" },
    bear: { bg: "bg-red-950/40 border-red-700/40",         label: "text-red-400",     icon: "▼", text: "Bear Case Prevails" },
  }[winner ?? ""] ?? { bg: "bg-amber-950/30 border-amber-700/40", label: "text-amber-400", icon: "━", text: "Draw" };

  const sections = [
    { key: "cases",    label: "Opening Arguments", bull: d.bull_case,    bear: d.bear_case },
    { key: "rebuttal", label: "Rebuttals",          bull: d.bull_rebuttal, bear: d.bear_rebuttal },
  ].filter((s) => s.bull || s.bear);

  function ArgList({ text }: { text?: string }) {
    if (!text) return <p className="text-xs text-muted-foreground/40 italic">No data</p>;
    const items = text.split("|").map((a) => a.trim()).filter(Boolean);
    return (
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-xs text-muted-foreground/80 leading-relaxed">
            <span className="mt-0.5 shrink-0 opacity-50">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-3">

      {/* Winner verdict */}
      {winner && (
        <div className={`rounded-lg border px-4 py-3 flex items-start gap-4 ${winnerBanner.bg}`}>
          <span className={`text-2xl font-black mt-0.5 ${winnerBanner.label}`}>{winnerBanner.icon}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <span className={`text-sm font-bold ${winnerBanner.label}`}>{winnerBanner.text}</span>
              {d.confidence && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border/30 bg-muted/20 text-muted-foreground">
                  {Math.round(d.confidence * 100)}% confidence
                </span>
              )}
              {d.investment_lean && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-border/30 bg-muted/20 text-muted-foreground capitalize">
                  {d.investment_lean}
                </span>
              )}
            </div>
            {d.winner_reasoning && (
              <p className="text-xs text-muted-foreground/70 leading-relaxed">{d.winner_reasoning}</p>
            )}
          </div>
        </div>
      )}

      {/* Debate sections */}
      {sections.map((s) => (
        <div key={s.key} className="border border-border/35 rounded-lg overflow-hidden bg-card/30">
          <button
            onClick={() => toggle(s.key)}
            className="w-full flex items-center justify-between px-4 py-3 text-xs font-semibold tracking-wide text-left hover:bg-muted/25 transition-colors"
          >
            <span className="label-xs">{s.label}</span>
            <span className="text-muted-foreground/40 text-[10px]">{openSections.has(s.key) ? "COLLAPSE ▲" : "EXPAND ▼"}</span>
          </button>

          {openSections.has(s.key) && (
            <div className="border-t border-border/30 grid grid-cols-2">
              {/* Bull column */}
              <div className="p-4 border-r border-border/30">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span className="label-xs text-emerald-500/70">Bull Case</span>
                </div>
                <ArgList text={s.bull} />
              </div>
              {/* Bear column */}
              <div className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                  <span className="label-xs text-red-500/70">Bear Case</span>
                </div>
                <ArgList text={s.bear} />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
