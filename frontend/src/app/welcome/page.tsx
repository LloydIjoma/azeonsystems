'use client';

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Suspense } from 'react';

function WelcomeContent() {
  const searchParams = useSearchParams();
  const tenantUrl = searchParams.get('url') || '';

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-azeon-navy to-azeon-navy-dark px-6 py-12">
      <Link href="/" className="mb-8 font-heading text-2xl font-extrabold tracking-tight text-white">
        Azeon<span className="text-azeon-orange">Systems</span>
      </Link>

      <div className="w-full max-w-md space-y-6 rounded-2xl bg-white p-8 shadow-2xl text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
          <svg className="h-7 w-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <div>
          <h1 className="font-heading text-2xl font-extrabold text-gray-900">
            Your workspace is ready!
          </h1>
          <p className="mt-3 text-sm text-gray-600">
            We’ve provisioned your dedicated environment.
            {tenantUrl && (
              <>
                <br />
                <span className="mt-2 inline-block font-medium text-gray-800 break-all">
                  {tenantUrl}
                </span>
              </>
            )}
          </p>
        </div>

        <div className="space-y-3 pt-2">
          {tenantUrl ? (
            <a
              href={tenantUrl}
              className="block w-full rounded-md bg-azeon-orange py-3 text-sm font-semibold text-white shadow-sm hover:bg-azeon-orange-dark transition"
            >
              Go to my workspace
            </a>
          ) : (
            <p className="text-sm text-red-600">Workspace URL not found. Please contact support.</p>
          )}

          <Link
            href="/login"
            className="block w-full rounded-md border border-gray-300 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition"
          >
            Back to login
          </Link>
        </div>

        <p className="pt-4 text-xs text-gray-500 border-t border-gray-100">
          Use the admin email and password you just created to sign in.
        </p>
      </div>
    </div>
  );
}

export default function WelcomePage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading...</div>}>
      <WelcomeContent />
    </Suspense>
  );
}
