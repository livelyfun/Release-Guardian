export type Role = "owner" | "admin" | "developer" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  role: Role;
  created_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  repository_url: string | null;
  archived: boolean;
  created_at: string;
}

export interface Environment {
  id: string;
  project_id: string;
  name: string;
  base_url: string;
  is_production: boolean;
  created_at: string;
}

export type MonitorKind = "http" | "browser" | "lighthouse";

export interface Monitor {
  id: string;
  environment_id: string;
  name: string;
  kind: MonitorKind;
  target_url: string;
  interval_seconds: number;
  enabled: boolean;
  last_checked_at: string | null;
  created_at: string;
}

export type RunStatus = "pending" | "running" | "passed" | "failed" | "inconclusive";

export interface StepResult {
  id: string;
  step_index: number;
  name: string;
  status: RunStatus;
  duration_ms: number | null;
  error: string | null;
}

export interface Run {
  id: string;
  monitor_id: string;
  environment_id: string;
  status: RunStatus;
  trigger: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  summary: Record<string, unknown> | null;
  steps: StepResult[];
  created_at: string;
  screenshot_url: string | null;
  screenshot_key: string | null;
}

export interface Deployment {
  id: string;
  environment_id: string;
  commit_sha: string;
  branch: string | null;
  pull_request: number | null;
  status: string;
  deployed_at: string | null;
  created_at: string;
}

export type ComparisonVerdict = "regressed" | "improved" | "unchanged" | "new";

export interface DeploymentMonitorComparison {
  monitor_id: string;
  monitor_name: string;
  current_status: string | null;
  previous_status: string | null;
  current_duration_ms: number | null;
  previous_duration_ms: number | null;
  duration_delta_pct: number | null;
  verdict: ComparisonVerdict;
}

export interface DeploymentComparison {
  deployment_id: string;
  status: string;
  previous_known_good: Deployment | null;
  monitors: DeploymentMonitorComparison[];
  summary: Record<string, number>;
}

export type IncidentStatus = "open" | "acknowledged" | "resolved";
export type Severity = "critical" | "high" | "medium" | "low";

export interface Incident {
  id: string;
  workspace_id: string;
  project_id: string;
  environment_id: string | null;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  dedupe_key: string;
  opened_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export type ChannelKind = "webhook" | "email";

export interface NotificationChannel {
  id: string;
  workspace_id: string;
  kind: ChannelKind;
  config: Record<string, string>;
  enabled: boolean;
  created_at: string;
}

export interface NotificationAttempt {
  id: string;
  channel_id: string;
  incident_id: string | null;
  status: string;
  attempt: number;
  subject: string | null;
  body: string | null;
  next_attempt_at: string | null;
  error: string | null;
  created_at: string;
}

export interface Artifact {
  id: string;
  run_id: string;
  kind: string;
  storage_key: string;
  url: string | null;
  size_bytes: number | null;
  mime_type: string | null;
  created_at: string;
}

export interface UsageSummary {
  metric: string;
  quantity: number;
}

export interface EscalationRule {
  id: string;
  workspace_id: string;
  name: string;
  severity: Severity;
  minutes_to_escalate: number;
  channel_kind: ChannelKind;
  channel_config: Record<string, string>;
  is_enabled: boolean;
  created_at: string;
}

export interface MaintenanceWindow {
  id: string;
  workspace_id: string;
  project_id: string | null;
  environment_id: string | null;
  monitor_id: string | null;
  reason: string;
  starts_at: string;
  ends_at: string;
  created_at: string;
}

export interface ApiKey {
  id: string;
  workspace_id: string;
  name: string;
  prefix: string;
  scopes: string[];
  revoked_at: string | null;
  created_at: string;
  key?: string;
}
