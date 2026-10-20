"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { Deployment, DeploymentComparison } from "@/lib/types";

function formatDuration(value: number | null): string {
  if (value === null) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${value} ms`;
}

function formatDelta(value: number | null): string {
  if (value === null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export default function DeploymentDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading } = useApi<Deployment>(`/deployments/${params.id}`);
  const comparison = useApi<DeploymentComparison>(`/deployments/${params.id}/comparison`);

  return (
    <>
      <PageHeader
        title="Deployment"
        description={data?.commit_sha}
        actions={
          <Link className="btn-secondary" href="/deployments">
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
          <Card className="max-w-xl p-6">
            <dl className="space-y-4 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Commit</dt>
                <dd className="font-mono">{data.commit_sha}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Branch</dt>
                <dd>{data.branch ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Pull request</dt>
                <dd>{data.pull_request ?? "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Status</dt>
                <dd>
                  <Badge value={data.status} />
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Deployed</dt>
                <dd>{formatDate(data.deployed_at)}</dd>
              </div>
            </dl>
          </Card>

          <Card className="mt-6 p-6">
            <h2 className="mb-1 text-sm font-semibold">Comparison with previous known good</h2>
            {comparison.loading ? (
              <Spinner />
            ) : comparison.error ? (
              <ErrorNotice message={comparison.error} />
            ) : comparison.data ? (
              comparison.data.previous_known_good ? (
                <>
                  <p className="mb-4 text-sm text-slate-500">
                    Baseline deployment{" "}
                    <Link
                      className="font-mono text-brand-600 hover:underline"
                      href={`/deployments/${comparison.data.previous_known_good.id}`}
                    >
                      {comparison.data.previous_known_good.commit_sha.slice(0, 10)}
                    </Link>{" "}
                    · {comparison.data.summary.regressed ?? 0} regressed ·{" "}
                    {comparison.data.summary.improved ?? 0} improved
                  </p>
                  {comparison.data.monitors.length === 0 ? (
                    <p className="text-sm text-slate-500">No checks were recorded for either deployment.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="text-xs uppercase text-slate-500">
                          <tr>
                            <th className="py-2 pr-4">Monitor</th>
                            <th className="py-2 pr-4">Before</th>
                            <th className="py-2 pr-4">After</th>
                            <th className="py-2 pr-4">Duration</th>
                            <th className="py-2">Verdict</th>
                          </tr>
                        </thead>
                        <tbody>
                          {comparison.data.monitors.map((monitor) => (
                            <tr key={monitor.monitor_id} className="border-t border-slate-100">
                              <td className="py-2 pr-4">{monitor.monitor_name}</td>
                              <td className="py-2 pr-4">
                                {monitor.previous_status ? (
                                  <Badge value={monitor.previous_status} />
                                ) : (
                                  "—"
                                )}
                              </td>
                              <td className="py-2 pr-4">
                                {monitor.current_status ? (
                                  <Badge value={monitor.current_status} />
                                ) : (
                                  "—"
                                )}
                              </td>
                              <td className="py-2 pr-4 text-slate-600">
                                {formatDuration(monitor.previous_duration_ms)} →{" "}
                                {formatDuration(monitor.current_duration_ms)}{" "}
                                <span className="text-xs text-slate-500">
                                  ({formatDelta(monitor.duration_delta_pct)})
                                </span>
                              </td>
                              <td className="py-2">
                                <Badge value={monitor.verdict} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-500">
                  No earlier passing deployment exists for this environment yet.
                </p>
              )
            ) : null}
          </Card>
        </>
      ) : null}
    </>
  );
}
