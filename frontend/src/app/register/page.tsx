"use client";

import { Suspense, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { slugify } from "@/lib/slugify";

// Keep in sync with PLAN_VALUES in app/api/signup/route.ts and with the
// self-serve tiers on the pricing page (frontend/src/components/PricingTable.tsx).
// "Custom" is intentionally excluded — it's sales-negotiated, not self-serve,
// and its pricing-page CTA links to #demo instead of here.
const PLANS = [
  { value: "starter", label: "Starter" },
  { value: "professional", label: "Professional" },
  { value: "enterprise", label: "Enterprise" },
] as const;

type Plan = (typeof PLANS)[number]["value"];

function isPlan(value: string | null): value is Plan {
  return PLANS.some((p) => p.value === value);
}

type SubmitState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success"; tenantUrl: string; adminPassword?: string }
  | { status: "error"; message: string };

function RegisterForm() {
  // Pre-selects whichever tier the visitor clicked on the pricing page
  // (e.g. /register?plan=enterprise); falls back to the most popular tier.
  const searchParams = useSearchParams();
  const requestedPlan = searchParams.get("plan");

  const [companyName, setCompanyName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [plan, setPlan] = useState<Plan>(isPlan(requestedPlan) ? requestedPlan : "professional");
  const [state, setState] = useState<SubmitState>({ status: "idle" });

  const slugPreview = useMemo(() => slugify(companyName), [companyName]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    if (!slugPreview.isValid) {
      setState({
        status: "error",
        message: "Please choose a company name that produces a valid subdomain.",
      });
      return;
    }

    setState({ status: "submitting" });

    try {
      const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          companyName,
          adminEmail,
          adminPassword: adminPassword || undefined,
          plan,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setState({ status: "error", message: data.error ?? "Something went wrong. Please try again." });
        return;
      }

      setState({ status: "success", tenantUrl: data.tenantUrl, adminPassword: data.adminPassword });
    } catch {
      setState({ status: "error", message: "Could not reach the server. Please try again." });
    }
  }

  if (state.status === "success") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-md rounded-2xl bg-white p-10 text-center shadow-sm">
          <h1 className="font-heading text-2xl font-bold text-azeon-navy">Your workspace is ready 🎉</h1>
          <p className="mt-4 font-body text-gray-600">
            Sign in at{" "}
            <a href={state.tenantUrl} className="font-semibold text-azeon-orange underline">
              {state.tenantUrl}
            </a>
          </p>
          {state.adminPassword && (
            <p className="mt-4 rounded-md bg-gray-50 p-3 font-body text-sm text-gray-700">
              Admin password: <code className="font-mono">{state.adminPassword}</code>
              <br />
              Save this now — it won&apos;t be shown again.
            </p>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6 py-16">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-2xl bg-white p-10 shadow-sm">
        <h1 className="font-heading text-2xl font-bold text-azeon-navy">Start your free trial</h1>
        <p className="mt-2 font-body text-sm text-gray-500">No credit card required.</p>

        <div className="mt-8 space-y-5">
          <div>
            <label className="block font-body text-sm font-semibold text-gray-700">Company name</label>
            <input
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 font-body text-sm focus:border-azeon-navy focus:outline-none focus:ring-1 focus:ring-azeon-navy"
              placeholder="Acme Corp"
            />
            <p className="mt-2 font-body text-xs text-gray-500">
              Your workspace:{" "}
              <span className={slugPreview.isValid ? "font-semibold text-azeon-navy" : "font-semibold text-red-500"}>
                https://{slugPreview.slug || "yourcompany"}.azeonsystems.com.ng
              </span>
              {!slugPreview.isValid && slugPreview.slug && (
                <span className="ml-1 text-red-500">
                  ({slugPreview.reason === "reserved" ? "that name is reserved" : "invalid characters"})
                </span>
              )}
            </p>
          </div>

          <div>
            <label className="block font-body text-sm font-semibold text-gray-700">Admin email</label>
            <input
              required
              type="email"
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 font-body text-sm focus:border-azeon-navy focus:outline-none focus:ring-1 focus:ring-azeon-navy"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label className="block font-body text-sm font-semibold text-gray-700">Admin password</label>
            <input
              type="password"
              minLength={8}
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 font-body text-sm focus:border-azeon-navy focus:outline-none focus:ring-1 focus:ring-azeon-navy"
              placeholder="Leave blank to auto-generate"
            />
          </div>

          <div>
            <label className="block font-body text-sm font-semibold text-gray-700">Plan</label>
            <select
              value={plan}
              onChange={(e) => setPlan(e.target.value as Plan)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 font-body text-sm focus:border-azeon-navy focus:outline-none focus:ring-1 focus:ring-azeon-navy"
            >
              {PLANS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {state.status === "error" && (
            <p className="rounded-md bg-red-50 px-3 py-2 font-body text-sm text-red-600">{state.message}</p>
          )}

          <button
            type="submit"
            disabled={state.status === "submitting" || !slugPreview.isValid}
            className="w-full rounded-md bg-azeon-orange px-4 py-3 font-body text-sm font-semibold text-white transition hover:bg-azeon-orange-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {state.status === "submitting" ? "Setting up your workspace…" : "Start Free Trial"}
          </button>
          {state.status === "submitting" && (
            <p className="text-center font-body text-xs text-gray-500">
              This can take a couple of minutes — we&apos;re creating your dedicated workspace.
            </p>
          )}
        </div>
      </form>
    </main>
  );
}

export default function RegisterPage() {
  // useSearchParams() requires a Suspense boundary so the page can still be
  // statically prerendered up to that point.
  return (
    <Suspense fallback={null}>
      <RegisterForm />
    </Suspense>
  );
}
