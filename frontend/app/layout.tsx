import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AlphaFund — AI Investment Research",
  description: "Multi-agent LLM investment analysis powered by LangGraph",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">

        {/* Disclaimer banner — always visible at top */}
        <div className="border-b border-amber-700/40 bg-amber-950/30 px-4 py-1.5">
          <p className="text-center text-[11px] font-semibold text-amber-300/90 tracking-wide">
            ⚠ For research and educational purposes only — <strong>NOT financial advice.</strong> Do not make investment decisions based on this output.
          </p>
        </div>

        {/* Top nav */}
        <nav className="sticky top-0 z-40 border-b border-border/50 bg-background/80 backdrop-blur-md">
          <div className="max-w-6xl mx-auto px-6 h-12 flex items-center gap-8">

            {/* Brand */}
            <Link href="/" className="flex items-center gap-2.5 group">
              <span className="w-6 h-6 rounded-sm bg-primary/10 border border-border/60 flex items-center justify-center text-[11px] font-black text-primary group-hover:bg-primary/20 transition-colors">
                α
              </span>
              <span className="text-sm font-bold tracking-wider text-foreground/90 group-hover:text-foreground transition-colors">
                ALPHAFUND
              </span>
              <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded border border-border/50 text-muted-foreground/60 tracking-widest">
                BETA
              </span>
            </Link>

            {/* Nav links */}
            <div className="flex items-center gap-1 ml-auto">
              {[
                { href: "/", label: "Analyze" },
                { href: "/history", label: "History" },
                { href: "/memory", label: "Memory" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/40 rounded-md transition-all"
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </nav>

        <main className="flex-1 flex flex-col">{children}</main>

        {/* Footer */}
        <footer className="border-t border-border/30 bg-muted/5 py-4 px-6">
          <div className="max-w-6xl mx-auto space-y-2">
            <p className="text-[11px] font-semibold text-amber-400/70 text-center tracking-wide">
              ⚠ NOT FINANCIAL ADVICE · Research tool only · Always consult a licensed financial professional before investing
            </p>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground/35 tracking-wider">© ALPHAFUND</span>
              <span className="text-[10px] text-muted-foreground/30 font-mono">LangGraph · Llama 3.3 70B · Groq</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
