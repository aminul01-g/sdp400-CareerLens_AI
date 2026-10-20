"use client";

/**
 * Confirm an email address.
 *
 * Reached from the link in the verification email, so the token arrives in the
 * query string. It is used once and then taken out of the address bar.
 */
import * as React from "react";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, MailWarning } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { errorMessage } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [state, setState] = React.useState<"idle" | "working" | "done" | "failed">("idle");
  const [message, setMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!token) {
      setState("failed");
      setMessage("The link is missing its token. Please request a new one.");
      return;
    }
    let cancelled = false;
    setState("working");
    authApi
      .verifyEmail(token)
      .then(() => {
        if (cancelled) return;
        setState("done");
        router.replace("/verify-email");
      })
      .catch((error) => {
        if (cancelled) return;
        setState("failed");
        setMessage(errorMessage(error, "That link is not valid, or has expired."));
      });
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  return (
    <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl">
            {state === "done" ? (
              <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
            ) : (
              <MailWarning className="h-5 w-5" aria-hidden="true" />
            )}
            Email confirmation
          </CardTitle>
          <CardDescription>
            Confirming your address is optional, but it lets us show unverified
            accounts to administrators.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {state === "working" ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Confirming your address…
            </p>
          ) : state === "done" ? (
            <div className="space-y-4">
              <Alert role="status">
                <AlertDescription>Your email address is confirmed.</AlertDescription>
              </Alert>
              <Button asChild className="w-full">
                <Link href="/dashboard">Go to your dashboard</Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Alert variant="destructive" role="alert">
                <AlertDescription>
                  {message ?? "That link is not valid, or has expired."}
                </AlertDescription>
              </Alert>
              <Button asChild variant="outline" className="w-full">
                <Link href="/login">Back to sign in</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
          <div className="h-8 w-48 animate-pulse rounded-md bg-muted" aria-hidden="true" />
        </div>
      }
    >
      <VerifyEmailForm />
    </Suspense>
  );
}
