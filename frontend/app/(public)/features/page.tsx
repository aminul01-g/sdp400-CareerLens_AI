import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";

export const metadata: Metadata = { title: "Features" };

/**
 * Features.
 *
 * Ported from the predecessor's `Features.tsx`, and rewritten to describe what the
 * shipped system actually does. The old page described a career quiz and a chatbot;
 * neither exists in CareerLens AI, and a features page that lists features the
 * product does not have is worse than no page.
 */
const modules = [
  {
    title: "Authentication",
    description: "Register, log in, log out, and refresh, with JWT bearer tokens and enforced user/admin roles. Every write requires a valid token, and every user-owned read is scoped by user id in the query itself.",
    points: ["bcrypt password hashing", "Case-insensitive unique email", "Explicit token expiry", "Admin role gate on every admin route"],
  },
  {
    title: "Profile",
    description: "Headline, career goal, bio, location, years of experience, preferred role family, and links. Create, read, edit, and delete — with the delete scoped to the profile row so the account and its other modules survive.",
    points: ["Full C/R/U/D", "Partial updates that distinguish absent from null", "URL validation on every link", "Live child counts in one request"],
  },
  {
    title: "Skills",
    description: "Add skills from a curated taxonomy of 150+ AI/ML technologies, each with proficiency from 1 to 5. Search matches aliases, so typing 'sklearn' finds Scikit-learn.",
    points: ["151 skills, 555 aliases, 8 categories", "Proficiency 1–5", "Provenance: manual or CV-extracted", "Bulk confirmation of detected skills"],
  },
  {
    title: "Projects, education, certifications",
    description: "Record what you have built and what you have studied. Project tech stacks are canonicalised through the taxonomy, so 'sklearn' and 'Scikit-learn' cannot become two different facts.",
    points: ["Full C/R/U/D on all three", "Ownership enforced in the query", "Date and year-range validation", "Unrecognised technologies flagged, not discarded"],
  },
  {
    title: "AI resume analysis",
    description: "Upload a PDF or DOCX. Text is extracted, matched against the taxonomy with spaCy phrase matching, and shown to you for confirmation before anything is saved. A scanned PDF says so clearly instead of reporting zero skills.",
    points: ["PDF and DOCX, 5 MB limit", "Extension and content type both validated", "Detected skills staged, never auto-saved", "Idempotent confirmation"],
  },
  {
    title: "AI job matching",
    description: "A ranked list of AI/ML roles with a compatibility percentage that decomposes into its two components, plus the matched and missing skills with their weights.",
    points: ["0.6 × coverage + 0.4 × cosine", "Every role explained", "Zero-match roles kept, not hidden", "Stored runs, immutable and re-readable"],
  },
  {
    title: "Skill-gap analysis",
    description: "Pick any target role and see the required skills minus yours, ordered strictly by that role's importance weight, banded into critical, important, and desirable.",
    points: ["Descending weight order", "Tier badges at 0.8 and 0.5", "Matched skills with your proficiency", "Reads confirmed skills only"],
  },
  {
    title: "Admin knowledge base",
    description: "An in-app panel for maintaining job roles, their required skills, and each skill's importance weight — with validation, conflict handling, and a live tier badge as the weight moves.",
    points: ["Role CRUD", "Atomic skill-set replacement", "Taxonomy maintenance with alias-collision checks", "Real aggregates, never invented numbers"],
  },
];

export default function FeaturesPage() {
  return (
    <div className="container mx-auto space-y-8 px-4 py-12">
      <PageHeader
        title="Features"
        description="Everything described here is implemented, tested, and reachable from this application."
      />

      <div className="grid gap-6 md:grid-cols-2">
        {modules.map((module) => (
          <Card key={module.title}>
            <CardHeader>
              <CardTitle>{module.title}</CardTitle>
              <CardDescription>{module.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {module.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Optional: the LLM learning path</CardTitle>
          <CardDescription>Off by default, and nothing depends on it</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            If an LLM API key is configured, the skill-gap page can ask a model to turn the
            missing-skill list into a short learning path. It is flagged off by default, it
            is reachable only through its own endpoint, and with the flag off that endpoint
            returns <code className="rounded bg-muted px-1 py-0.5 text-xs">503</code> and
            nothing else changes.
          </p>
          <p>
            The core recommendation and gap features work identically either way — which is
            the point of building it this way.
          </p>
        </CardContent>
      </Card>

      <div className="flex justify-center pt-4">
        <Button asChild size="lg">
          <Link href="/register">Try it with your own CV</Link>
        </Button>
      </div>
    </div>
  );
}
