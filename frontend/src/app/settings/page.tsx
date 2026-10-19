"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, ErrorNotice, PageHeader, Spinner } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { User, Workspace } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const me = useApi<User>("/auth/me");
  const workspaces = useApi<Workspace[]>("/workspaces");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    setActiveId(window.localStorage.getItem("rg_workspace_id"));
  }, []);

  function selectWorkspace(id: string) {
    window.localStorage.setItem("rg_workspace_id", id);
    setActiveId(id);
    window.dispatchEvent(new Event("rg-workspace-changed"));
    router.refresh();
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const workspace = await apiClient.post<Workspace>("/workspaces", { name });
      setName("");
      selectWorkspace(workspace.id);
      workspaces.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create workspace");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Settings" description="Profile, workspaces, and active context." />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-4 text-sm font-semibold">Profile</h2>
          {me.loading ? (
            <Spinner />
          ) : me.error ? (
            <ErrorNotice message={me.error} />
          ) : me.data ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Name</dt>
                <dd>{me.data.name}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Email</dt>
                <dd>{me.data.email}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Email verified</dt>
                <dd>{me.data.email_verified ? "Yes" : "No"}</dd>
              </div>
            </dl>
          ) : null}
        </Card>

        <Card className="p-6">
          <h2 className="mb-4 text-sm font-semibold">Workspaces</h2>
          {workspaces.loading ? (
            <Spinner />
          ) : workspaces.data && workspaces.data.length > 0 ? (
            <ul className="space-y-2">
              {workspaces.data.map((workspace) => (
                <li
                  key={workspace.id}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                    workspace.id === activeId ? "border-brand-300 bg-brand-50" : "border-slate-200"
                  }`}
                >
                  <div>
                    <p className="font-medium">{workspace.name}</p>
                    <p className="text-xs text-slate-500">{workspace.role}</p>
                  </div>
                  {workspace.id === activeId ? (
                    <span className="text-xs text-brand-600">Active</span>
                  ) : (
                    <button className="text-xs text-brand-600 hover:underline" onClick={() => selectWorkspace(workspace.id)}>
                      Use
                    </button>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No workspaces yet.</p>
          )}

          <form onSubmit={create} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <div>
              <label className="label" htmlFor="workspace-name">
                New workspace
              </label>
              <input
                id="workspace-name"
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>
            {error ? <ErrorNotice message={error} /> : null}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Creating…" : "Create workspace"}
            </button>
          </form>
        </Card>
      </div>
    </>
  );
}
