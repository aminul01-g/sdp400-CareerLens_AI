"use client";

/**
 * TanStack Query provider.
 *
 * Mounted once in the root layout. It was previously at `App.tsx:70`; the plan
 * keeps the dependency (already installed, already wrapped) and adds no new state
 * library.
 *
 * A single global `onError` turns any unhandled mutation failure into a toast, so
 * an individual screen only has to handle the errors it can explain better than
 * "something went wrong". `401` and `403` are excluded: the first is handled by
 * the route guard, the second by the page that states the role requirement, and a
 * toast on top of either is noise.
 */
import * as React from "react";
import {
  MutationCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { ApiError } from "@/lib/api/config";
import { useToast } from "@/hooks/use-toast";

function makeQueryClient(onError: (error: unknown) => void): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // One retry, not three: a 403 or a 422 will not become a 200 on the
        // second attempt, and silent retries make a broken screen look slow
        // rather than wrong.
        retry: 1,
      },
      mutations: { retry: 0 },
    },
    mutationCache: new MutationCache({ onError }),
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    return makeQueryClient(() => undefined);
  }
  // One client per browser session, created lazily so the first render does not
  // build a client that is then thrown away by a re-render.
  browserQueryClient ??= makeQueryClient((error) => {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return;
    }
    globalThis.dispatchEvent(
      new CustomEvent("careerlens:mutation-error", { detail: error }),
    );
  });
  return browserQueryClient;
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();
  const { toast } = useToast();

  React.useEffect(() => {
    const handler = (event: Event) => {
      const error = (event as CustomEvent<unknown>).detail;
      toast({
        title: "That did not work",
        description: error instanceof Error ? error.message : "Something went wrong.",
        variant: "destructive",
      });
    };
    globalThis.addEventListener("careerlens:mutation-error", handler);
    return () => globalThis.removeEventListener("careerlens:mutation-error", handler);
  }, [toast]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
