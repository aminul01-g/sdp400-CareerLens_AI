import Link from "next/link";
import { ArrowRight, Brain, FileSearch, ListChecks, Sparkles, Target, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Landing page. Ported from the predecessor's `Landing.tsx`, copy corrected to CareerLens AI. */
const features = [
  {
    icon: ListChecks,
    title: "A real profile, not a quiz",
    body: "Skills with a proficiency from 1 to 5, projects with a tech stack, education, and certifications — all stored in normalised tables, not a comma-separated text field.",
  },
  {
    icon: FileSearch,
    title: "CV analysis that shows its work",
    body: "Upload a PDF or DOCX. We extract the text, match it against a curated taxonomy of 150+ AI/ML skills and their aliases, and show you every match before anything is saved.",
  },
  {
    icon: TrendingUp,
    title: "A score you can check",
    body: "Compatibility combines weighted skill coverage with TF-IDF text similarity. You see both components, both weights, and the formula — not one opaque number.",
  },
  {
    icon: Target,
    title: "A gap report, in priority order",
    body: "Pick a target role and see exactly which skills you are missing, ranked by that role's importance weight, with critical and desirable items separated.",
  },
];

const steps = [
  { title: "Create your profile", body: "Add your headline, career goal, and the skills you actually have." },
  { title: "Upload your CV", body: "Let the extractor suggest skills, then confirm or reject each one." },
  { title: "Get ranked roles", body: "See which AI/ML roles fit, and exactly why each score came out where it did." },
  { title: "Close the gap", body: "Work down the missing skills in importance order, then generate again." },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col">
      <section className="border-b bg-gradient-to-b from-primary/5 to-background">
        <div className="container mx-auto grid gap-10 px-4 py-16 md:grid-cols-2 md:items-center md:py-24">
          <div className="space-y-6">
            <Badge variant="secondary" className="gap-1.5">
              <Sparkles className="h-3 w-3" aria-hidden="true" />
              For AI/ML careers specifically
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Know which AI/ML role fits you —{" "}
              <span className="text-primary">and why</span>
            </h1>
            <p className="max-w-xl text-lg text-muted-foreground">
              CareerLens AI builds a profile from your skills, projects, and CV, then ranks
              AI/ML job roles with a compatibility score it will show you the working for.
              Every match comes with the matched and missing skills behind it.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/register">
                  Get started
                  <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/features">See how it works</Link>
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Free and open source. No trained classifier — the engine is deterministic,
              CPU-only, and runs entirely on your own data.
            </p>
          </div>

          <Card className="border-primary/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" aria-hidden="true" />
                Machine Learning Engineer
              </CardTitle>
              <CardDescription>An example of how a score is produced</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Compatibility</span>
                  <span className="font-semibold">shown as a percentage</span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted">
                  <div className="h-2 rounded-full bg-primary" style={{ width: "62%" }} />
                </div>
              </div>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-md border p-3">
                  <dt className="text-muted-foreground">Weighted skill coverage</dt>
                  <dd className="text-lg font-semibold">0.51</dd>
                </div>
                <div className="rounded-md border p-3">
                  <dt className="text-muted-foreground">TF-IDF similarity</dt>
                  <dd className="text-lg font-semibold">0.26</dd>
                </div>
              </dl>
              <p className="text-xs text-muted-foreground">
                compatibility = 0.6 × coverage + 0.4 × cosine. Both components and both
                weights are shown on every result, because a score you cannot check is not
                an explanation.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="container mx-auto px-4 py-16">
        <div className="mx-auto max-w-2xl space-y-3 text-center">
          <h2 className="text-3xl font-bold tracking-tight">What it actually does</h2>
          <p className="text-muted-foreground">
            Four things, each of which is a real feature rather than a promise.
          </p>
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {features.map((feature) => (
            <Card key={feature.title}>
              <CardHeader>
                <feature.icon className="h-6 w-6 text-primary" aria-hidden="true" />
                <CardTitle className="text-lg">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{feature.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y bg-muted/30">
        <div className="container mx-auto px-4 py-16">
          <h2 className="text-center text-3xl font-bold tracking-tight">How it works</h2>
          <ol className="mx-auto mt-10 grid max-w-4xl gap-6 md:grid-cols-4">
            {steps.map((step, index) => (
              <li key={step.title} className="space-y-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {index + 1}
                </span>
                <h3 className="font-semibold">{step.title}</h3>
                <p className="text-sm text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="container mx-auto px-4 py-16">
        <div className="rounded-lg border bg-card p-8 text-center">
          <h2 className="text-2xl font-bold tracking-tight">Start with what you already know</h2>
          <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
            Add five skills and you will get a ranked list. That is enough to be useful.
          </p>
          <Button asChild size="lg" className="mt-6">
            <Link href="/register">Create your free account</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
