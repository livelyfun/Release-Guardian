"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, ErrorNotice, PageHeader, Spinner } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api";
import { useActiveWorkspaceId, useApi } from "@/lib/hooks";
import type {
  ChannelKind,
  EscalationRule,
  MaintenanceWindow,
  Member,
  NotificationAttempt,
  NotificationChannel,
  Role,
  Severity,
  User,
  Workspace,
} from "@/lib/types";

const ROLES: Role[] = ["owner", "admin", "developer", "viewer"];

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

  const escalations = useApi<EscalationRule[]>(
    activeWorkspace ? `/workspaces/${activeWorkspace}/escalation-rules` : null,
  );
  const [escName, setEscName] = useState("");
  const [escSeverity, setEscSeverity] = useState<Severity>("high");
  const [escMinutes, setEscMinutes] = useState("30");
  const [escKind, setEscKind] = useState<ChannelKind>("webhook");
  const [escTarget, setEscTarget] = useState("");
  const [escError, setEscError] = useState<string | null>(null);
  const [escBusy, setEscBusy] = useState(false);

  const windows = useApi<MaintenanceWindow[]>(
    activeWorkspace ? `/workspaces/${activeWorkspace}/maintenance-windows` : null,
  );
  const [windowReason, setWindowReason] = useState("");
  const [windowStart, setWindowStart] = useState("");
  const [windowEnd, setWindowEnd] = useState("");
  const [windowError, setWindowError] = useState<string | null>(null);
  const [windowBusy, setWindowBusy] = useState(false);

  const members = useApi<Member[]>(
    activeWorkspace ? `/workspaces/${activeWorkspace}/members` : null,
  );
  const [memberEmail, setMemberEmail] = useState("");
  const [memberRole, setMemberRole] = useState<Role>("viewer");
  const [memberError, setMemberError] = useState<string | null>(null);
  const [memberBusy, setMemberBusy] = useState(false);

  useEffect(() => {
    setActiveId(window.localStorage.getItem("rg_workspace_id"));
  }, []);

  useEffect(() => {
    const start = new Date();
    const end = new Date(start.getTime() + 2 * 60 * 60 * 1000);
    const local = (date: Date) => {
      const offset = date.getTimezoneOffset() * 60 * 1000;
      return new Date(date.getTime() - offset).toISOString().slice(0, 16);
    };
    setWindowStart(local(start));
    setWindowEnd(local(end));
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

  async function inviteMember(event: React.FormEvent) {
    event.preventDefault();
    if (!activeWorkspace) return;
    setMemberBusy(true);
    setMemberError(null);
    try {
      await apiClient.post(`/workspaces/${activeWorkspace}/members`, {
        email: memberEmail,
        role: memberRole,
      });
      setMemberEmail("");
      setMemberRole("viewer");
      members.reload();
    } catch (err) {
      setMemberError(err instanceof ApiError ? err.message : "Failed to add member");
    } finally {
      setMemberBusy(false);
    }
  }

  async function changeMemberRole(member: Member, role: Role) {
    setMemberBusy(true);
    setMemberError(null);
    try {
      await apiClient.patch(`/workspaces/${member.workspace_id}/members/${member.id}`, {
        role,
      });
      members.reload();
    } catch (err) {
      setMemberError(err instanceof ApiError ? err.message : "Failed to update member");
    } finally {
      setMemberBusy(false);
    }
  }

  async function removeMember(member: Member) {
    if (!window.confirm(`Remove ${member.email ?? member.user_id} from this workspace?`)) {
      return;
    }
    setMemberBusy(true);
    setMemberError(null);
    try {
      await apiClient.del(`/workspaces/${member.workspace_id}/members/${member.id}`);
      members.reload();
    } catch (err) {
      setMemberError(err instanceof ApiError ? err.message : "Failed to remove member");
    } finally {
      setMemberBusy(false);
    }
  }

  async function createEscalation(event: React.FormEvent) {
    event.preventDefault();
    if (!activeWorkspace) return;
    setEscBusy(true);
    setEscError(null);
    try {
      const config = escKind === "webhook" ? { url: escTarget } : { to: escTarget };
      await apiClient.post(`/workspaces/${activeWorkspace}/escalation-rules`, {
        name: escName,
        severity: escSeverity,
        minutes_to_escalate: Number(escMinutes),
        kind: escKind,
        config,
      });
      setEscName("");
      setEscTarget("");
      escalations.reload();
    } catch (err) {
      setEscError(err instanceof ApiError ? err.message : "Failed to create escalation rule");
    } finally {
      setEscBusy(false);
    }
  }

  async function removeEscalation(id: string) {
    setEscError(null);
    try {
      await apiClient.del(`/escalation-rules/${id}`);
      escalations.reload();
    } catch (err) {
      setEscError(err instanceof ApiError ? err.message : "Failed to delete escalation rule");
    }
  }

  async function createWindow(event: React.FormEvent) {
    event.preventDefault();
    if (!activeWorkspace) return;
    setWindowBusy(true);
    setWindowError(null);
    try {
      const starts = new Date(windowStart);
      const ends = new Date(windowEnd);
      if (!(starts < ends)) {
        throw new ApiError(400, "End time must be after start time");
      }
      await apiClient.post(`/workspaces/${activeWorkspace}/maintenance-windows`, {
        reason: windowReason,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
      });
      setWindowReason("");
      windows.reload();
    } catch (err) {
      setWindowError(err instanceof ApiError ? err.message : "Failed to create maintenance window");
    } finally {
      setWindowBusy(false);
    }
  }

  async function removeWindow(id: string) {
    setWindowError(null);
    try {
      await apiClient.del(`/maintenance-windows/${id}`);
      windows.reload();
    } catch (err) {
      setWindowError(err instanceof ApiError ? err.message : "Failed to delete maintenance window");
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
        <h2 className="mb-1 text-sm font-semibold">Team</h2>
        <p className="mb-4 text-sm text-slate-500">
          Members and roles for the active workspace. Owners manage owners; admins
          manage other roles.
        </p>

        {!activeWorkspace ? (
          <p className="text-sm text-slate-500">Select a workspace to manage members.</p>
        ) : members.loading ? (
          <Spinner />
        ) : members.error ? (
          <ErrorNotice message={members.error} />
        ) : (
          <>
            {members.data && members.data.length > 0 ? (
              <ul className="space-y-2">
                {members.data.map((member) => (
                  <li
                    key={member.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium">
                        {member.name ?? member.user_id}
                        {me.data?.id === member.user_id ? (
                          <span className="ml-2 text-xs font-normal text-slate-500">(you)</span>
                        ) : null}
                      </p>
                      <p className="break-all text-xs text-slate-500">
                        {member.email ?? member.user_id}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <select
                        aria-label={`Role for ${member.email ?? member.user_id}`}
                        className="input w-auto py-1 text-xs"
                        value={member.role}
                        disabled={memberBusy}
                        onChange={(event) =>
                          changeMemberRole(member, event.target.value as Role)
                        }
                      >
                        {ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      <button
                        className="text-xs text-red-600 hover:underline"
                        disabled={memberBusy}
                        onClick={() => removeMember(member)}
                      >
                        Remove
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No members found.</p>
            )}

            {memberError ? (
              <div className="mt-4">
                <ErrorNotice message={memberError} />
              </div>
            ) : null}

            <form
              onSubmit={inviteMember}
              className="mt-5 space-y-3 border-t border-slate-100 pt-5"
            >
              <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
                <div>
                  <label className="label" htmlFor="member-email">
                    Add member by email
                  </label>
                  <input
                    id="member-email"
                    className="input"
                    type="email"
                    value={memberEmail}
                    onChange={(event) => setMemberEmail(event.target.value)}
                    placeholder="teammate@example.com"
                    required
                  />
                </div>
                <div>
                  <label className="label" htmlFor="member-role">
                    Role
                  </label>
                  <select
                    id="member-role"
                    className="input"
                    value={memberRole}
                    onChange={(event) => setMemberRole(event.target.value as Role)}
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <button className="btn-primary" disabled={memberBusy}>
                {memberBusy ? "Saving…" : "Add member"}
              </button>
            </form>
          </>
        )}
      </Card>

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

      <Card className="mt-6 p-6">
        <h2 className="mb-1 text-sm font-semibold">Escalation rules</h2>
        <p className="mb-4 text-sm text-slate-500">
          Page another destination when an incident stays open for a set time. Rules fire
          at most once per incident, latest threshold last.
        </p>

        {!activeWorkspace ? (
          <p className="text-sm text-slate-500">Select a workspace to manage escalations.</p>
        ) : escalations.loading ? (
          <Spinner />
        ) : escalations.error ? (
          <ErrorNotice message={escalations.error} />
        ) : escalations.data && escalations.data.length > 0 ? (
          <ul className="space-y-2">
            {escalations.data.map((rule) => (
              <li
                key={rule.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium">
                    {rule.name}
                    <span className="ml-2 text-xs uppercase text-slate-500">
                      {rule.severity}
                    </span>
                  </p>
                  <p className="break-all text-xs text-slate-500">
                    after {rule.minutes_to_escalate} min via {rule.channel_kind} ·{" "}
                    {rule.channel_config.url ?? rule.channel_config.to ?? "No target"}
                  </p>
                </div>
                <button
                  className="text-xs text-red-600 hover:underline"
                  onClick={() => removeEscalation(rule.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No escalation rules yet.</p>
        )}

        <form onSubmit={createEscalation} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="label" htmlFor="escalation-name">
                Rule name
              </label>
              <input
                id="escalation-name"
                className="input"
                value={escName}
                onChange={(event) => setEscName(event.target.value)}
                placeholder="page-oncall"
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="escalation-severity">
                Severity
              </label>
              <select
                id="escalation-severity"
                className="input"
                value={escSeverity}
                onChange={(event) => setEscSeverity(event.target.value as Severity)}
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="escalation-minutes">
                After (minutes)
              </label>
              <input
                id="escalation-minutes"
                className="input"
                type="number"
                min={0}
                max={10080}
                value={escMinutes}
                onChange={(event) => setEscMinutes(event.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
            <div>
              <label className="label" htmlFor="escalation-kind">
                Channel
              </label>
              <select
                id="escalation-kind"
                className="input"
                value={escKind}
                onChange={(event) => setEscKind(event.target.value as ChannelKind)}
              >
                <option value="webhook">Webhook</option>
                <option value="email">Email</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="escalation-target">
                {escKind === "webhook" ? "Webhook URL" : "Email recipient"}
              </label>
              <input
                id="escalation-target"
                className="input"
                value={escTarget}
                onChange={(event) => setEscTarget(event.target.value)}
                placeholder={
                  escKind === "webhook"
                    ? "https://hooks.example.com/escalation"
                    : "manager@example.com"
                }
                required
              />
            </div>
          </div>
          {escError ? <ErrorNotice message={escError} /> : null}
          <button className="btn-primary" disabled={escBusy || !activeWorkspace}>
            {escBusy ? "Adding…" : "Add escalation rule"}
          </button>
        </form>
      </Card>

      <Card className="mt-6 p-6">
        <h2 className="mb-1 text-sm font-semibold">Maintenance windows</h2>
        <p className="mb-4 text-sm text-slate-500">
          Checks keep running, but incidents are suppressed while a window is active.
          Windows created here apply to the whole workspace.
        </p>

        {!activeWorkspace ? (
          <p className="text-sm text-slate-500">Select a workspace to manage windows.</p>
        ) : windows.loading ? (
          <Spinner />
        ) : windows.error ? (
          <ErrorNotice message={windows.error} />
        ) : windows.data && windows.data.length > 0 ? (
          <ul className="space-y-2">
            {windows.data.map((window) => (
              <li
                key={window.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium">{window.reason || "Scheduled maintenance"}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(window.starts_at).toLocaleString()} →{" "}
                    {new Date(window.ends_at).toLocaleString()}
                  </p>
                </div>
                <button
                  className="text-xs text-red-600 hover:underline"
                  onClick={() => removeWindow(window.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No maintenance windows scheduled.</p>
        )}

        <form onSubmit={createWindow} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
          <div>
            <label className="label" htmlFor="window-reason">
              Reason
            </label>
            <input
              id="window-reason"
              className="input"
              value={windowReason}
              onChange={(event) => setWindowReason(event.target.value)}
              placeholder="Production deploy"
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="window-start">
                Starts
              </label>
              <input
                id="window-start"
                className="input"
                type="datetime-local"
                value={windowStart}
                onChange={(event) => setWindowStart(event.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="window-end">
                Ends
              </label>
              <input
                id="window-end"
                className="input"
                type="datetime-local"
                value={windowEnd}
                onChange={(event) => setWindowEnd(event.target.value)}
                required
              />
            </div>
          </div>
          {windowError ? <ErrorNotice message={windowError} /> : null}
          <button className="btn-primary" disabled={windowBusy || !activeWorkspace}>
            {windowBusy ? "Scheduling…" : "Schedule window"}
          </button>
        </form>
      </Card>
    </>
  );
}
