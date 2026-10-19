"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { Run } from "@/lib/types";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading } = useApi<Run>(`/runs/${params.id}`);

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
        </>
      ) : null}
    </>
  );
}
