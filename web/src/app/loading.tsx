import { Page, Skeleton } from "@/components/ui";

export default function Loading() {
  return (
    <Page>
      <Skeleton className="h-28" />
      <Skeleton className="mt-4 h-64" />
    </Page>
  );
}
