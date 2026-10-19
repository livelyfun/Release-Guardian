"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, ErrorNotice, PageHeader, Spinner } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type {
  ChannelKind,
  NotificationAttempt,
  NotificationChannel,
  User,
  Workspace,
} from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const me = useApi<User>("/auth/me");
  const workspaces = useApi<Workspace[]>("/workspaces");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeWorkspace = useActiveWorkspaceId();
  const channels = useApi<NotificationChannel[]>(
    activeWorkspace ? `/workspaces/${activeWorkspace}/notification-channels` : null,
  );
  const [channelKind, setChannelKind] = useState<ChannelKind>("webhook");
  const [channelTarget, setChannelTarget] = useState("");
  const [channelError, setChannelError] = useState<string | null>(null);
  const [channelBusy, setChannelBusy] = useState(false);
  const [attemptsFor, setAttemptsFor] = useState<string | null>(null);
  const attempts = useApi<NotificationAttempt[]>(
    attemptsFor ? `/notification-channels/${attemptsFor}/attempts` : null,
  );

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

  async function createChannel(event: React.FormEvent) {
    event.preventDefault();
    if (!activeWorkspace) return;
    setChannelBusy(true);
    setChannelError(null);
    try {
      const config = channelKind === "webhook" ? { url: channelTarget } : { to: channelTarget };
      await apiClient.post(`/workspaces/${activeWorkspace}/notification-channels`, {
        kind: channelKind,
        config,
      });
      setChannelTarget("");
      channels.reload();
    } catch (err) {
      setChannelError(err instanceof ApiError ? err.message : "Failed to create channel");
    } finally {
      setChannelBusy(false);
    }
  }

  async function toggleChannel(channel: NotificationChannel) {
    setChannelError(null);
    try {
      await apiClient.patch(`/notification-channels/${channel.id}`, {
        enabled: !channel.enabled,
      });
      channels.reload();
    } catch (err) {
      setChannelError(err instanceof ApiError ? err.message : "Failed to update channel");
    }
  }

  async function removeChannel(id: string) {
    setChannelError(null);
    try {
      await apiClient.del(`/notification-channels/${id}`);
      if (attemptsFor === id) setAttemptsFor(null);
      channels.reload();
    } catch (err) {
      setChannelError(err instanceof ApiError ? err.message : "Failed to delete channel");
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

      <Card className="mt-6 p-6">
        <h2 className="mb-1 text-sm font-semibold">Notification channels</h2>
        <p className="mb-4 text-sm text-slate-500">
          Alert destinations for incidents in the active workspace.
        </p>

        {!activeWorkspace ? (
          <p className="text-sm text-slate-500">Select a workspace to manage channels.</p>
        ) : channels.loading ? (
          <Spinner />
        ) : channels.error ? (
          <ErrorNotice message={channels.error} />
        ) : channels.data && channels.data.length > 0 ? (
          <ul className="space-y-2">
            {channels.data.map((channel) => (
              <li
                key={channel.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium">
                    {channel.kind}
                    {channel.enabled ? "" : " (disabled)"}
                  </p>
                  <p className="break-all text-xs text-slate-500">
                    {channel.config.url ?? channel.config.to ?? "No target configured"}
                  </p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <button
                    className="text-brand-600 hover:underline"
                    onClick={() => setAttemptsFor(attemptsFor === channel.id ? null : channel.id)}
                  >
                    Attempts
                  </button>
                  <button
                    className="text-brand-600 hover:underline"
                    onClick={() => toggleChannel(channel)}
                  >
                    {channel.enabled ? "Disable" : "Enable"}
                  </button>
                  <button
                    className="text-red-600 hover:underline"
                    onClick={() => removeChannel(channel.id)}
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No notification channels yet.</p>
        )}

        {attemptsFor ? (
          <div className="mt-4 rounded-lg bg-slate-50 p-3 text-sm">
            {attempts.loading ? (
              <Spinner />
            ) : attempts.data && attempts.data.length > 0 ? (
              <ul className="space-y-1">
                {attempts.data.map((attempt) => (
                  <li key={attempt.id} className="flex justify-between gap-3">
                    <span>
                      {attempt.status}
                      {attempt.error ? ` — ${attempt.error}` : ""}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(attempt.created_at).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-500">No delivery attempts yet.</p>
            )}
          </div>
        ) : null}

        <form onSubmit={createChannel} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
          <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
            <div>
              <label className="label" htmlFor="channel-kind">
                Channel
              </label>
              <select
                id="channel-kind"
                className="input"
                value={channelKind}
                onChange={(event) => setChannelKind(event.target.value as ChannelKind)}
              >
                <option value="webhook">Webhook</option>
                <option value="email">Email</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="channel-target">
                {channelKind === "webhook" ? "Webhook URL" : "Email recipient"}
              </label>
              <input
                id="channel-target"
                className="input"
                value={channelTarget}
                onChange={(event) => setChannelTarget(event.target.value)}
                placeholder={
                  channelKind === "webhook"
                    ? "https://hooks.example.com/release-guardian"
                    : "oncall@example.com"
                }
                required
              />
            </div>
          </div>
          {channelError ? <ErrorNotice message={channelError} /> : null}
          <button className="btn-primary" disabled={channelBusy || !activeWorkspace}>
            {channelBusy ? "Adding…" : "Add channel"}
          </button>
        </form>
      </Card>
    </>
  );
}
