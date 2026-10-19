"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge, Card, EmptyState, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Environment, Project } from "@/lib/types";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const project = useApi<Project>(`/projects/${params.id}`);
  const environments = useApi<Environment[]>(`/projects/${params.id}/environments`);

  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [isProduction, setIsProduction] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await apiClient.post(`/projects/${params.id}/environments`, {
        name,
        base_url: baseUrl,
        is_production: isProduction,
      });
      setName("");
      setBaseUrl("");
      setIsProduction(false);
      environments.reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to create environment");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title={project.data?.name ?? "Project"}
        description={project.data?.repository_url ?? undefined}
        actions={
          <Link className="btn-secondary" href="/projects">
            Back
          </Link>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <h2 className="mb-3 text-sm font-semibold">Environments</h2>
          {environments.loading ? (
            <Spinner />
          ) : environments.data && environments.data.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Base URL</th>
                    <th>Type</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {environments.data.map((environment) => (
                    <tr key={environment.id}>
                      <td>
                        <Link
                          className="font-medium text-brand-600 hover:underline"
                          href={`/monitors?environment_id=${environment.id}`}
                        >
                          {environment.name}
                        </Link>
                      </td>
                      <td className="max-w-xs truncate text-slate-500">{environment.base_url}</td>
                      <td>
                        <Badge value={environment.is_production ? "enabled" : "disabled"}>
                          {environment.is_production ? "production" : "non-production"}
                        </Badge>
                      </td>
                      <td className="text-slate-500">{formatDate(environment.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No environments" description="Add staging or production targets." />
          )}
        </div>

        <Card className="h-fit p-5">
          <h2 className="mb-3 text-sm font-semibold">Add environment</h2>
          <form onSubmit={create} className="space-y-3">
            <div>
              <label className="label" htmlFor="env-name">
                Name
              </label>
              <input
                id="env-name"
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="env-url">
                Base URL
              </label>
              <input
                id="env-url"
                type="url"
                className="input"
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="https://example.com"
                required
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={isProduction}
                onChange={(event) => setIsProduction(event.target.checked)}
              />
              Production environment
            </label>
            {formError ? <ErrorNotice message={formError} /> : null}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Saving…" : "Add environment"}
            </button>
          </form>
        </Card>
      </div>
    </>
  );
}
