"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiClient, ApiError, setTokens } from "@/lib/api";

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: { id: string; email: string; name: string };
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result =
        mode === "login"
          ? await apiClient.post<AuthResponse>("/auth/login", { email, password })
          : await apiClient.post<AuthResponse>("/auth/register", { email, password, name });
      setTokens(result.access_token, result.refresh_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-600 text-base font-bold text-white">
            RG
          </span>
          <h1 className="text-xl font-semibold">Release Guardian</h1>
          <p className="text-sm text-slate-500">Website reliability and release verification</p>
        </div>

        <form onSubmit={submit} className="card space-y-4 p-6">
          <div className="flex rounded-lg bg-slate-100 p-1 text-sm">
            {(["login", "register"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setMode(value)}
                className={`flex-1 rounded-md px-3 py-1.5 capitalize transition ${
                  mode === value ? "bg-white font-medium shadow-sm" : "text-slate-500"
                }`}
              >
                {value}
              </button>
            ))}
          </div>

          {mode === "register" ? (
            <div>
              <label className="label" htmlFor="name">
                Name
              </label>
              <input
                id="name"
                className="input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>
          ) : null}

          <div>
            <label className="label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              required
            />
          </div>

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
