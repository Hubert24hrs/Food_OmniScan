"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, ErrorBox, Field, inputCls, Page } from "@/components/ui";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [field, setField] = useState("ingredients");
  const [issue, setIssue] = useState("");
  const [value, setValue] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  return (
    <Page title="Report incorrect information">
      <Card className="max-w-xl space-y-3">
        <Field label="What's wrong?">
          <select className={inputCls} value={field} onChange={(e) => setField(e.target.value)}>
            {["ingredients", "nutrition", "allergens", "name", "brand", "image", "other"].map((x) => <option key={x}>{x}</option>)}
          </select>
        </Field>
        <Field label="Describe the problem"><textarea className={`${inputCls} min-h-24 py-2`} value={issue} onChange={(e) => setIssue(e.target.value)} /></Field>
        <Field label="Correct value from the package (optional)"><textarea className={`${inputCls} min-h-20 py-2`} value={value} onChange={(e) => setValue(e.target.value)} /></Field>
        {error ? <ErrorBox error={error} /> : null}
        <Button loading={busy} disabled={issue.trim().length < 5} onClick={async () => {
          setBusy(true);
          try {
            await api(`/products/${id}/report`, { body: { field, issue, suggested_value: value || null } });
            router.push(`/product/${id}`);
          } catch (e) { setError(e); } finally { setBusy(false); }
        }}>Send report</Button>
      </Card>
    </Page>
  );
}
