"use client";

import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  FileSpreadsheet,
  FileUp,
  RotateCcw,
  TriangleAlert,
  Upload,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { EntitySpec, ImportJob, ImportPreview, ImportResult } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ImportStatusBadge } from "@/components/data/data-bits";
import { cn } from "@/lib/utils";

const NONE = "__none__";

export function ImportCenter({ excel = false }: { excel?: boolean }) {
  const { user } = useAuth();
  const canWrite = user && user.role !== "executive";
  const { data: entities } = useFetch<Record<string, EntitySpec>>("/data/entities");
  const { data: history, refetch: refetchHistory } = useFetch<ImportJob[]>("/data/imports");

  const [entity, setEntity] = useState("suppliers");
  const [file, setFile] = useState<File | null>(null);
  const [sheet, setSheet] = useState<string | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = excel ? ".xlsx,.xlsm" : ".csv";
  const spec = entities?.[entity];

  function reset() {
    setFile(null);
    setSheet(null);
    setPreview(null);
    setMapping({});
    setResult(null);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function runPreview(f: File, ent: string, sh: string | null, map?: Record<string, string | null>) {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("entity", ent);
      if (sh) fd.append("sheet", sh);
      if (map) fd.append("mapping", JSON.stringify(cleanMap(map)));
      const pv = await api.upload<ImportPreview>("/data/import/preview", fd);
      setPreview(pv);
      if (!map) setMapping(pv.suggested_mapping);
      if (excel && pv.sheets.length && !sh) setSheet(pv.sheets[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
      setPreview(null);
    } finally {
      setBusy(false);
    }
  }

  function cleanMap(map: Record<string, string | null>): Record<string, string | null> {
    const out: Record<string, string | null> = {};
    for (const [k, v] of Object.entries(map)) out[k] = v === NONE ? null : v;
    return out;
  }

  function onFile(f: File | undefined) {
    if (!f) return;
    setFile(f);
    setSheet(null);
    setResult(null);
    runPreview(f, entity, null);
  }

  function changeEntity(ent: string) {
    setEntity(ent);
    setResult(null);
    if (file) runPreview(file, ent, sheet);
  }

  function changeSheet(sh: string) {
    setSheet(sh);
    if (file) runPreview(file, entity, sh);
  }

  function setFieldMap(field: string, col: string) {
    setMapping((m) => ({ ...m, [field]: col === NONE ? null : col }));
  }

  async function revalidate() {
    if (file) await runPreview(file, entity, sheet, mapping);
  }

  async function commit() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("entity", entity);
      fd.append("mapping", JSON.stringify(cleanMap(mapping)));
      if (sheet) fd.append("sheet", sheet);
      const res = await api.upload<ImportResult>("/data/import/commit", fd);
      setResult(res);
      refetchHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        {/* Entity + dropzone */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">1 · Select data type & upload</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>Target entity</Label>
              <Select value={entity} onValueChange={changeEntity} disabled={!canWrite}>
                <SelectTrigger className="sm:w-64"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {entities &&
                    Object.entries(entities).map(([key, s]) => (
                      <SelectItem key={key} value={key}>{s.label}</SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>

            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); onFile(e.dataTransfer.files?.[0]); }}
              onClick={() => canWrite && inputRef.current?.click()}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors",
                dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-accent/30",
                !canWrite && "cursor-not-allowed opacity-60"
              )}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                {excel ? <FileSpreadsheet className="h-6 w-6" /> : <FileUp className="h-6 w-6" />}
              </span>
              <p className="mt-3 text-sm font-medium">
                {file ? file.name : `Drop a ${excel ? "Excel (.xlsx)" : "CSV"} file here`}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {file ? "Click to replace" : `or click to browse · ${accept}`}
              </p>
              <input
                ref={inputRef}
                type="file"
                accept={accept}
                className="hidden"
                onChange={(e) => onFile(e.target.files?.[0])}
                disabled={!canWrite}
              />
            </div>

            {excel && preview && preview.sheets.length > 0 && (
              <div className="space-y-1.5">
                <Label>Worksheet</Label>
                <Select value={sheet ?? preview.sheets[0]} onValueChange={changeSheet}>
                  <SelectTrigger className="sm:w-64"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {preview.sheets.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {error && <p className="text-sm text-destructive">{error}</p>}
            {!canWrite && (
              <p className="text-xs text-muted-foreground">
                Your role has read-only access; importing requires Operations Manager or Analyst.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Mapping + validation */}
        {preview && spec && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="text-sm">2 · Map columns & validate</CardTitle>
              <span className="text-xs text-muted-foreground">{formatNumber(preview.row_count)} rows detected</span>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {spec.fields.map((f) => (
                  <div key={f.name} className="space-y-1">
                    <Label className="flex items-center gap-1 text-xs">
                      {f.label}
                      {f.required && <span className="text-destructive">*</span>}
                    </Label>
                    <Select
                      value={mapping[f.name] ?? NONE}
                      onValueChange={(v) => setFieldMap(f.name, v)}
                      disabled={!canWrite}
                    >
                      <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value={NONE}>— Not mapped —</SelectItem>
                        {preview.columns.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border/60 bg-muted/30 p-3 text-sm">
                <span className="flex items-center gap-1.5 text-success">
                  <CheckCircle2 className="h-4 w-4" /> {formatNumber(preview.validation.valid)} valid
                </span>
                <span className="flex items-center gap-1.5 text-destructive">
                  <XCircle className="h-4 w-4" /> {formatNumber(preview.validation.rejected)} rejected
                </span>
                {canWrite && (
                  <Button variant="outline" size="sm" className="ml-auto" onClick={revalidate} disabled={busy}>
                    <RotateCcw className="h-3.5 w-3.5" /> Re-validate
                  </Button>
                )}
              </div>

              {preview.validation.errors.length > 0 && (
                <div className="rounded-lg border border-border/60">
                  <div className="border-b border-border/60 px-3 py-2 text-xs font-medium text-muted-foreground">
                    Validation errors (first {preview.validation.errors.length})
                  </div>
                  <div className="max-h-40 overflow-y-auto divide-y divide-border/40 text-xs">
                    {preview.validation.errors.map((e, i) => (
                      <div key={i} className="flex gap-2 px-3 py-1.5">
                        <span className="shrink-0 font-mono text-muted-foreground">Row {e.row}</span>
                        <span className="text-destructive">{e.errors.join("; ")}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* preview table */}
              <div className="overflow-x-auto rounded-lg border border-border/60">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border/60 bg-muted/40 text-left text-muted-foreground">
                      {preview.columns.map((c) => (
                        <th key={c} className="whitespace-nowrap px-3 py-2 font-medium">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {preview.preview_rows.map((row, i) => (
                      <tr key={i}>
                        {preview.columns.map((c) => (
                          <td key={c} className="whitespace-nowrap px-3 py-1.5">{String(row[c] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {canWrite && (
                <div className="flex items-center gap-2">
                  <Button onClick={commit} disabled={busy || preview.validation.valid === 0}>
                    <Upload className="h-4 w-4" /> Import {formatNumber(preview.validation.valid)} rows
                  </Button>
                  <Button variant="ghost" onClick={reset} disabled={busy}>Cancel</Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Result */}
        {result && (
          <Card className={cn(
            result.status === "success" ? "border-success/30 bg-success/5"
              : result.status === "failed" ? "border-destructive/30 bg-destructive/5"
              : "border-warning/30 bg-warning/5"
          )}>
            <CardContent className="space-y-3 py-5">
              <div className="flex items-center gap-2">
                {result.status === "failed"
                  ? <TriangleAlert className="h-5 w-5 text-destructive" />
                  : <CheckCircle2 className="h-5 w-5 text-success" />}
                <p className="font-medium">
                  Import {result.status} — {formatNumber(result.rows_imported)} imported,{" "}
                  {formatNumber(result.rows_rejected)} rejected
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3 text-sm">
                <Stat label="Processed" value={formatNumber(result.rows_processed)} />
                <Stat label="Imported" value={formatNumber(result.rows_imported)} tone="text-success" />
                <Stat label="Rejected" value={formatNumber(result.rows_rejected)} tone="text-destructive" />
              </div>
              <Button variant="outline" size="sm" onClick={reset}>Import another file</Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* History */}
      <div>
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-sm">Import History</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!history || history.length === 0 ? (
              <p className="py-6 text-center text-xs text-muted-foreground">No imports yet.</p>
            ) : (
              history.map((j) => (
                <div key={j.id} className="rounded-lg border border-border/60 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium capitalize">{j.entity_type}</p>
                    <ImportStatusBadge status={j.status} />
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{j.source_name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatNumber(j.rows_imported)} imported · {formatNumber(j.rows_rejected)} rejected ·{" "}
                    {relativeTime(j.created_at)}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/60 p-2.5">
      <p className="section-label">{label}</p>
      <p className={cn("mt-0.5 font-mono text-lg font-semibold tabular-nums", tone)}>{value}</p>
    </div>
  );
}
