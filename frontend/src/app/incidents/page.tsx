"use client";

import Link from "next/link";
import { Badge, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { Incident } from "@/lib/types";

export default function IncidentsPage() {
  const workspaceId = useActiveWorkspaceId();
  const { data, error, loading } = useApi<Incident[]>(
    workspaceId ? `/incidents?workspace_id=${workspaceId}` : null,
  );

  return (
    <>
      <PageHeader title="Incidents" description="Deduplicated failures with lifecycle tracking." />
      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data && data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Opened</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((incident) => (
                <tr key={incident.id}>
                  <td>
                    <Link className="font-medium text-brand-600 hover:underline" href={`/incidents/${incident.id}`}>
                      {incident.title}
                    </Link>
                  </td>
                  <td>
                    <Badge value={incident.severity} />
                  </td>
                  <td>
                    <Badge value={incident.status} />
                  </td>
                  <td className="text-slate-500">{formatDate(incident.opened_at)}</td>
                  <td>
                    <Link className="text-brand-600 hover:underline" href={`/incidents/${incident.id}`}>
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-8 text-sm text-slate-500">No incidents. Everything is healthy.</p>
      )}
    </>
  );
}
