import Link from "next/link";
import { Button } from "@/components/ui/button";
import { SearchX } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <SearchX className="h-12 w-12 text-muted-foreground" aria-hidden="true" />
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Page not found</h1>
        <p className="text-muted-foreground">
          That page does not exist. It may have been moved, or the link may be wrong.
        </p>
      </div>
      <div className="flex gap-2">
        <Button asChild>
          <Link href="/dashboard">Go to dashboard</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/">Back to home</Link>
        </Button>
      </div>
    </div>
  );
}
