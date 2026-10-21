"use client";

/**
 * The language toggle for the AI features.
 *
 * The application itself is English-only; this chooses the language of the
 * *generated* explanations. It never changes a skill name, a role title or a
 * calculated score, and the panel that explains this says so.
 *
 * The choice is stored on the profile, so it follows the learner to another
 * device, and it can be overridden per request.
 */
import { Languages } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useProfile, useUpdateProfile } from "@/lib/hooks/use-profile";
import type { AiLanguage } from "@/lib/api/types";

const options: { value: AiLanguage; label: string }[] = [
  { value: "en", label: "English" },
  { value: "bn", label: "বাংলা" },
];

interface LanguageToggleProps {
  value: AiLanguage;
  onChange: (language: AiLanguage) => void;
  className?: string;
}

export function LanguageToggle({ value, onChange, className }: LanguageToggleProps) {
  return (
    <div
      className={className}
      role="group"
      aria-label="Language of the generated guidance"
    >
      <span className="mr-2 inline-flex items-center gap-1 text-sm text-muted-foreground">
        <Languages className="h-4 w-4" aria-hidden="true" />
        <span className="hidden sm:inline">Guidance language</span>
      </span>
      <span className="inline-flex rounded-md border p-0.5">
        {options.map((option) => (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={value === option.value ? "default" : "ghost"}
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
            className="h-7 px-2 text-xs"
          >
            {option.label}
          </Button>
        ))}
      </span>
    </div>
  );
}

/**
 * A toggle that also stores the choice on the profile.
 *
 * The stored preference is the default for every AI request; the per-page
 * state is what the page actually sends, so a user can answer one question in
 * Bangla and the next in English without changing their profile.
 */
export function StoredLanguageToggle({ value, onChange, className }: LanguageToggleProps) {
  const updateProfile = useUpdateProfile();

  function handleChange(language: AiLanguage) {
    onChange(language);
    void updateProfile
      .mutateAsync({ preferred_language: language })
      .catch(() => {
        /* The page keeps the choice; the profile update is a convenience. */
      });
  }

  return <LanguageToggle value={value} onChange={handleChange} className={className} />;
}

/** The language the profile says to use, defaulting to English. */
export function usePreferredLanguage(): AiLanguage {
  const { data: profile } = useProfile();
  return profile?.preferred_language === "bn" ? "bn" : "en";
}
