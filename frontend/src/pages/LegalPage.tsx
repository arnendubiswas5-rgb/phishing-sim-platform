import { Link } from "react-router-dom";
import type { ReactNode } from "react";

/** Shared frame for the public Privacy and Terms pages: readable column,
 *  neutral styling, and a link back to sign in. */
export function LegalPage({ title, updated, children }: { title: string; updated: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-black px-4 py-10">
      <div className="mx-auto max-w-2xl rounded-xl bg-neutral-900 p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-neutral-100">{title}</h1>
        <p className="mt-1 text-sm text-neutral-400">Last updated: {updated}</p>
        <div className="mt-6 space-y-5 text-sm leading-6 text-neutral-200">{children}</div>
        <div className="mt-8 border-t border-neutral-800 pt-4 text-sm">
          <Link to="/login" className="font-medium text-green-400 hover:text-green-300 hover:underline">
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}

export function Section({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-1 text-base font-semibold text-neutral-100">{heading}</h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}
