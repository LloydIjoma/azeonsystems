'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

type Status = 'form' | 'submitting' | 'error';

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-azeon-navy to-azeon-navy-dark px-6 py-12">
      <Link href="/" className="mb-8 font-heading text-2xl font-extrabold tracking-tight text-white">
        Azeon<span className="text-azeon-orange">Systems</span>
      </Link>
      <div className="w-full max-w-md space-y-6 rounded-2xl bg-white p-8 shadow-2xl">
        {children}
      </div>
    </div>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [plan, setPlan] = useState('Starter');
  const [status, setStatus] = useState<Status>('form');
  const [error, setError] = useState('');

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setStatus('submitting');

    try {
      const res = await fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companyName, email, password, plan }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.message || 'Registration failed');
        setStatus('error');
        return;
      }

      // Redirect to the custom welcome page we control
      const tenantUrl = data.tenantUrl || '';
      router.push(`/welcome?url=${encodeURIComponent(tenantUrl)}`);
    } catch {
      setError('Something went wrong. Please try again.');
      setStatus('error');
    }
  };

  if (status === 'submitting') {
    return (
      <Shell>
        <div className="space-y-6 text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-azeon-orange border-t-transparent" />
          <div>
            <h2 className="font-heading text-2xl font-extrabold text-gray-900">
              Provisioning your workspace...
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              This can take a few minutes while we set up your dedicated environment.
              Please don&apos;t close or refresh this tab.
            </p>
          </div>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="text-center">
        <h2 className="font-heading text-2xl font-extrabold text-gray-900">Start your free trial</h2>
        <p className="mt-2 text-sm text-gray-600">No credit card required.</p>
      </div>

      {status === 'error' && error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      <form className="space-y-6" onSubmit={handleRegister} autoComplete="on">
        <div>
          <label className="block text-sm font-medium text-gray-700">Company name</label>
          <input
            type="text"
            name="company"
            required
            autoComplete="organization"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-azeon-orange focus:outline-none"
            placeholder="Your company name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Admin email</label>
          <input
            type="email"
            name="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-azeon-orange focus:outline-none"
            placeholder="you@company.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Admin password</label>
          <input
            type="password"
            name="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-azeon-orange focus:outline-none"
            placeholder="••••••••"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Plan</label>
          <select
            name="plan"
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-azeon-orange focus:outline-none bg-white"
          >
            <option value="Starter">Starter</option>
            <option value="Professional">Professional</option>
            <option value="Enterprise">Enterprise</option>
          </select>
        </div>

        <button
          type="submit"
          className="w-full rounded-md bg-azeon-orange py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-azeon-orange-dark transition"
        >
          Start Free Trial
        </button>
      </form>

      <div className="text-center text-sm text-gray-600 pt-4 border-t border-gray-100">
        Already have an account?{' '}
        <Link href="/login" className="font-semibold text-azeon-orange hover:underline">
          Sign in
        </Link>
      </div>
    </Shell>
  );
}
