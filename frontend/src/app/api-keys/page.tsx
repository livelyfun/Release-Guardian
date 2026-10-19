"use client";

import { useState } from "react";
import { Card, ErrorNotice, PageHeader, Spinner, formatDate } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type { ApiKey } from "@/lib/types";

export default function ApiKeysPage() {
  const workspaceId = useActiveWorkspaceId();
  const { data, error, loading, reload } = useApi<ApiKey[]>(
    workspaceId ? `/workspaces/${workspaceId}/api-keys` : null,
  );
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write" | "admin">("read");
  const [created, setCreated] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!workspaceId) return;
    setBusy(true);
    setFormError(null);
    setCreated(null);
    try {
      const scopes = scope === "read" ? [] : [scope];
      const result = await apiClient.post<ApiKey>(`/workspaces/${workspaceId}/api-keys`, {
        name,
        scopes,
      });
      setCreated(result.key ?? null);
      setName("");
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to create key");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    try {
      await apiClient.del(`/api-keys/${id}`);
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to revoke key");
    }
  }

  return (
    <>
      <PageHeader title="API keys" description="Machine-to-machine credentials scoped to this workspace." />

      {created ? (
        <Card className="mb-6 border-emerald-200 bg-emerald-50 p-5">
          <p className="text-sm font-medium text-emerald-800">
            Copy this key now — it will not be shown again.
          </p>
          <code className="mt-2 block break-all rounded-lg bg-white px-3 py-2 text-xs">
            {created}
          </code>
        </Card>
      ) : null}

      <form onSubmit={create} className="card mb-6 grid gap-3 p-5 sm:grid-cols-[1fr_160px_auto] sm:items-end">
        <div>
          <label className="label" htmlFor="key-name">
            Key name
          </label>
          <input
            id="key-name"
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </div>
        <div>
          <label className="label" htmlFor="key-scope">
            Scope
          </label>
          <select
            id="key-scope"
            className="input"
            value={scope}
            onChange={(event) => setScope(event.target.value as "read" | "write" | "admin")}
          >
            <option value="read">Read</option>
            <option value="write">Write</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <button className="btn-primary" disabled={busy || !workspaceId}>
          {busy ? "Creating…" : "Create key"}
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
                <th>Prefix</th>
                <th>Scope</th>
                <th>Status</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.map((key) => (
                <tr key={key.id}>
                  <td className="font-medium">{key.name}</td>
                  <td className="font-mono text-xs text-slate-500">{key.prefix}…</td>
                  <td className="text-slate-500">
                    {key.scopes.length > 0 ? key.scopes.join(", ") : "read"}
                  </td>
                  <td className="text-slate-500">{key.revoked_at ? `revoked ${formatDate(key.revoked_at)}` : "active"}</td>
                  <td className="text-slate-500">{formatDate(key.created_at)}</td>
                  <td>
                    {key.revoked_at ? null : (
                      <button className="text-sm text-red-600 hover:underline" onClick={() => revoke(key.id)}>
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-8 text-sm text-slate-500">No API keys yet.</p>
      )}
    </>
  );
}
