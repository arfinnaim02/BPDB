"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="p-10"><h1>Could not load system status</h1>
    <button className="mt-4 underline" onClick={reset}>Try again</button></main>;
}
