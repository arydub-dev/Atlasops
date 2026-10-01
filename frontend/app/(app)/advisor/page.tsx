"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Send, Sparkles, User as UserIcon } from "lucide-react";
import { api } from "@/lib/api";
import type { AIOrchestrateResponse } from "@/lib/types";
import { PageHeader } from "@/components/shared/page-header";
import { Markdown } from "@/components/shared/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface Message {
  role: "user" | "assistant";
  content: string;
  model?: string;
  intent?: string;
  tool?: string;
  confidence?: number | null;
  citations?: { type?: string; id?: string; source?: string }[];
}

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [provider, setProvider] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get<string[]>("/ai/suggestions").then(setSuggestions).catch(() => {});
    api
      .get<{ provider: string }>("/ai/status")
      .then((s) => setProvider(s.provider))
      .catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function send(prompt: string) {
    if (!prompt.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", content: prompt }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post<AIOrchestrateResponse>("/ai/orchestrate", {
        prompt,
        report_type: "orchestrate",
      });
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.response,
          model: res.model,
          intent: res.intent,
          tool: res.tool,
          confidence: res.confidence,
          citations: res.citations,
        },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: e instanceof Error ? e.message : "Request failed" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col space-y-4">
      <PageHeader
        title="Operations Copilot"
        description="Graph-grounded orchestration — intent detection, retrieval, risk, and cited responses."
      >
        <Badge variant={provider === "openai" ? "success" : "secondary"} className="gap-1.5">
          <Sparkles className="h-3 w-3" />
          {provider === "openai" ? "OpenAI" : "Local Engine"}
        </Badge>
      </PageHeader>

      <Card className="flex min-h-0 flex-1 flex-col">
        <CardContent ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto pt-5">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Bot className="h-7 w-7" />
              </div>
              <p className="mt-4 text-sm font-medium">What operational question can I analyze?</p>
              <p className="mt-1 max-w-md text-xs text-muted-foreground">
                Mission summaries, root-cause, impact, supplier and inventory analysis — every answer
                cites graph entities and live risk context.
              </p>
              <div className="mt-5 flex max-w-xl flex-wrap justify-center gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:bg-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
              {m.role === "assistant" && (
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Bot className="h-4 w-4" />
                </span>
              )}
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2.5 ${
                  m.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "border border-border bg-muted/40"
                }`}
              >
                {m.role === "assistant" ? (
                  <>
                    {(m.tool || m.confidence != null) && (
                      <div className="mb-2 flex flex-wrap gap-1.5">
                        {m.tool && (
                          <Badge variant="secondary" className="text-[10px]">
                            {m.tool}
                          </Badge>
                        )}
                        {m.intent && (
                          <Badge variant="outline" className="text-[10px]">
                            {m.intent}
                          </Badge>
                        )}
                        {m.confidence != null && (
                          <Badge variant="outline" className="text-[10px]">
                            {(m.confidence * 100).toFixed(0)}% confidence
                          </Badge>
                        )}
                      </div>
                    )}
                    <Markdown content={m.content} />
                    {m.citations && m.citations.length > 0 && (
                      <div className="mt-3 border-t border-border/60 pt-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                          Citations
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {m.citations.slice(0, 8).map((c, ci) => (
                            <Badge key={ci} variant="secondary" className="text-[10px]">
                              {c.type}
                              {c.id ? `:${String(c.id).slice(0, 24)}` : ""}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm">{m.content}</p>
                )}
              </div>
              {m.role === "user" && (
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary">
                  <UserIcon className="h-4 w-4" />
                </span>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Bot className="h-4 w-4" />
              </span>
              <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 px-4 py-3">
                {[0, 1, 2].map((d) => (
                  <span
                    key={d}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground"
                    style={{ animationDelay: `${d * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          )}
        </CardContent>

        <div className="border-t border-border p-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about delays, impact, suppliers, inventory…"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
