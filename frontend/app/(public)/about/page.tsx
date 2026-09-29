import type { Metadata } from "next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";

export const metadata: Metadata = { title: "About" };

/** Ported from the predecessor's `About.tsx`, with the branding corrected. */
export default function AboutPage() {
  return (
    <div className="container mx-auto space-y-8 px-4 py-12">
      <PageHeader
        title="About CareerLens AI"
        description="An AI-powered job and career recommendation system built for AI/ML roles."
      />

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>The problem</CardTitle>
            <CardDescription>What generic career tools do not do</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              General job boards list thousands of roles and treat a search box as their
              whole product. They have no controlled knowledge base, so they cannot tell
              you <em>why</em> a role matches or what specifically you are missing.
            </p>
            <p>
              Meanwhile, AI/ML is a market where the skill set is unusually well defined.
              There are roughly 150 technologies that matter, they have well-known aliases,
              and roles weight them differently. A system built around that structure can
              do something a generic one cannot: explain the answer precisely.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Our approach</CardTitle>
            <CardDescription>Deterministic, explainable, CPU-only</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              The compatibility score combines <strong>weighted skill coverage</strong> with{" "}
              <strong>TF-IDF cosine similarity</strong> between your profile text and each
              role description. Both components are shown to you, along with the weights used
              to combine them.
            </p>
            <p>
              There is <strong>no trained classifier</strong>. No large labelled dataset of
              career outcomes exists, so training one would mean fitting noise. Unsupervised
              similarity plus rule-based weighting is a deliberate choice, not a shortcut,
              and we say so in the evaluation report rather than implying more.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>What we are honest about</CardTitle>
          <CardDescription>Stated here rather than buried</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm text-muted-foreground md:grid-cols-2">
          <ul className="list-disc space-y-1 pl-5">
            <li>OCR is not supported, so a scanned PDF cannot be analysed.</li>
            <li>The engine understands English only.</li>
            <li>TF-IDF is lexical: a profile saying "torch" and a role saying "PyTorch" need the alias index to connect.</li>
          </ul>
          <ul className="list-disc space-y-1 pl-5">
            <li>There is no notion of seniority in the matching model.</li>
            <li>The evaluation runs on 24 synthetic hand-labelled profiles, which indicates behaviour rather than establishing statistical significance.</li>
            <li>Output is a suggestion, not a job offer or a hiring decision.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
