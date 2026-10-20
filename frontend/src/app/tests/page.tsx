"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiDownload, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { Run } from "@/lib/types";

export default function TestRunsPage() {
  const workspaceId = useActiveWorkspaceId();
  const { data, error, loading } = useApi<Run[]>(
    workspaceId ? `/runs?workspace_id=${workspaceId}` : null,
  );
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  async function exportCsv() {
    if (!workspaceId) return;
    setExporting(true);
    setExportError(null);
    try {
      await apiDownload(`/runs/export.csv?workspace_id=${workspaceId}`, "runs.csv");
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Failed to export runs");
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Test runs"
        description="History of monitor executions and step results."
        actions={
          <button className="btn-secondary" onClick={exportCsv} disabled={!workspaceId || exporting}>
            {exporting ? "Exporting…" : "Export CSV"}
          </button>
        }
      />
      {exportError ? <div className="mb-4"><ErrorNotice message={exportError} /></div> : null}
      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data && data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Trigger</th>
                <th>Duration</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((run) => (
                <tr key={run.id}>
                  <td className="font-mono text-xs text-slate-500">{run.id.slice(0, 8)}</td>
                  <td>
                    <Badge value={run.status} />
                  </td>
                  <td className="text-slate-500">{run.trigger}</td>
                  <td className="text-slate-500">{run.duration_ms ? `${run.duration_ms} ms` : "—"}</td>
                  <td className="text-slate-500">{formatDate(run.created_at)}</td>
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
        <p className="py-8 text-sm text-slate-500">No runs recorded yet.</p>
      )}
    </>
  );
}
