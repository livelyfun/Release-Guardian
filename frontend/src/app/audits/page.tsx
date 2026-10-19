"use client";

import { ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";

interface AuditLog {
  id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  created_at: string;
}

export default function AuditsPage() {
  const workspaceId = useActiveWorkspaceId();
  const { data, error, loading } = useApi<AuditLog[]>(
    workspaceId ? `/workspaces/${workspaceId}/audit-logs` : null,
  );

  return (
    <>
      <PageHeader title="Audit log" description="Sensitive administrative actions in this workspace." />
      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data && data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Target</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.id}>
                  <td className="font-medium">{entry.action}</td>
                  <td className="text-slate-500">
                    {entry.target_type}
                    {entry.target_id ? ` · ${entry.target_id.slice(0, 8)}` : ""}
                  </td>
                  <td className="text-slate-500">{formatDate(entry.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-8 text-sm text-slate-500">No audit entries yet.</p>
      )}
    </>
  );
}
