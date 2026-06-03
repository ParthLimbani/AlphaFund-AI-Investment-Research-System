"use client";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function RiskMeter({ risk }: { risk: Record<string, any> }) {
  const level = (risk.risk_level ?? "unknown").toLowerCase();

  const SEGMENTS = [
    { id: "low",      label: "LOW",      color: "bg-emerald-500", textColor: "text-emerald-400" },
    { id: "moderate", label: "MOD",      color: "bg-amber-500",   textColor: "text-amber-400"   },
    { id: "high",     label: "HIGH",     color: "bg-orange-500",  textColor: "text-orange-400"  },
    { id: "extreme",  label: "EXTREME",  color: "bg-red-500",     textColor: "text-red-400"     },
  ];

  const levelIdx = SEGMENTS.findIndex((s) => s.id === level);
  const activeSegment = SEGMENTS[levelIdx];

  const flags = [
    { label: "CVaR",       value: risk.cvar_flag,         key: "cvar" },
    { label: "Volatility", value: risk.volatility_flag,   key: "vol"  },
    { label: "Overall",    value: risk.overall_risk_flag, key: "all"  },
  ];

  return (
    <div className="space-y-4">

      {/* Risk gauge */}
      <div className="rounded-lg border border-border/35 bg-card/30 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="label-xs">Risk Assessment</span>
          {activeSegment && (
            <span className={`text-sm font-bold font-mono uppercase ${activeSegment.textColor}`}>
              {level}
            </span>
          )}
        </div>

        {/* Segmented bar */}
        <div className="flex gap-1 h-2 rounded-full overflow-hidden">
          {SEGMENTS.map((seg, i) => (
            <div
              key={seg.id}
              className={`flex-1 rounded-full transition-all duration-700 ${
                i <= levelIdx && levelIdx >= 0 ? seg.color : "bg-muted/30"
              }`}
            />
          ))}
        </div>
        <div className="flex justify-between">
          {SEGMENTS.map((seg) => (
            <span key={seg.id} className={`text-[9px] font-mono tracking-widest ${
              seg.id === level ? "text-foreground/70" : "text-muted-foreground/30"
            }`}>
              {seg.label}
            </span>
          ))}
        </div>
      </div>

      {/* Flag indicators */}
      <div className="grid grid-cols-3 gap-2">
        {flags.map(({ label, value }) => (
          <div key={label} className={`rounded-lg border p-3 text-center transition-colors ${
            value ? "border-red-700/50 bg-red-950/25" : "border-emerald-800/30 bg-emerald-950/10"
          }`}>
            <div className={`text-base font-bold mb-0.5 ${value ? "text-red-400" : "text-emerald-400"}`}>
              {value ? "✕" : "✓"}
            </div>
            <div className="label-xs">{label}</div>
          </div>
        ))}
      </div>

      {/* Risk factors */}
      {risk.risk_factors?.length > 0 && (
        <div className="rounded-lg border border-border/30 bg-card/20 p-4">
          <div className="label-xs mb-3">Risk Factors</div>
          <ul className="space-y-2">
            {risk.risk_factors.map((f: string, i: number) => (
              <li key={i} className="flex gap-2 text-xs text-muted-foreground leading-relaxed">
                <span className="text-orange-500/70 shrink-0 mt-0.5">▲</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Mitigations */}
      {risk.risk_mitigation?.length > 0 && (
        <div className="rounded-lg border border-border/30 bg-card/20 p-4">
          <div className="label-xs mb-3">Mitigations</div>
          <ul className="space-y-2">
            {risk.risk_mitigation.map((m: string, i: number) => (
              <li key={i} className="flex gap-2 text-xs text-muted-foreground leading-relaxed">
                <span className="text-emerald-500/70 shrink-0 mt-0.5">▸</span>
                <span>{m}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Position size */}
      {risk.position_size_suggestion && (
        <div className="flex items-center justify-between rounded-lg border border-border/30 bg-muted/10 px-4 py-3 text-xs">
          <span className="label-xs">Suggested Position</span>
          <span className="font-mono text-foreground/70">{risk.position_size_suggestion}</span>
        </div>
      )}

      {/* Summary */}
      {risk.summary && (
        <p className="text-xs text-muted-foreground/55 italic border-l-2 border-border/30 pl-3 leading-relaxed">
          {risk.summary}
        </p>
      )}
    </div>
  );
}
