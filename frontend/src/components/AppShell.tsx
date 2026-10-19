"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearTokens, isAuthenticated } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/projects", label: "Projects" },
  { href: "/monitors", label: "Monitors" },
  { href: "/tests", label: "Test runs" },
  { href: "/deployments", label: "Deployments" },
  { href: "/incidents", label: "Incidents" },
  { href: "/audits", label: "Audits" },
  { href: "/api-keys", label: "API keys" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (pathname === "/login") {
      setReady(true);
      return;
    }
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [pathname, router]);

  if (pathname === "/login") return <>{children}</>;

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading…
      </div>
    );
  }

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
      <aside className="hidden border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <div className="flex h-16 items-center gap-2 border-b border-slate-200 px-5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            RG
          </span>
          <div>
            <p className="text-sm font-semibold leading-tight">Release Guardian</p>
            <p className="text-[11px] text-slate-500">Reliability control plane</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-lg px-3 py-2 text-sm transition ${
                  active
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 p-3">
          <button onClick={logout} className="w-full rounded-lg px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50">
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white lg:hidden">
              RG
            </span>
            <select
              className="max-w-[220px] rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
              aria-label="Mobile navigation"
              onChange={(event) => router.push(event.target.value)}
              value={NAV.find((item) => pathname.startsWith(item.href))?.href ?? "/dashboard"}
            >
              {NAV.map((item) => (
                <option key={item.href} value={item.href}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-900">
            Sign out
          </button>
        </header>
        <main className="flex-1 px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
