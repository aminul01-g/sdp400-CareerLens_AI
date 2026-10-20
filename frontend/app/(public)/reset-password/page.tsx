"use client";

/**
 * Choose a new password.
 *
 * The token arrives in the query string, because that is what an email link
 * has to be. It is read once, used once, and then the URL is replaced with a
 * clean one so the token does not linger in the address bar, in the browser
 * history, or in a referrer header.
 */
import * as React from "react";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, KeyRound, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api/client";
import { authApi } from "@/lib/api/auth";
import { passwordSchema } from "@/lib/schemas";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [done, setDone] = React.useState(false);
  const [isPending, setIsPending] = React.useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const parsed = passwordSchema.safeParse(password);
    if (!parsed.success) {
      setFieldErrors({ password: parsed.error.issues[0]?.message ?? "Enter a valid password." });
      return;
    }
    if (password !== confirm) {
      setFieldErrors({ confirm: "The two passwords do not match." });
      return;
    }

    setIsPending(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
      // Take the token out of the address bar. It has been used, but there is
      // no reason to leave it in the history.
      router.replace("/reset-password");
    } catch (error) {
      setFormError(errorMessage(error, "That link is not valid, or has expired."));
    } finally {
      setIsPending(false);
    }
  }

  if (!token) {
    return (
      <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-2xl">This link is incomplete</CardTitle>
            <CardDescription>
              The reset link is missing its token. Ask for a new one and open the link
              from the email straight away.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/forgot-password">Request a new link</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl">
            <KeyRound className="h-5 w-5" aria-hidden="true" />
            Choose a new password
          </CardTitle>
          <CardDescription>
            Your new password takes effect immediately, and any other session you have
            open will be signed out.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {done ? (
            <div className="space-y-4">
              <Alert role="status">
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                <AlertDescription>
                  Your password has been changed. Sign in with the new one.
                </AlertDescription>
              </Alert>
              <Button asChild className="w-full">
                <Link href="/login">Sign in</Link>
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {formError ? (
                <Alert variant="destructive" role="alert">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="password">New password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby="password-hint"
                />
                <p id="password-hint" className="text-xs text-muted-foreground">
                  At least 8 characters, with an uppercase letter, a lowercase letter and
                  a digit.
                </p>
                {fieldErrors.password ? (
                  <p className="text-sm text-destructive">{fieldErrors.password}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm">Confirm the new password</Label>
                <Input
                  id="confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirm}
                  onChange={(event) => setConfirm(event.target.value)}
                  aria-invalid={Boolean(fieldErrors.confirm)}
                />
                {fieldErrors.confirm ? (
                  <p className="text-sm text-destructive">{fieldErrors.confirm}</p>
                ) : null}
              </div>

              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                {isPending ? "Saving…" : "Set the new password"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
          <div className="h-8 w-48 animate-pulse rounded-md bg-muted" aria-hidden="true" />
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
