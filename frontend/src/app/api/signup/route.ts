import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";

// Node runtime (not Edge): we need node:crypto for HMAC and a fetch loop
// that can stay open for minutes while bench provisions the tenant site.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PROVISIONER_URL = process.env.PROVISIONER_URL ?? "http://127.0.0.1:8001";
const WEBHOOK_SECRET = process.env.PROVISIONER_WEBHOOK_SECRET;
const POLL_INTERVAL_MS = Number(process.env.SIGNUP_POLL_INTERVAL_MS ?? 3000);
const POLL_TIMEOUT_MS = Number(process.env.SIGNUP_POLL_TIMEOUT_MS ?? 15 * 60 * 1000);

// Keep in sync with the PLANS list in app/register/page.tsx and with the
// self-serve tiers on the pricing page (components/PricingTable.tsx).
const PLAN_VALUES = ["starter", "professional", "enterprise"] as const;
type Plan = (typeof PLAN_VALUES)[number];

interface SignupBody {
  companyName?: string;
  adminEmail?: string;
  adminPassword?: string;
  plan?: string;
}

interface ProvisionAcceptedResponse {
  job_id: string;
  slug: string;
  site_name: string;
  status_url: string;
}

interface ProvisionJobStatus {
  job_id: string;
  slug: string;
  site_name: string;
  status: string;
  error: string | null;
  admin_email?: string;
  admin_password?: string;
}

function isValidPlan(value: unknown): value is Plan {
  return typeof value === "string" && (PLAN_VALUES as readonly string[]).includes(value);
}

export async function POST(req: NextRequest) {
  if (!WEBHOOK_SECRET) {
    console.error("PROVISIONER_WEBHOOK_SECRET is not set for the frontend server.");
    return NextResponse.json({ error: "Server misconfiguration." }, { status: 500 });
  }

  let body: SignupBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const { companyName, adminEmail, adminPassword, plan } = body;

  if (!companyName || !companyName.trim()) {
    return NextResponse.json({ error: "companyName is required." }, { status: 400 });
  }
  if (!adminEmail || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(adminEmail)) {
    return NextResponse.json({ error: "A valid adminEmail is required." }, { status: 400 });
  }
  if (!isValidPlan(plan)) {
    return NextResponse.json(
      { error: `plan must be one of: ${PLAN_VALUES.join(", ")}.` },
      { status: 400 }
    );
  }

  // `plan` rides along for future billing wiring — the provisioner doesn't
  // act on it yet (see provisioner/app.py); it's not persisted anywhere.
  const provisionPayload = {
    company_name: companyName.trim(),
    admin_email: adminEmail.trim(),
    ...(adminPassword ? { admin_password: adminPassword } : {}),
    plan,
  };

  const rawBody = JSON.stringify(provisionPayload);
  const signature = `sha256=${crypto.createHmac("sha256", WEBHOOK_SECRET).update(rawBody).digest("hex")}`;

  let provisionRes: Response;
  try {
    provisionRes = await fetch(`${PROVISIONER_URL}/webhooks/provision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Azeon-Signature": signature,
      },
      body: rawBody,
    });
  } catch (err) {
    console.error("Failed to reach provisioner:", err);
    return NextResponse.json(
      { error: "Could not reach the provisioning service. Please try again shortly." },
      { status: 502 }
    );
  }

  if (provisionRes.status !== 202) {
    const detail = await safeJson(provisionRes);
    return NextResponse.json(
      { error: detail?.error ?? "Provisioning request was rejected." },
      { status: provisionRes.status === 409 ? 409 : 502 }
    );
  }

  const accepted = (await provisionRes.json()) as ProvisionAcceptedResponse;
  const { job_id, status_url } = accepted;

  // Poll the provisioner's job status until it reports completed/failed, or
  // we hit our own ceiling.
  //
  // CAVEAT: this keeps the HTTP request open for as long as provisioning
  // takes (realistically a couple of minutes — bench new-site + installing
  // erpnext + azeon_core). That's fine on a long-running Node server (this
  // route is pinned to the Node runtime, not Edge, for exactly this reason)
  // but WOULD be killed early on a serverless host with a short function
  // timeout (e.g. Vercel's default). If this frontend ever moves to
  // serverless, replace this loop with client-side polling of a thin
  // /api/signup/status/[jobId] proxy instead of blocking here.
  const deadline = Date.now() + POLL_TIMEOUT_MS;

  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);

    let statusRes: Response;
    try {
      statusRes = await fetch(`${PROVISIONER_URL}${status_url}`, { cache: "no-store" });
    } catch (err) {
      console.error("Failed to poll provisioner job status:", err);
      continue; // transient network hiccup — keep trying until the deadline
    }

    if (!statusRes.ok) continue;

    const job = (await statusRes.json()) as ProvisionJobStatus;

    if (job.status === "completed") {
      return NextResponse.json({
        jobId: job_id,
        tenantUrl: `https://${job.site_name}`,
        adminEmail: job.admin_email,
        // admin_password is only present on the FIRST "completed" read from
        // the provisioner — it redacts it from memory right after. Passed
        // through once so the user can see their generated password.
        adminPassword: job.admin_password,
      });
    }

    if (job.status === "failed") {
      return NextResponse.json(
        { error: job.error ?? "Provisioning failed.", jobId: job_id },
        { status: 500 }
      );
    }
    // otherwise still in progress — keep polling
  }

  return NextResponse.json(
    {
      error: "Provisioning is taking longer than expected. Please check back shortly.",
      jobId: job_id,
      statusUrl: status_url,
    },
    { status: 202 }
  );
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function safeJson(res: Response): Promise<{ error?: string } | null> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}
