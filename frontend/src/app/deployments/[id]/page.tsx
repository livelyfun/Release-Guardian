"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { Deployment } from "@/lib/types";

export default function DeploymentDetailPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading } = useApi<Deployment>(`/deployments/${params.id}`);

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
                <Badge value={data.status === "success" ? "passed" : "pending"}>{data.status}</Badge>
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Deployed</dt>
              <dd>{formatDate(data.deployed_at)}</dd>
            </div>
          </dl>
        </Card>
      ) : null}
    </>
  );
}
