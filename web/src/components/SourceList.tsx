import { Badge } from "./ui";

export type Source = { key: string; title: string; publisher: string | null; year: number | null; url: string | null; verified: boolean };

export function SourceList({ sources }: { sources: Source[] }) {
  return (
    <ul className="space-y-2 text-sm">
      {sources.map((s) => (
        <li key={s.key} id={s.key}>
          {s.url ? <a className="text-brand underline" href={s.url} target="_blank" rel="noreferrer">{s.title}</a> : <span className="font-semibold">{s.title}</span>}
          <span className="text-muted"> · {[s.publisher, s.year].filter(Boolean).join(", ")}</span>
          {!s.verified && <Badge tone="amber" className="ml-1">pending editorial check</Badge>}
        </li>
      ))}
    </ul>
  );
}
