"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Badge, Card, ErrorNotice, PageHeader, Spinner, Stat, formatDate } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { Incident, Project, Workspace } from "@/lib/types";

export default function DashboardPage() {
  const workspaces = useApi<Workspace[]>("/workspaces");
  const active = workspaces.data?.[0] ?? null;

  useEffect(() => {
    if (active) window.localStorage.setItem("rg_workspace_id", active.id);
  }, [active]);

  const projects = useApi<Project[]>(active ? `/projects?workspace_id=${active.id}` : null);
  const incidents = useApi<Incident[]>(
    active ? `/incidents?workspace_id=${active.id}&status=open` : null,
  );

  if (workspaces.loading) return <Spinner label="Loading workspace" />;
  if (workspaces.error) return <ErrorNotice message={workspaces.error} />;

  if (!active) {
    return (
      <>
        <PageHeader title="Overview" description="Create a workspace to get started." />
        <Card className="p-6">
          <p className="text-sm text-slate-600">
            You don&apos;t belong to any workspace yet. Visit{" "}
            <Link className="text-brand-600 underline" href="/settings">
              Settings
            </Link>{" "}
            to create one.
          </p>
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Overview"
        description={`Workspace: ${active.name} · role ${active.role}`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Projects" value={projects.data?.length ?? "—"} />
        <Stat label="Open incidents" value={incidents.data?.length ?? "—"} />
        <Stat label="Workspace role" value={active.role} />
        <Stat label="Environment" value={active.slug} hint="Workspace slug" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Projects</h2>
            <Link className="text-sm text-brand-600 hover:underline" href="/projects">
              View all
            </Link>
          </div>
          {projects.loading ? (
            <Spinner />
          ) : projects.data && projects.data.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {projects.data.slice(0, 5).map((project) => (
                <li key={project.id} className="flex items-center justify-between py-2">
                  <Link className="text-sm hover:underline" href={`/projects/${project.id}`}>
                    {project.name}
                  </Link>
                  <span className="text-xs text-slate-400">{formatDate(project.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-4 text-sm text-slate-500">No projects yet.</p>
          )}
        </Card>

        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Open incidents</h2>
            <Link className="text-sm text-brand-600 hover:underline" href="/incidents">
              View all
            </Link>
          </div>
          {incidents.loading ? (
            <Spinner />
          ) : incidents.data && incidents.data.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {incidents.data.slice(0, 5).map((incident) => (
                <li key={incident.id} className="flex items-center justify-between gap-3 py-2">
                  <Link
                    className="truncate text-sm hover:underline"
                    href={`/incidents/${incident.id}`}
                  >
                    {incident.title}
                  </Link>
                  <Badge value={incident.severity} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-4 text-sm text-slate-500">No open incidents.</p>
          )}
        </Card>
      </div>
    </>
  );
}
