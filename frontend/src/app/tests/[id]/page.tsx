"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { Artifact, Run } from "@/lib/types";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading } = useApi<Run>(`/runs/${params.id}`);
  const artifacts = useApi<Artifact[]>(params.id ? `/runs/${params.id}/artifacts` : null);
  const workspaceId = useActiveWorkspaceId();

  return (
    <>
      <PageHeader
        title={`Run ${params.id.slice(0, 8)}`}
        description={data ? `Monitor ${data.monitor_id.slice(0, 8)}` : undefined}
        actions={
          <Link className="btn-secondary" href="/tests">
            Back
          </Link>
        }
      />

      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data ? (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-4">
            <Card className="p-4">
              <p className="text-xs uppercase text-slate-500">Status</p>
              <p className="mt-1">
                <Badge value={data.status} />
              </p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase text-slate-500">Trigger</p>
              <p className="mt-1 font-medium">{data.trigger}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase text-slate-500">Duration</p>
              <p className="mt-1 font-medium">{data.duration_ms ? `${data.duration_ms} ms` : "—"}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs uppercase text-slate-500">Finished</p>
              <p className="mt-1 text-sm">{formatDate(data.finished_at)}</p>
            </Card>
          </div>

          <h2 className="mb-3 text-sm font-semibold">Steps</h2>
          {data.steps.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Step</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {data.steps.map((step) => (
                    <tr key={step.id}>
                      <td className="text-slate-500">{step.step_index + 1}</td>
                      <td className="font-medium">{step.name}</td>
                      <td>
                        <Badge value={step.status} />
                      </td>
                      <td className="text-slate-500">
                        {step.duration_ms ? `${step.duration_ms} ms` : "—"}
                      </td>
                      <td className="max-w-sm truncate text-red-600">{step.error ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-6 text-sm text-slate-500">No step results recorded.</p>
          )}

          <h2 className="mb-3 mt-8 text-sm font-semibold">Evidence</h2>
          {!workspaceId ? (
            <p className="text-sm text-slate-500">Select a workspace to view artifacts.</p>
          ) : artifacts.loading ? (
            <Spinner />
          ) : artifacts.error ? (
            <ErrorNotice message={artifacts.error} />
          ) : artifacts.data && artifacts.data.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {artifacts.data.map((artifact) => (
                <ArtifactCard key={artifact.id} artifact={artifact} workspaceId={workspaceId} />
              ))}
            </div>
          ) : (
            <p className="py-4 text-sm text-slate-500">
              No stored evidence for this run. Browser monitors keep a final screenshot;
              Lighthouse runs keep a JSON report.
            </p>
          )}
        </>
      ) : null}
    </>
  );
}

function formatBytes(value: number | null): string {
  if (!value) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function ArtifactCard({ artifact, workspaceId }: { artifact: Artifact; workspaceId: string }) {
  const [signedUrl, setSignedUrl] = useState<string | null>(artifact.url);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const query = encodeURIComponent(artifact.storage_key);
    apiClient
      .get<{ signed_url: string }>(
        `/workspaces/${workspaceId}/artifacts/signed-url?artifact_key=${query}`,
      )
      .then((response) => {
        if (active) setSignedUrl(response.signed_url);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof ApiError ? err.message : "Artifact URL unavailable");
        }
      });
    return () => {
      active = false;
    };
  }, [artifact.storage_key, workspaceId]);

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <p className="text-sm font-medium capitalize">{artifact.kind}</p>
          <p className="text-xs text-slate-500">
            {formatBytes(artifact.size_bytes)}
            {artifact.mime_type ? ` · ${artifact.mime_type}` : ""}
          </p>
        </div>
        {signedUrl ? (
          <a
            className="text-xs text-brand-600 hover:underline"
            href={signedUrl}
            rel="noreferrer"
            target="_blank"
          >
            Open
          </a>
        ) : null}
      </div>
      {artifact.kind === "screenshot" && signedUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={`Screenshot from run ${artifact.run_id.slice(0, 8)}`}
          className="max-h-96 w-full bg-slate-50 object-contain"
          src={signedUrl}
        />
      ) : (
        <p className="break-all px-4 py-4 font-mono text-xs text-slate-500">
          {artifact.storage_key}
        </p>
      )}
      {error ? <p className="px-4 pb-4 text-xs text-amber-700">{error}</p> : null}
    </Card>
  );
}
