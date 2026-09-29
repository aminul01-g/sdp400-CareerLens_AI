"use client";

/**
 * Registration.
 *
 * Ported from the predecessor's `Register.tsx`, with the field it silently dropped
 * now actually sent: `Register.tsx:21,71-73` collected `educationLevel`, required
 * it, and then `Register.tsx:92` called `api.register(name, email, password)`
 * without it. The value was collected, validated, and thrown away. It is now
 * persisted on `Profile.education_level`.
 *
 * The client-side policy is identical to the server's (`lib/schemas.ts`), and the
 * server's own 422 field errors are merged in either way, so the server stays the
 * authority.
 */
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, Eye, EyeOff, Loader2, UserPlus } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/components/providers/AuthProvider";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import { registerSchema, type RegisterInput } from "@/lib/schemas";

const EDUCATION_LEVELS = [
  "High school",
  "Undergraduate",
  "Postgraduate",
  "PhD",
  "Self-taught",
  "Other",
] as const;

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [values, setValues] = React.useState<Omit<RegisterInput, "acceptTerms">>({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    educationLevel: "",
  });
  const [accepted, setAccepted] = React.useState(false);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [formError, setFormError] = React.useState<string | null>(null);
  const [showPassword, setShowPassword] = React.useState(false);
  const [isPending, setIsPending] = React.useState(false);

  function update<K extends keyof typeof values>(key: K, value: (typeof values)[K]) {
    setValues((previous) => ({ ...previous, [key]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const parsed = registerSchema.safeParse({ ...values, acceptTerms: accepted });
    if (!parsed.success) {
      setFieldErrors(
        Object.fromEntries(parsed.error.issues.map((issue) => [String(issue.path[0]), issue.message])),
      );
      return;
    }

    setIsPending(true);
    try {
      await register({
        name: parsed.data.name,
        email: parsed.data.email,
        password: parsed.data.password,
        // The field the predecessor form collected and then discarded.
        education_level: parsed.data.educationLevel || null,
      });
      router.replace("/dashboard");
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) {
        // Prefer the server's own field errors: it is the authority on validation.
        setFieldErrors((previous) => ({ ...previous, ...error.fieldErrors }));
      }
      setFormError(errorMessage(error, "We could not create your account."));
    } finally {
      setIsPending(false);
    }
  }

  const passwordChecks = [
    { label: "At least 8 characters", ok: values.password.length >= 8 },
    { label: "An uppercase letter", ok: /[A-Z]/.test(values.password) },
    { label: "A lowercase letter", ok: /[a-z]/.test(values.password) },
    { label: "A digit", ok: /\d/.test(values.password) },
  ];

  return (
    <div className="container mx-auto flex min-h-[70vh] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-2xl">
            <UserPlus className="h-5 w-5" aria-hidden="true" />
            Create your account
          </CardTitle>
          <CardDescription>
            Build a profile, add your skills, and get a ranked list of AI/ML roles.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            {formError ? (
              <Alert variant="destructive" role="alert">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="name">Full name</Label>
              <Input
                id="name"
                autoComplete="name"
                required
                value={values.name}
                onChange={(event) => update("name", event.target.value)}
                aria-invalid={Boolean(fieldErrors.name)}
                aria-describedby={fieldErrors.name ? "name-error" : undefined}
              />
              {fieldErrors.name ? (
                <p id="name-error" className="text-sm text-destructive">{fieldErrors.name}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={values.email}
                onChange={(event) => update("email", event.target.value)}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? "email-error" : undefined}
              />
              {fieldErrors.email ? (
                <p id="email-error" className="text-sm text-destructive">{fieldErrors.email}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="education">Highest level of education</Label>
              <Select
                value={values.educationLevel || undefined}
                onValueChange={(value) => update("educationLevel", value)}
              >
                <SelectTrigger id="education">
                  <SelectValue placeholder="Select your level" />
                </SelectTrigger>
                <SelectContent>
                  {EDUCATION_LEVELS.map((level) => (
                    <SelectItem key={level} value={level}>
                      {level}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                This helps us judge how far along your profile is. It is optional.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  value={values.password}
                  onChange={(event) => update("password", event.target.value)}
                  className="pr-10"
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby="password-requirements"
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
              <ul id="password-requirements" className="grid grid-cols-2 gap-1 text-xs">
                {passwordChecks.map((check) => (
                  <li
                    key={check.label}
                    className={check.ok ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"}
                  >
                    <CheckCircle2 className="mr-1 inline h-3 w-3" aria-hidden="true" />
                    {check.label}
                  </li>
                ))}
              </ul>
              {fieldErrors.password ? (
                <p className="text-sm text-destructive">{fieldErrors.password}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input
                id="confirmPassword"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={values.confirmPassword}
                onChange={(event) => update("confirmPassword", event.target.value)}
                aria-invalid={Boolean(fieldErrors.confirmPassword)}
                aria-describedby={fieldErrors.confirmPassword ? "confirm-error" : undefined}
              />
              {fieldErrors.confirmPassword ? (
                <p id="confirm-error" className="text-sm text-destructive">{fieldErrors.confirmPassword}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <Checkbox
                  id="terms"
                  checked={accepted}
                  onCheckedChange={(checked) => setAccepted(checked === true)}
                  aria-invalid={Boolean(fieldErrors.acceptTerms)}
                />
                <Label htmlFor="terms" className="text-sm font-normal leading-snug">
                  I understand that CareerLens AI produces suggestions, not job offers, and
                  that its matching engine uses unsupervised similarity and rule-based
                  weighting rather than a trained classifier.
                </Label>
              </div>
              {fieldErrors.acceptTerms ? (
                <p className="text-sm text-destructive">{fieldErrors.acceptTerms}</p>
              ) : null}
            </div>

            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isPending ? "Creating your account…" : "Create account"}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link href="/login" className="font-medium text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
