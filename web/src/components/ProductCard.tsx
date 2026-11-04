import Link from "next/link";
import { Package } from "lucide-react";
import { assetUrl } from "@/lib/api";
import type { ProductSummary } from "@/lib/types";
import { MiniScore } from "./score";

export function ProductThumb({ src, alt }: { src?: string | null; alt: string }) {
  const url = assetUrl(src);
  return url ? (
    // eslint-disable-next-line @next/next/no-img-element -- third-party OFF image hosts; no Next image optimisation
    <img src={url} alt={alt} className="size-14 shrink-0 rounded-xl border border-line bg-white object-contain" loading="lazy" />
  ) : (
    <span className="grid size-14 shrink-0 place-items-center rounded-xl bg-surface-2 text-muted">
      <Package className="size-6" aria-hidden />
    </span>
  );
}

export function ProductCard({ p, sub, right }: { p: ProductSummary; sub?: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-3 transition hover:border-brand/50">
      <Link href={`/product/${p.id}`} className="flex min-w-0 flex-1 items-center gap-3">
        <ProductThumb src={p.image_url} alt={p.name || "Product"} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{p.name || "Unnamed product"}</p>
          <p className="truncate text-sm text-muted">{[p.brand, sub].filter(Boolean).join(" · ") || p.barcode}</p>
        </div>
        <MiniScore score={p.score} color={p.color} />
      </Link>
      {right}
    </div>
  );
}
