"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PackageSearch, ScanLine, WifiOff } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { cacheProduct } from "@/lib/offline";
import { Button, Card, EmptyState, ErrorBox, LinkButton, Page } from "@/components/ui";
import type { Analysis, Product } from "@/lib/types";

type Resp = { product: Product; analysis: Analysis };
const STEPS = ["Validating barcode", "Checking Open Food Facts and USDA", "Reading ingredients", "Scoring with FDA Daily Values", "Checking your profiles"];

export default function ScanProcessing() {
  const { code } = useParams<{ code: string }>();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [err, setErr] = useState<ApiError | null>(null);

  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 650);
    api<Resp>(`/products/barcode/${code}`)
      .then((r) => {
        cacheProduct(r.product.id, r);
        sessionStorage.setItem(`omniscan.p.${r.product.id}`, JSON.stringify(r));
        router.replace(`/product/${r.product.id}`);
      })
      .catch((e) => setErr(e as ApiError))
      .finally(() => clearInterval(t));
    return () => clearInterval(t);
  }, [code, router]);

  if (err?.code === "product_not_found") {
    return (
      <Page>
        <EmptyState
          icon={<PackageSearch className="size-6" />}
          title="We couldn't find this product"
          body={`Barcode ${code} isn't in Open Food Facts or our database yet. Add it in about a minute by photographing the label. A moderator will verify it, and it'll help everyone after you.`}
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <LinkButton href={`/submit?barcode=${code}`}>Add this product</LinkButton>
              <LinkButton href="/analyze" variant="secondary">Just analyze the label</LinkButton>
            </div>
          }
        />
      </Page>
    );
  }
  if (err) {
    return (
      <Page>
        {err.code === "provider_unavailable" || err.code === "network_error" ? (
          <EmptyState icon={<WifiOff className="size-6" />} title="Product databases are unreachable" body="This is usually temporary. Your scan wasn't lost. Try again in a moment." action={<Button onClick={() => location.reload()}>Try again</Button>} />
        ) : (
          <div className="space-y-3">
            <ErrorBox error={err} />
            <LinkButton href="/scan" variant="secondary">Scan another barcode</LinkButton>
          </div>
        )}
      </Page>
    );
  }
  return (
    <Page>
      <Card className="mx-auto mt-6 max-w-sm text-center" aria-live="polite">
        <div className="mx-auto grid size-20 place-items-center rounded-3xl bg-brand-soft text-brand">
          <ScanLine className="size-10 animate-pulse" aria-hidden />
        </div>
        <p className="mt-4 font-display text-xl font-extrabold">Analyzing {code}</p>
        <ol className="mt-4 space-y-2 text-left text-sm">
          {STEPS.map((s, i) => (
            <li key={s} className={`flex items-center gap-2 ${i <= step ? "text-ink" : "text-muted"}`}>
              <span className={`size-2 rounded-full ${i < step ? "bg-good" : i === step ? "animate-pulse bg-brand" : "bg-line"}`} /> {s}
            </li>
          ))}
        </ol>
      </Card>
    </Page>
  );
}
