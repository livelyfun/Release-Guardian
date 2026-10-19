"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Badge, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { Environment, Monitor, MonitorKind } from "@/lib/types";

function MonitorsInner() {
  const searchParams = useSearchParams();
  const workspaceId = useActiveWorkspaceId();
  const environmentId = searchParams.get("environment_id");

  const environments = useApi<Environment[]>(
    workspaceId ? `/environments?workspace_id=${workspaceId}` : null,
  );
  const monitorsPath = environmentId
    ? `/monitors?environment_id=${environmentId}`
    : workspaceId
      ? `/monitors?workspace_id=${workspaceId}`
      : null;
  const monitors = useApi<Monitor[]>(monitorsPath);

  const [form, setForm] = useState({
    environment_id: environmentId ?? "",
    name: "",
    kind: "http" as MonitorKind,
    target_url: "",
    interval_seconds: 300,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await apiClient.post(`/environments/${form.environment_id}/monitors`, {
        name: form.name,
        kind: form.kind,
        target_url: form.target_url,
        interval_seconds: form.interval_seconds,
      });
      setForm((prev) => ({ ...prev, name: "", target_url: "" }));
      monitors.reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to create monitor");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Monitors" description="Scheduled HTTP, browser, and performance checks." />

      <form onSubmit={create} className="card mb-6 grid gap-3 p-5 lg:grid-cols-5 lg:items-end">
        <div>
          <label className="label" htmlFor="monitor-env">
            Environment
          </label>
          <select
            id="monitor-env"
            className="input"
            value={form.environment_id}
            onChange={(event) => setForm({ ...form, environment_id: event.target.value })}
            required
          >
            <option value="">Select…</option>
            {(environments.data ?? []).map((environment) => (
              <option key={environment.id} value={environment.id}>
                {environment.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="monitor-name">
            Name
          </label>
          <input
            id="monitor-name"
            className="input"
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            required
          />
        </div>
        <div>
          <label className="label" htmlFor="monitor-kind">
            Kind
          </label>
          <select
            id="monitor-kind"
            className="input"
            value={form.kind}
            onChange={(event) => setForm({ ...form, kind: event.target.value as MonitorKind })}
          >
            <option value="http">HTTP</option>
            <option value="browser">Browser</option>
            <option value="lighthouse">Lighthouse</option>
          </select>
        </div>
        <div>
          <label className="label" htmlFor="monitor-url">
            Target URL
          </label>
          <input
            id="monitor-url"
            type="url"
            className="input"
            value={form.target_url}
            onChange={(event) => setForm({ ...form, target_url: event.target.value })}
            placeholder="https://example.com/health"
            required
          />
        </div>
        <button className="btn-primary" disabled={busy}>
          {busy ? "Adding…" : "Add monitor"}
        </button>
      </form>

      {formError ? <div className="mb-4"><ErrorNotice message={formError} /></div> : null}

      {monitors.loading ? (
        <Spinner />
      ) : monitors.error ? (
        <ErrorNotice message={monitors.error} />
      ) : monitors.data && monitors.data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Kind</th>
                <th>Target</th>
                <th>Interval</th>
                <th>Status</th>
                <th>Last checked</th>
              </tr>
            </thead>
            <tbody>
              {monitors.data.map((monitor) => (
                <tr key={monitor.id}>
                  <td>
                    <Link className="font-medium text-brand-600 hover:underline" href={`/monitors/${monitor.id}`}>
                      {monitor.name}
                    </Link>
                  </td>
                  <td className="uppercase text-slate-500">{monitor.kind}</td>
                  <td className="max-w-xs truncate text-slate-500">{monitor.target_url}</td>
                  <td className="text-slate-500">{monitor.interval_seconds}s</td>
                  <td>
                    <Badge value={monitor.enabled ? "enabled" : "disabled"} />
                  </td>
                  <td className="text-slate-500">{formatDate(monitor.last_checked_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-8 text-sm text-slate-500">No monitors yet.</p>
      )}
    </>
  );
}

export default function MonitorsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <MonitorsInner />
    </Suspense>
  );
}
