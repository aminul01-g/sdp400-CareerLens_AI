"use client";

/**
 * Login.
 *
 * Ported from the predecessor's `Login.tsx`, with two changes: the password
 * minimum is raised from 6 to 8 to match the server and the register form, and the
 * `?from=` path recorded by the route guard is honoured after a successful login.
 *
 * A failed login shows one message for both "no such account" and "wrong
 * password", because distinguishing them turns the form into an account
 * enumeration oracle.
 */
import * as React from "react";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, LogIn, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/components/providers/AuthProvider";
import { errorMessage } from "@/lib/api/client";
import { loginSchema, type LoginInput } from "@/lib/schemas";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const from = searchParams.get("from");

  const [values, setValues] = React.useState<LoginInput>({ email: "", password: "" });
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [showPassword, setShowPassword] = React.useState(false);
  const [isPending, setIsPending] = React.useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const parsed = loginSchema.safeParse(values);
    if (!parsed.success) {
      setFieldErrors(
        Object.fromEntries(parsed.error.issues.map((issue) => [String(issue.path[0]), issue.message])),
      );
      return;
    }

    setIsPending(true);
    try {
      await login(parsed.data.email, parsed.data.password);
      // Send the user back to where the guard intercepted them, but only to a
      // same-origin path — an attacker-supplied absolute URL must not be honoured.
      router.replace(from && from.startsWith("/") && !from.startsWith("//") ? from : "/dashboard");
    } catch (error) {
      setFormError(errorMessage(error, "Email or password is incorrect."));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl">
            <LogIn className="h-5 w-5" aria-hidden="true" />
            Welcome back
          </CardTitle>
          <CardDescription>Sign in to see your AI/ML role recommendations.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {formError ? (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={values.email}
                onChange={(event) => setValues((v) => ({ ...v, email: event.target.value }))}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
              />
              {fieldErrors.email ? (
                <p id="email-error" className="text-sm text-destructive">
                  {fieldErrors.email}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={values.password}
                  onChange={(event) => setValues((v) => ({ ...v, password: event.target.value }))}
                  className="pr-10"
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={fieldErrors.password ? "password-error" : undefined}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowPassword((shown) => !shown)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                </Button>
              </div>
              {fieldErrors.password ? (
                <p id="password-error" className="text-sm text-destructive">
                  {fieldErrors.password}
                </p>
              ) : null}
            </div>

            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isPending ? "Signing in…" : "Sign in"}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              No account yet?{" "}
              <Link href="/register" className="font-medium text-primary hover:underline">
                Create one
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * `useSearchParams()` opts a route out of static prerendering, so the form is
 * wrapped in a Suspense boundary. Without it the build fails on the missing
 * boundary rather than degrading — which is the correct failure, because a login
 * page that cannot read `?from=` cannot honour the post-login redirect at all.
 */
export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
          <div className="h-8 w-48 animate-pulse rounded-md bg-muted" aria-hidden="true" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
