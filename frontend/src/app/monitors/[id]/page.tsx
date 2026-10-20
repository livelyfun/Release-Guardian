"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { StepBuilder } from "@/components/step-builder";
import { apiClient, ApiError } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type {
  BrowserStep,
  Monitor,
  RegressionSuppression,
  Run,
} from "@/lib/types";

function toLocalInput(date: Date): string {
  const offset = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export default function MonitorDetailPage() {
  const params = useParams<{ id: string }>();
  const monitor = useApi<Monitor>(`/monitors/${params.id}`);
  const runs = useApi<Run[]>(`/monitors/${params.id}/runs`);
  const suppression = useApi<RegressionSuppression>(
    `/monitors/${params.id}/regression-suppression`,
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [steps, setSteps] = useState<BrowserStep[]>([]);
  const [captureTrace, setCaptureTrace] = useState(false);
  const [captureHar, setCaptureHar] = useState(false);
  const [screenshotEachStep, setScreenshotEachStep] = useState(false);
  const [formFactor, setFormFactor] = useState("desktop");
  const [saveReport, setSaveReport] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [configBusy, setConfigBusy] = useState(false);
  const [configSaved, setConfigSaved] = useState(false);

  const [suppressUntil, setSuppressUntil] = useState("");
  const [suppressReason, setSuppressReason] = useState("");
  const [suppressError, setSuppressError] = useState<string | null>(null);
  const [suppressBusy, setSuppressBusy] = useState(false);

  useEffect(() => {
    if (!monitor.data) return;
    const config = monitor.data.config ?? {};
    setSteps(Array.isArray(config.steps) ? (config.steps as BrowserStep[]) : []);
    setCaptureTrace(Boolean(config.capture_trace));
    setCaptureHar(Boolean(config.capture_har));
    setScreenshotEachStep(Boolean(config.screenshot_each_step));
    setFormFactor(typeof config.form_factor === "string" ? config.form_factor : "desktop");
    setSaveReport(Boolean(config.save_assets));
  }, [monitor.data]);

  useEffect(() => {
    setSuppressUntil(toLocalInput(new Date(Date.now() + 60 * 60 * 1000)));
  }, []);

  async function trigger() {
    setBusy(true);
    setError(null);
    try {
      await apiClient.post(`/monitors/${params.id}/runs`, {});
      runs.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to trigger run");
    } finally {
      setBusy(false);
    }
  }

  async function saveConfig(event: React.FormEvent) {
    event.preventDefault();
    if (!monitor.data) return;
    setConfigBusy(true);
    setConfigError(null);
    setConfigSaved(false);
    try {
      const config = { ...(monitor.data.config ?? {}) };
      if (monitor.data.kind === "browser") {
        config.steps = steps;
        config.capture_trace = captureTrace;
        config.capture_har = captureHar;
        config.screenshot_each_step = screenshotEachStep;
      } else if (monitor.data.kind === "lighthouse") {
        config.form_factor = formFactor;
        config.save_assets = saveReport;
      }
      await apiClient.patch(`/monitors/${params.id}`, { config });
      monitor.reload();
      setConfigSaved(true);
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "Failed to save configuration");
    } finally {
      setConfigBusy(false);
    }
  }

  async function setSuppression(event: React.FormEvent) {
    event.preventDefault();
    setSuppressBusy(true);
    setSuppressError(null);
    try {
      await apiClient.post(`/monitors/${params.id}/regression-suppression`, {
        until: new Date(suppressUntil).toISOString(),
        reason: suppressReason,
      });
      setSuppressReason("");
      suppression.reload();
    } catch (err) {
      setSuppressError(err instanceof ApiError ? err.message : "Failed to set suppression");
    } finally {
      setSuppressBusy(false);
    }
  }

  async function clearSuppression() {
    setSuppressBusy(true);
    setSuppressError(null);
    try {
      await apiClient.del(`/monitors/${params.id}/regression-suppression`);
      suppression.reload();
    } catch (err) {
      setSuppressError(err instanceof ApiError ? err.message : "Failed to clear suppression");
    } finally {
      setSuppressBusy(false);
    }
  }

  const isBrowser = monitor.data?.kind === "browser";
  const isLighthouse = monitor.data?.kind === "lighthouse";

  return (
    <>
      <PageHeader
        title={monitor.data?.name ?? "Monitor"}
        description={monitor.data?.target_url}
        actions={
          <>
            <Link className="btn-secondary" href="/monitors">
              Back
            </Link>
            <button className="btn-primary" onClick={trigger} disabled={busy}>
              {busy ? "Queuing…" : "Run now"}
            </button>
          </>
        }
      />

      {monitor.data ? (
        <div className="mb-6 grid gap-4 sm:grid-cols-4">
          <Card className="p-4">
            <p className="text-xs uppercase text-slate-500">Kind</p>
            <p className="mt-1 font-medium uppercase">{monitor.data.kind}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs uppercase text-slate-500">Interval</p>
            <p className="mt-1 font-medium">{monitor.data.interval_seconds}s</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs uppercase text-slate-500">Status</p>
            <p className="mt-1">
              <Badge value={monitor.data.enabled ? "enabled" : "disabled"} />
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-xs uppercase text-slate-500">Last checked</p>
            <p className="mt-1 text-sm">{formatDate(monitor.data.last_checked_at)}</p>
          </Card>
        </div>
      ) : null}

      {error ? <div className="mb-4"><ErrorNotice message={error} /></div> : null}

      {isBrowser || isLighthouse ? (
        <Card className="mb-6 p-6">
          <h2 className="mb-4 text-sm font-semibold">Configuration</h2>
          <form onSubmit={saveConfig} className="space-y-4">
            {isBrowser ? (
              <>
                <StepBuilder steps={steps} onChange={setSteps} disabled={configBusy} />
                <div className="flex flex-wrap gap-5 border-t border-slate-100 pt-4 text-sm text-slate-600">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={captureTrace}
                      disabled={configBusy}
                      onChange={(event) => setCaptureTrace(event.target.checked)}
                    />
                    Capture Playwright trace
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={captureHar}
                      disabled={configBusy}
                      onChange={(event) => setCaptureHar(event.target.checked)}
                    />
                    Capture HAR
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={screenshotEachStep}
                      disabled={configBusy}
                      onChange={(event) => setScreenshotEachStep(event.target.checked)}
                    />
                    Screenshot every step
                  </label>
                </div>
              </>
            ) : (
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <label className="label" htmlFor="monitor-form-factor">
                    Form factor
                  </label>
                  <select
                    id="monitor-form-factor"
                    className="input w-auto"
                    value={formFactor}
                    disabled={configBusy}
                    onChange={(event) => setFormFactor(event.target.value)}
                  >
                    <option value="desktop">Desktop</option>
                    <option value="mobile">Mobile</option>
                  </select>
                </div>
                <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={saveReport}
                    disabled={configBusy}
                    onChange={(event) => setSaveReport(event.target.checked)}
                  />
                  Save the JSON report as an artifact
                </label>
              </div>
            )}

            {configError ? <ErrorNotice message={configError} /> : null}
            {configSaved ? <p className="text-sm text-emerald-700">Configuration saved.</p> : null}
            <button className="btn-primary" disabled={configBusy}>
              {configBusy ? "Saving…" : "Save configuration"}
            </button>
          </form>
        </Card>
      ) : null}

      <Card className="mb-6 p-6">
        <h2 className="mb-1 text-sm font-semibold">Regression suppression</h2>
        <p className="mb-4 text-sm text-slate-500">
          Pause performance-regression incidents for planned work. Failed checks still
          open incidents.
        </p>

        {suppression.loading ? (
          <Spinner />
        ) : suppression.error ? (
          <ErrorNotice message={suppression.error} />
        ) : (
          <>
            {suppression.data?.active ? (
              <div className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Regressions suppressed until{" "}
                {new Date(suppression.data.until ?? "").toLocaleString()}
                {suppression.data.reason ? ` — ${suppression.data.reason}` : ""}
                <button
                  className="ml-3 text-xs font-medium underline disabled:opacity-50"
                  disabled={suppressBusy}
                  onClick={clearSuppression}
                >
                  Clear
                </button>
              </div>
            ) : (
              <p className="mb-4 text-sm text-slate-500">No active suppression.</p>
            )}

            {suppressError ? <div className="mb-4"><ErrorNotice message={suppressError} /></div> : null}

            <form onSubmit={setSuppression} className="flex flex-wrap items-end gap-3">
              <div>
                <label className="label" htmlFor="suppress-until">
                  Suppress until
                </label>
                <input
                  id="suppress-until"
                  className="input w-auto"
                  type="datetime-local"
                  value={suppressUntil}
                  disabled={suppressBusy}
                  onChange={(event) => setSuppressUntil(event.target.value)}
                  required
                />
              </div>
              <div className="min-w-56 flex-1">
                <label className="label" htmlFor="suppress-reason">
                  Reason
                </label>
                <input
                  id="suppress-reason"
                  className="input"
                  value={suppressReason}
                  disabled={suppressBusy}
                  onChange={(event) => setSuppressReason(event.target.value)}
                  placeholder="Known cold start during migration"
                />
              </div>
              <button className="btn-secondary" disabled={suppressBusy}>
                {suppressBusy ? "Saving…" : "Suppress"}
              </button>
            </form>
          </>
        )}
      </Card>

      <h2 className="mb-3 text-sm font-semibold">Recent runs</h2>
      {runs.loading ? (
        <Spinner />
      ) : runs.error ? (
        <ErrorNotice message={runs.error} />
      ) : runs.data && runs.data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Trigger</th>
                <th>Duration</th>
                <th>Started</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {runs.data.map((run) => (
                <tr key={run.id}>
                  <td>
                    <Badge value={run.status} />
                  </td>
                  <td className="text-slate-500">{run.trigger}</td>
                  <td className="text-slate-500">{run.duration_ms ? `${run.duration_ms} ms` : "—"}</td>
                  <td className="text-slate-500">{formatDate(run.started_at)}</td>
                  <td>
                    <Link className="text-brand-600 hover:underline" href={`/tests/${run.id}`}>
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-8 text-sm text-slate-500">No runs yet. Trigger one to get started.</p>
      )}
    </>
  );
}
