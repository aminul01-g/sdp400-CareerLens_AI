"use client";

/**
 * Profile.
 *
 * Create, read, edit, and delete — the proposal's first CRUD entity. The delete
 * dialog states exactly what is removed *and what is kept*, because that
 * distinction is real in the schema: `DELETE /api/profile` removes the profile row
 * only, so the account, the login, and the user's skills, projects, education, and
 * certifications all survive.
 */
import * as React from "react";
import Link from "next/link";
import { Loader2, Save, Trash2, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { ApiError } from "@/lib/api/config";
import { errorMessage } from "@/lib/api/client";
import {
  useCreateProfile,
  useDeleteProfile,
  useProfile,
  useUpdateProfile,
} from "@/lib/hooks/use-profile";

const EDUCATION_LEVELS = [
  "", "High school", "Undergraduate", "Postgraduate", "PhD", "Self-taught", "Other",
];

interface FormState {
  headline: string;
  career_goal: string;
  bio: string;
  location: string;
  education_level: string;
  years_experience: string;
  preferred_role_family: string;
  github: string;
  linkedin: string;
  portfolio: string;
}

const EMPTY: FormState = {
  headline: "", career_goal: "", bio: "", location: "",
  education_level: "", years_experience: "", preferred_role_family: "",
  github: "", linkedin: "", portfolio: "",
};

export default function ProfilePage() {
  const profile = useProfile();
  const updateProfile = useUpdateProfile();
  const createProfile = useCreateProfile();
  const deleteProfile = useDeleteProfile();

  const [form, setForm] = React.useState<FormState>(EMPTY);
  const [fieldErrors, setFieldErrors] = React.useState<Record<string, string>>({});
  const [saved, setSaved] = React.useState(false);
  const [confirmOpen, setConfirmOpen] = React.useState(false);

  // Seed the form once the profile arrives. Guarded on data identity so a
  // background refetch cannot clobber unsaved edits.
  React.useEffect(() => {
    if (!profile.data) return;
    setForm({
      headline: profile.data.headline ?? "",
      career_goal: profile.data.career_goal ?? "",
      bio: profile.data.bio ?? "",
      location: profile.data.location ?? "",
      education_level: profile.data.education_level ?? "",
      years_experience:
        profile.data.years_experience != null ? String(profile.data.years_experience) : "",
      preferred_role_family: profile.data.preferred_role_family ?? "",
      github: profile.data.links?.github ?? "",
      linkedin: profile.data.links?.linkedin ?? "",
      portfolio: profile.data.links?.portfolio ?? "",
    });
  }, [profile.data]);

  if (profile.isPending) return <LoadingPage label="Loading your profile" />;
  if (profile.isError) {
    return (
      <div className="space-y-4">
        <PageHeader title="Profile" />
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </div>
    );
  }

  const data = profile.data;
  const isEmpty = !data.headline && !data.bio && !data.career_goal;
  const isMutating = updateProfile.isPending || createProfile.isPending;

  function update<K extends keyof FormState>(key: K, value: string) {
    setForm((previous) => ({ ...previous, [key]: value }));
    setSaved(false);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});

    const years = form.years_experience.trim();
    if (years && (Number.isNaN(Number(years)) || Number(years) < 0 || Number(years) > 60)) {
      setFieldErrors({ years_experience: "Enter a number between 0 and 60." });
      return;
    }
    for (const [key, value] of Object.entries({ github: form.github, linkedin: form.linkedin, portfolio: form.portfolio })) {
      if (value && !/^https?:\/\/.+/i.test(value)) {
        setFieldErrors({ [key]: "Enter a full URL starting with http:// or https://" });
        return;
      }
    }

    const payload = {
      headline: form.headline || null,
      career_goal: form.career_goal || null,
      bio: form.bio || null,
      location: form.location || null,
      education_level: form.education_level || null,
      years_experience: years ? Number(years) : null,
      preferred_role_family: form.preferred_role_family || null,
      links: Object.fromEntries(
        Object.entries({ github: form.github, linkedin: form.linkedin, portfolio: form.portfolio }).filter(
          ([, v]) => v,
        ),
      ),
    };

    try {
      // The endpoint is get-or-create, so the same call serves first save and edit.
      await updateProfile.mutateAsync(payload);
      setSaved(true);
    } catch (error) {
      if (error instanceof ApiError && error.isValidation) {
        setFieldErrors(error.fieldErrors);
      }
      alert(errorMessage(error, "We could not save your profile."));
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Profile"
        description={
          isEmpty
            ? "Complete your profile — the headline and career goal feed your profile text, which the engine matches against."
            : "This information contributes to the text the matching engine reads."
        }
        actions={
          <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
            <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
            Delete profile
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-4">
        {[
          { label: "Skills", value: data.skills_count, href: "/skills" },
          { label: "Projects", value: data.projects_count, href: "/projects" },
          { label: "Education", value: data.education_count, href: "/education" },
          { label: "Certifications", value: data.certifications_count, href: "/certifications" },
        ].map((item) => (
          <Link key={item.label} href={item.href}>
            <Card className="h-full transition-colors hover:border-primary/50">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">{item.label}</p>
                <p className="text-2xl font-bold">{item.value}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" aria-hidden="true" />
            {isEmpty ? "Complete your profile" : "Edit your profile"}
          </CardTitle>
          <CardDescription>Everything here is optional except the email on your account.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="headline">Headline</Label>
                <Input
                  id="headline" maxLength={200} value={form.headline}
                  onChange={(e) => update("headline", e.target.value)}
                  placeholder="Machine Learning Engineer"
                  aria-invalid={Boolean(fieldErrors.headline)}
                />
                {fieldErrors.headline ? <p className="text-sm text-destructive">{fieldErrors.headline}</p> : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location" maxLength={120} value={form.location}
                  onChange={(e) => update("location", e.target.value)}
                  placeholder="Dhaka, Bangladesh"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="career_goal">Career goal</Label>
              <Textarea
                id="career_goal" rows={3} maxLength={2000} value={form.career_goal}
                onChange={(e) => update("career_goal", e.target.value)}
                placeholder="Where do you want to be in one to two years?"
                aria-describedby="career-goal-hint"
              />
              <p id="career-goal-hint" className="text-xs text-muted-foreground">
                This is concatenated into your profile text, so it genuinely affects your match scores.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="bio">Bio</Label>
              <Textarea id="bio" rows={4} maxLength={4000} value={form.bio} onChange={(e) => update("bio", e.target.value)} />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="education_level">Education level</Label>
                <select
                  id="education_level" value={form.education_level}
                  onChange={(e) => update("education_level", e.target.value)}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {EDUCATION_LEVELS.map((level) => (
                    <option key={level || "none"} value={level}>{level || "Not specified"}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="years_experience">Years of experience</Label>
                <Input
                  id="years_experience" type="number" min={0} max={60} value={form.years_experience}
                  onChange={(e) => update("years_experience", e.target.value)}
                  aria-invalid={Boolean(fieldErrors.years_experience)}
                />
                {fieldErrors.years_experience ? (
                  <p className="text-sm text-destructive">{fieldErrors.years_experience}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="preferred_role_family">Preferred role family</Label>
                <Input
                  id="preferred_role_family" maxLength={80} value={form.preferred_role_family}
                  onChange={(e) => update("preferred_role_family", e.target.value)}
                  placeholder="ML Engineer"
                />
              </div>
            </div>

            <fieldset className="space-y-3 rounded-md border p-4">
              <legend className="px-1 text-sm font-medium">Links</legend>
              {(
                [
                  { id: "github", label: "GitHub", value: form.github, set: (v: string) => update("github", v) },
                  { id: "linkedin", label: "LinkedIn", value: form.linkedin, set: (v: string) => update("linkedin", v) },
                  { id: "portfolio", label: "Portfolio", value: form.portfolio, set: (v: string) => update("portfolio", v) },
                ] as const
              ).map((field) => (
                <div key={field.id} className="space-y-2">
                  <Label htmlFor={field.id}>{field.label}</Label>
                  <Input
                    id={field.id} value={field.value} onChange={(e) => field.set(e.target.value)}
                    placeholder={`https://${field.id}.com/your-handle`}
                    aria-invalid={Boolean(fieldErrors[field.id])}
                  />
                  {fieldErrors[field.id] ? (
                    <p className="text-sm text-destructive">{fieldErrors[field.id]}</p>
                  ) : null}
                </div>
              ))}
            </fieldset>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={isMutating}>
                {isMutating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" /> : <Save className="mr-2 h-4 w-4" aria-hidden="true" />}
                {isMutating ? "Saving…" : "Save profile"}
              </Button>
              {saved ? <p className="text-sm text-emerald-600 dark:text-emerald-400" role="status">Saved.</p> : null}
            </div>
          </form>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Delete your profile?"
        isPending={deleteProfile.isPending}
        description={
          <>
            <p>This will remove your headline, career goal, bio, location, and links.</p>
            <p className="font-medium text-foreground">
              Kept: your account and login, your {data.skills_count} skill(s), your{" "}
              {data.projects_count} project(s), your education records, and your certifications.
              Those are separate modules with their own delete operations.
            </p>
            <p>You can rebuild your profile afterwards without re-registering.</p>
          </>
        }
        onConfirm={async () => {
          try {
            await deleteProfile.mutateAsync();
            setConfirmOpen(false);
          } catch (error) {
            setConfirmOpen(false);
            alert(errorMessage(error, "We could not delete your profile."));
          }
        }}
      />
    </div>
  );
}
