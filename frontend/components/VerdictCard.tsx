"use client";

type Props = {
  action: string;
  confidence: number;
  ticker: string;
  timeHorizon?: string;
  priceTarget?: string;
  explanation?: string;
  keyReasons?: string[];
  keyRisks?: string[];
};

const STYLES: Record<string, { border: string; glow: string; text: string; badge: string; bar: string }> = {
  BUY:  { border: "border-emerald-700/50", glow: "glow-green",  text: "text-emerald-400", badge: "bg-emerald-500/15 text-emerald-300 border-emerald-600/40", bar: "bg-emerald-500" },
  HOLD: { border: "border-amber-700/50",  glow: "glow-amber",  text: "text-amber-400",   badge: "bg-amber-500/15  text-amber-300  border-amber-600/40",  bar: "bg-amber-500"  },
  SELL: { border: "border-red-700/50",    glow: "glow-red",    text: "text-red-400",     badge: "bg-red-500/15    text-red-300    border-red-600/40",    bar: "bg-red-500"    },
};

const DEFAULT_STYLE = { border: "border-border/50", glow: "", text: "text-foreground", badge: "bg-muted text-muted-foreground border-border", bar: "bg-muted-foreground" };

export function VerdictCard({ action, confidence, ticker, timeHorizon, priceTarget, explanation, keyReasons = [], keyRisks = [] }: Props) {
  const s = STYLES[action] ?? DEFAULT_STYLE;
  const pct = Math.round(confidence * 100);
  const today = new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  return (
    <div className={`rounded-xl border-2 bg-card/60 backdrop-blur-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500 ${s.border} ${s.glow}`}>

      {/* Research note header */}
      <div className="px-5 py-2.5 border-b border-border/30 flex items-center justify-between bg-muted/10">
        <div className="flex items-center gap-2">
          <span className="label-xs">AI Research Note</span>
          <span className="text-muted-foreground/30">·</span>
          <span className="font-mono text-[10px] text-muted-foreground/50">{ticker}</span>
        </div>
        <span className="text-[10px] font-mono text-muted-foreground/40">{today}</span>
      </div>

      <div className="p-5 space-y-4">
        {/* Action + confidence + meta */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-5">
            <div className={`px-4 py-2 rounded-lg border text-2xl font-black tracking-widest ${s.badge}`}>
              {action}
            </div>
            <div>
              <div className="label-xs mb-0.5">Confidence</div>
              <div className={`text-3xl font-black font-mono tracking-tight ${s.text}`}>{pct}%</div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-xl font-mono font-bold tracking-wider">{ticker}</div>
            {timeHorizon && (
              <div className="text-xs text-muted-foreground capitalize mt-0.5">
                {timeHorizon.replace(/_/g, " ")}
              </div>
            )}
            {priceTarget && priceTarget !== "N/A" && (
              <div className="text-xs text-muted-foreground font-mono mt-0.5">
                Target <span className="text-foreground/70">{priceTarget}</span>
              </div>
            )}
          </div>
        </div>

        {/* Confidence bar */}
        <div className="space-y-1">
          <div className="w-full h-1.5 bg-muted/60 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out ${s.bar}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground/40 font-mono">
            <span>0%</span><span>50%</span><span>100%</span>
          </div>
        </div>

        {/* Explanation */}
        {explanation && (
          <p className="text-sm text-foreground/75 leading-relaxed border-l-2 border-border/40 pl-3 italic">
            {explanation}
          </p>
        )}

        {/* Reasons + Risks */}
        {(keyReasons.length > 0 || keyRisks.length > 0) && (
          <div className="grid grid-cols-2 gap-3 pt-1">
            {keyReasons.length > 0 && (
              <div className="rounded-lg border border-border/30 bg-emerald-950/10 p-3">
                <div className="label-xs text-emerald-500/60 mb-2">Key Drivers</div>
                <ul className="space-y-1.5">
                  {keyReasons.map((r, i) => (
                    <li key={i} className="flex gap-1.5 text-xs text-muted-foreground">
                      <span className="text-emerald-500 shrink-0 mt-0.5">▸</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {keyRisks.length > 0 && (
              <div className="rounded-lg border border-border/30 bg-red-950/10 p-3">
                <div className="label-xs text-red-500/60 mb-2">Key Risks</div>
                <ul className="space-y-1.5">
                  {keyRisks.map((r, i) => (
                    <li key={i} className="flex gap-1.5 text-xs text-muted-foreground">
                      <span className="text-red-500 shrink-0 mt-0.5">▸</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
