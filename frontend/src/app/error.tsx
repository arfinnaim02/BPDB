"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="loading-page"><h1>The workspace could not load</h1><p>Check the API connection and try again.</p><button className="button primary" onClick={reset}>Try again</button></main>;
}
