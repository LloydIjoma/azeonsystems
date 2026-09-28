import { NextResponse } from 'next/server';
import crypto from 'node:crypto';

// Bridges the marketing site's /register form to the Flask provisioner
// (see ../../../../../provisioner/app.py). The provisioner speaks
// "signed POST -> 202 + job_id -> poll for completion"; this route does
// the signing and polling on the caller's behalf and only ever returns a
// single final response, per the contract exercised by
// scripts/e2e_test.py's run_via_frontend_flow():
//   - 200 { tenantUrl } once the tenant site is fully provisioned
//   - non-200 { message } on validation, upstream, or timeout failure
//
// NOTE (see DEPLOYMENT.md step 6): this only works because in production
// Next.js runs as a persistent `next start` process (systemd), which can
// hold a connection open for the several minutes provisioning takes. If
// this route is ever deployed to a serverless platform with a short
// function timeout, it needs to change to client-side polling instead.
export const runtime = 'nodejs';

// Keep in sync with provisioner/app.py's PLAN_VALUES.
const PLAN_VALUES = new Set(['starter', 'professional', 'enterprise']);

interface SignupRequestBody {
  companyName?: unknown;
  email?: unknown;
  password?: unknown;
  plan?: unknown;
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
  steps: Array<{ step: string; ok: boolean; detail: string }>;
  error: string | null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function signPayload(secret: string, rawBody: string): string {
  const digest = crypto.createHmac('sha256', secret).update(rawBody).digest('hex');
  return `sha256=${digest}`;
}

export async function POST(request: Request) {
  const provisionerUrl = process.env.PROVISIONER_URL;
  const webhookSecret = process.env.PROVISIONER_WEBHOOK_SECRET;
  // Defaults mirror frontend/.env.example.
  const pollIntervalMs = Number(process.env.SIGNUP_POLL_INTERVAL_MS) || 3000;
  const pollTimeoutMs = Number(process.env.SIGNUP_POLL_TIMEOUT_MS) || 900000;

  if (!provisionerUrl || !webhookSecret) {
    console.error(
      'Signup API misconfigured: PROVISIONER_URL and/or PROVISIONER_WEBHOOK_SECRET are not set.'
    );
    return NextResponse.json(
      { message: 'Signup is temporarily unavailable. Please try again later.' },
      { status: 500 }
    );
  }

  let body: SignupRequestBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: 'Invalid JSON body' }, { status: 400 });
  }

  const { companyName, email, password, plan } = body ?? {};

  if (!companyName || typeof companyName !== 'string') {
    return NextResponse.json({ message: 'companyName is required' }, { status: 400 });
  }
  if (!email || typeof email !== 'string') {
    return NextResponse.json({ message: 'email is required' }, { status: 400 });
  }
  if (!password || typeof password !== 'string') {
    return NextResponse.json({ message: 'password is required' }, { status: 400 });
  }

  let normalizedPlan = 'starter';
  if (typeof plan === 'string' && plan.trim()) {
    const lower = plan.trim().toLowerCase();
    if (!PLAN_VALUES.has(lower)) {
      return NextResponse.json(
        { message: `plan must be one of: ${Array.from(PLAN_VALUES).join(', ')}` },
        { status: 400 }
      );
    }
    normalizedPlan = lower;
  }

  // Field names here match what provisioner/app.py's /webhooks/provision
  // expects (snake_case, admin_* prefix), not the frontend form's own
  // camelCase field names.
  const rawBody = JSON.stringify({
    company_name: companyName,
    admin_email: email,
    admin_password: password,
    plan: normalizedPlan,
  });
  const signature = signPayload(webhookSecret, rawBody);

  let accepted: ProvisionAcceptedResponse;
  try {
    const provisionRes = await fetch(`${provisionerUrl}/webhooks/provision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Azeon-Signature': signature,
      },
      body: rawBody,
    });

    const data = await provisionRes.json().catch(() => null);

    if (provisionRes.status !== 202) {
      const message = (data && (data.error || data.message)) || 'Failed to start provisioning';
      return NextResponse.json({ message }, { status: provisionRes.status || 502 });
    }

    if (!data || !data.job_id || !data.status_url || !data.site_name) {
      throw new Error('Provisioner accepted the request but returned an unexpected response');
    }

    accepted = data;
  } catch (error: any) {
    console.error('Signup API: failed to reach provisioner', error);
    return NextResponse.json(
      { message: 'Could not reach the provisioning service. Please try again.' },
      { status: 502 }
    );
  }

  const statusUrl = new URL(accepted.status_url, provisionerUrl).toString();
  const deadline = Date.now() + pollTimeoutMs;
  let job: ProvisionJobStatus | null = null;

  try {
    while (Date.now() < deadline) {
      await sleep(pollIntervalMs);

      const statusRes = await fetch(statusUrl, { method: 'GET' });
      if (!statusRes.ok) {
        // Transient poll failure — keep trying until the deadline.
        continue;
      }

      const parsed: ProvisionJobStatus = await statusRes.json();
      if (parsed.status === 'completed' || parsed.status === 'failed') {
        job = parsed;
        break;
      }
    }
  } catch (error: any) {
    console.error('Signup API: error while polling provisioning status', error);
    return NextResponse.json(
      {
        message:
          'Lost contact with the provisioning service while your tenant was being created.',
      },
      { status: 502 }
    );
  }

  if (!job) {
    return NextResponse.json(
      {
        message: `Provisioning is taking longer than expected. Please contact support with job id ${accepted.job_id}.`,
      },
      { status: 504 }
    );
  }

  if (job.status === 'failed') {
    return NextResponse.json({ message: job.error || 'Provisioning failed' }, { status: 502 });
  }

  return NextResponse.json({ tenantUrl: `https://${job.site_name}` }, { status: 200 });
}
