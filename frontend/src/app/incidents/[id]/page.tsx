"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Incident, IncidentStatus } from "@/lib/types";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading, reload } = useApi<Incident>(`/incidents/${params.id}`);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function update(status: IncidentStatus) {
    setBusy(true);
    setActionError(null);
    try {
      await apiClient.patch(`/incidents/${params.id}`, { status });
      reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to update incident");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title={data?.title ?? "Incident"}
        actions={
          <Link className="btn-secondary" href="/incidents">
            Back
          </Link>
        }
      />
      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <Card className="p-6">
            <dl className="space-y-4 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Status</dt>
                <dd>
                  <Badge value={data.status} />
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Severity</dt>
                <dd>
                  <Badge value={data.severity} />
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Dedupe key</dt>
                <dd className="font-mono text-xs">{data.dedupe_key}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Opened</dt>
                <dd>{formatDate(data.opened_at)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Acknowledged</dt>
                <dd>{formatDate(data.acknowledged_at)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Resolved</dt>
                <dd>{formatDate(data.resolved_at)}</dd>
              </div>
            </dl>
          </Card>

          <Card className="h-fit p-5">
            <h2 className="mb-3 text-sm font-semibold">Actions</h2>
            {actionError ? <div className="mb-3"><ErrorNotice message={actionError} /></div> : null}
            <div className="space-y-2">
              <button
                className="btn-secondary w-full"
                onClick={() => update("acknowledged")}
                disabled={busy || data.status !== "open"}
              >
                Acknowledge
              </button>
              <button
                className="btn-primary w-full"
                onClick={() => update("resolved")}
                disabled={busy || data.status === "resolved"}
              >
                Resolve
              </button>
            </div>
          </Card>
        </div>
      ) : null}
    </>
  );
}
