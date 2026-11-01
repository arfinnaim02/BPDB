export default function Loading() {
  return <main className="loading-page" aria-busy="true"><div className="spinner"/><h1>Reading the dataset…</h1><p>Fetching current canonical records from the API.</p></main>;
}
