"use client";

import Link from "next/link";
import { useState } from "react";
import { ErrorNotice, EmptyState, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { Project } from "@/lib/types";

export default function ProjectsPage() {
  const workspaceId = useActiveWorkspaceId();
  const path = workspaceId ? `/projects?workspace_id=${workspaceId}` : null;
  const { data, error, loading, reload } = useApi<Project[]>(path);

  const [name, setName] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!workspaceId) return;
    setBusy(true);
    setFormError(null);
    try {
      await apiClient.post("/projects", {
        workspace_id: workspaceId,
        name,
        repository_url: repositoryUrl || null,
      });
      setName("");
      setRepositoryUrl("");
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to create project");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Projects" description="Websites and applications under monitoring." />

      <form onSubmit={create} className="card mb-6 grid gap-3 p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div>
          <label className="label" htmlFor="project-name">
            Name
          </label>
          <input
            id="project-name"
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </div>
        <div>
          <label className="label" htmlFor="project-repo">
            Repository URL (optional)
          </label>
          <input
            id="project-repo"
            className="input"
            value={repositoryUrl}
            onChange={(event) => setRepositoryUrl(event.target.value)}
            placeholder="https://github.com/org/repo"
          />
        </div>
        <button className="btn-primary" disabled={busy || !workspaceId}>
          {busy ? "Creating…" : "Add project"}
        </button>
      </form>

      {formError ? <div className="mb-4"><ErrorNotice message={formError} /></div> : null}

      {loading ? (
        <Spinner />
      ) : error ? (
        <ErrorNotice message={error} />
      ) : data && data.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
                <th>Repository</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data.map((project) => (
                <tr key={project.id}>
                  <td>
                    <Link className="font-medium text-brand-600 hover:underline" href={`/projects/${project.id}`}>
                      {project.name}
                    </Link>
                  </td>
                  <td className="text-slate-500">{project.slug}</td>
                  <td className="max-w-xs truncate text-slate-500">{project.repository_url ?? "—"}</td>
                  <td className="text-slate-500">{formatDate(project.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No projects yet" description="Add your first project to start monitoring." />
      )}
    </>
  );
}
