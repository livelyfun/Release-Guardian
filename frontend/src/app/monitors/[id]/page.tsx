"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Monitor, Run } from "@/lib/types";

export default function MonitorDetailPage() {
  const params = useParams<{ id: string }>();
  const monitor = useApi<Monitor>(`/monitors/${params.id}`);
  const runs = useApi<Run[]>(`/monitors/${params.id}/runs`);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
