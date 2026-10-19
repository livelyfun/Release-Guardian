"use client";

import Link from "next/link";
import { Badge, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { Deployment } from "@/lib/types";

export default function DeploymentsPage() {
  const workspaceId = useActiveWorkspaceId();
  const { data, error, loading } = useApi<Deployment[]>(
    workspaceId ? `/deployments?workspace_id=${workspaceId}` : null,
  );

  return (
    <>
      <PageHeader title="Deployments" description="Release events correlated with monitor runs." />
      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data && data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Commit</th>
                <th>Branch</th>
                <th>PR</th>
                <th>Status</th>
                <th>Deployed</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((deployment) => (
                <tr key={deployment.id}>
                  <td className="font-mono text-xs">{deployment.commit_sha.slice(0, 10)}</td>
                  <td className="text-slate-500">{deployment.branch ?? "—"}</td>
                  <td className="text-slate-500">{deployment.pull_request ?? "—"}</td>
                  <td>
                    <Badge value={deployment.status === "success" ? "passed" : "pending"}>
                      {deployment.status}
                    </Badge>
                  </td>
                  <td className="text-slate-500">{formatDate(deployment.deployed_at)}</td>
                  <td>
                    <Link className="text-brand-600 hover:underline" href={`/deployments/${deployment.id}`}>
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-8 text-sm text-slate-500">No deployments recorded yet.</p>
      )}
    </>
  );
}
