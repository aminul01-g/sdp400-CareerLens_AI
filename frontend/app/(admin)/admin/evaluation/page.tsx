"use client";

/**
 * The evaluation report, charted.
 *
 * Reads the **committed** report from `GET /api/admin/evaluation` rather than
 * re-running the harness. That is deliberate: if the chart re-ran the evaluation it
 * could disagree with the document in the repository, and the document is the
 * artefact of record. Every number below is read straight off that payload.
 *
 * The corollary is that nothing here may be *derived*. A top-5 hit rate is
 * computable from `outcomes`, and it is deliberately absent: the harness does not
 * report it, so showing it here would put a number in the UI that no committed
 * document vouches for. The same reasoning removed the old `top5_hit_rate` card
 * and the `environment` / `notes` blocks — none of them exist in the payload.
 *
 * When the report is absent the page shows the command to generate it instead of
 * a 500.
 */
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Tooltip, XAxis, YAxis,
} from "recharts";
import { AlertTriangle, CheckCircle2, FileSearch, Target } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { LoadingPage } from "@/components/shared/Loading";
import { PageHeader } from "@/components/shared/PageHeader";
import { useChartSize } from "@/components/shared/useChartSize";
import { useEvaluation } from "@/lib/hooks/use-admin";
import type { EvaluationReport } from "@/lib/api/types";

const CHART_COLOURS = ["#6366f1", "#22c55e", "#f59e0b"];
const CHOSEN_COVERAGE_WEIGHT = 0.6;

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

/**
 * The payload carries role **slugs** (`time-series-forecasting-specialist`), not
 * titles. Splitting on the separator is presentation only — it recovers the words
 * the slug was built from and invents nothing.
 */
const humaniseSlug = (slug: string) =>
  slug
    .split("-")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

export default function AdminEvaluationPage() {
  const report = useEvaluation();

  // Chart geometry is measured here, not by recharts' ResponsiveContainer — see
  // useChartSize for why. Declared before the loading and error returns below,
  // because a hook that is skipped on one render and called on the next breaks
  // React's hook ordering.
  const components = useChartSize(256);
  const byFamily = useChartSize(320);
  const sweep = useChartSize(256);

  if (report.isPending) return <LoadingPage label="Loading the evaluation report" />;
  if (report.isError) {
    const notFound = report.error instanceof Error && "status" in report.error;
    return (
      <div className="space-y-4">
        <PageHeader title="Evaluation" />
        {notFound ? (
          <EmptyState
            icon={<FileSearch className="h-8 w-8" aria-hidden="true" />}
            title="The evaluation has not been run yet"
            description={
              <>
                Generate it from the backend with{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">python -m app.ml.evaluation</code>
                . The harness reads the hand-labelled profiles and the version-controlled job
                knowledge base, then writes{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">docs/evaluation_report.md</code>.
              </>
            }
          />
        ) : (
          <ErrorState error={report.error} onRetry={() => void report.refetch()} />
        )}
      </div>
    );
  }

  const data: EvaluationReport = report.data;
  const { metrics, recommendation } = data;

  // `per_family` arrives keyed by family name; recharts needs a flat array.
  const perFamily = Object.entries(data.per_family).map(([family, value]) => ({
    family,
    ...value,
  }));

  const headline = [
    { label: "Top-1 accuracy", value: percent(metrics.top1_accuracy), hint: "the expected role ranked first" },
    {
      label: "Top-3 hit rate",
      value: percent(metrics.top3_hit_rate),
      hint: `target ≥ ${percent(data.target_top3_hit_rate)}`,
    },
    {
      label: "Mean reciprocal rank",
      value: metrics.mean_reciprocal_rank.toFixed(3),
      hint: "rewards correct ordering",
    },
    {
      label: "Mean compatibility of expected",
      value: percent(metrics.mean_compatibility_of_expected),
      hint: `noise floor ${percent(data.noise_floor)}`,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evaluation"
        description={`The matching engine measured against ${metrics.n_profiles} hand-labelled profiles. These are measured results, not projections.`}
        actions={
          <Badge variant="outline">generated {new Date(data.generated_at).toLocaleDateString()}</Badge>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {headline.map((metric) => (
          <Card key={metric.label}>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">{metric.label}</p>
              <p className="mt-1 text-3xl font-bold">{metric.value}</p>
              <p className="text-xs text-muted-foreground">{metric.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Alert variant={data.meets_target ? "default" : "destructive"}>
        {data.meets_target ? (
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
        ) : (
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
        )}
        <AlertTitle>
          {data.meets_target
            ? `Target met — top-3 hit rate is ${percent(metrics.top3_hit_rate)} against a target of ${percent(data.target_top3_hit_rate)}`
            : `Target missed — top-3 hit rate is ${percent(metrics.top3_hit_rate)} against a target of ${percent(data.target_top3_hit_rate)}`}
        </AlertTitle>
        <AlertDescription>
          Measured over {metrics.n_profiles} profiles at a coverage weight of{" "}
          {recommendation.coverage_weight.toFixed(2)}. The same gate runs as a test, so a
          regression fails the build rather than going unnoticed.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Score components at the chosen weighting</CardTitle>
          <CardDescription>
            The two halves of the formula, averaged across every profile. Skill coverage does
            nearly all the work; the TF-IDF term is small by design.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div ref={components.ref} className="w-full" style={{ height: components.height }}>
            {components.width > 0 ? (
              <BarChart
                width={components.width}
                height={components.height}
                data={[
                  { name: "Skill coverage", value: metrics.component_means.skill_coverage },
                  { name: "TF-IDF similarity", value: metrics.component_means.tfidf_similarity },
                  { name: "Combined compatibility", value: metrics.component_means.compatibility },
                  { name: "Noise floor", value: data.noise_floor },
                ]}
                margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Tooltip formatter={(value: number) => [percent(value), "mean"]} />
                <Bar dataKey="value" name="Mean" radius={[3, 3, 0, 0]} maxBarSize={80}>
                  {["skill_coverage", "tfidf_similarity", "compatibility", "noise"].map((key) => (
                    <Cell key={key} fill={key === "noise" ? "#94a3b8" : CHART_COLOURS[0]} />
                  ))}
                </Bar>
              </BarChart>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Metrics by role family</CardTitle>
          <CardDescription>Where the engine is strong and where it is not</CardDescription>
        </CardHeader>
        <CardContent>
          {perFamily.length === 0 ? (
            <p className="text-sm text-muted-foreground">No per-family breakdown recorded.</p>
          ) : (
            <div ref={byFamily.ref} className="w-full" style={{ height: byFamily.height }}>
              {byFamily.width > 0 ? (
                <BarChart
                  width={byFamily.width}
                  height={byFamily.height}
                  data={perFamily}
                  margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
                  <XAxis dataKey="family" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={70} interval={0} />
                  <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                  <Tooltip
                    formatter={(value: number, name: string) =>
                      [name === "mean_reciprocal_rank" ? value.toFixed(3) : percent(value), name]
                    }
                  />
                  <Legend />
                  <Bar dataKey="top1_accuracy" name="top-1 accuracy" fill={CHART_COLOURS[0]} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="top3_hit_rate" name="top-3 hit rate" fill={CHART_COLOURS[1]} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="mean_reciprocal_rank" name="MRR" fill={CHART_COLOURS[2]} radius={[3, 3, 0, 0]} />
                </BarChart>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Weight sweep</CardTitle>
          <CardDescription>
            All metrics at each weighting. Published in full so a reader sees the sensitivity
            rather than only the chosen value.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Table>
            <caption className="sr-only">Top-1, top-3 and MRR at each coverage/TF-IDF weighting</caption>
            <TableHeader>
              <TableRow>
                <TableHead>Coverage weight</TableHead>
                <TableHead>TF-IDF weight</TableHead>
                <TableHead className="text-right">Top-1</TableHead>
                <TableHead className="text-right">Top-3</TableHead>
                <TableHead className="text-right">MRR</TableHead>
                <TableHead className="text-right">Mean compat.</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.sweep.map((row) => {
                const chosen = row.coverage_weight === CHOSEN_COVERAGE_WEIGHT;
                return (
                  <TableRow key={row.coverage_weight} className={chosen ? "bg-primary/5" : undefined}>
                    <TableCell className="font-mono tabular-nums">
                      {row.coverage_weight.toFixed(2)}
                      {chosen ? <Badge className="ml-2" variant="secondary">chosen</Badge> : null}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">{row.tfidf_weight.toFixed(2)}</TableCell>
                    <TableCell className="text-right tabular-nums">{percent(row.top1_accuracy)}</TableCell>
                    <TableCell className="text-right tabular-nums">{percent(row.top3_hit_rate)}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.mean_reciprocal_rank.toFixed(3)}</TableCell>
                    <TableCell className="text-right tabular-nums">{percent(row.mean_compatibility_of_expected)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          <div ref={sweep.ref} className="w-full" style={{ height: sweep.height }}>
            {sweep.width > 0 ? (
              <BarChart
                width={sweep.width}
                height={sweep.height}
                data={data.sweep}
                margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
                <XAxis dataKey="coverage_weight" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}`} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Tooltip formatter={(value: number, name: string) => [percent(value), name]} labelFormatter={(label) => `coverage weight ${label}`} />
                <Legend />
                <Bar dataKey="top3_hit_rate" name="top-3 hit rate" radius={[3, 3, 0, 0]}>
                  {data.sweep.map((row) => (
                    <Cell
                      key={row.coverage_weight}
                      fill={row.coverage_weight === CHOSEN_COVERAGE_WEIGHT ? "#6366f1" : "#c7d2fe"}
                    />
                  ))}
                </Bar>
              </BarChart>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Per-profile results</CardTitle>
          <CardDescription>
            Each profile's expected role, where it actually ranked, and the rationale recorded
            before the engine was run.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <caption className="sr-only">Per-profile evaluation results</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Profile</TableHead>
                  <TableHead>Expected role</TableHead>
                  <TableHead className="text-right">Rank</TableHead>
                  <TableHead className="text-right">Compat.</TableHead>
                  <TableHead>Top 3 predicted</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.outcomes.map((profile) => (
                  <TableRow key={profile.id}>
                    <TableCell>
                      <p className="font-medium">{profile.id}</p>
                      <p className="max-w-48 truncate text-xs text-muted-foreground">{profile.name}</p>
                      {profile.note ? (
                        <p className="mt-1 max-w-48 text-xs text-amber-600 dark:text-amber-500">
                          {profile.note}
                        </p>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <p className="text-sm">{humaniseSlug(profile.expected_role)}</p>
                      <p className="text-xs text-muted-foreground">{profile.expected_family}</p>
                    </TableCell>
                    <TableCell className="text-right">
                      {profile.expected_rank == null ? (
                        <Badge variant="secondary">unranked</Badge>
                      ) : profile.expected_rank <= 3 ? (
                        <Badge>{profile.expected_rank}</Badge>
                      ) : (
                        <span className="tabular-nums">{profile.expected_rank}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {percent(profile.expected_compatibility)}
                    </TableCell>
                    <TableCell>
                      <ol className="list-decimal space-y-0.5 pl-4 text-xs text-muted-foreground">
                        {profile.top3_roles.map((slug) => (
                          <li key={slug}>
                            {humaniseSlug(slug)}
                            {slug === profile.expected_role ? (
                              <Badge className="ml-2" variant="secondary">expected</Badge>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" aria-hidden="true" />
            What this report is
          </CardTitle>
          <CardDescription>
            Provenance of the numbers above. The caveats that qualify them live in{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">docs/limitations.md</code> and{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">docs/evaluation_report.md</code>,
            not here — this page only shows what the harness measured.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            {[
              ["Report schema", data.schema_version],
              ["Generated", data.generated_at],
              ["Profiles", String(metrics.n_profiles)],
              ["Chosen coverage weight", recommendation.coverage_weight.toFixed(2)],
              ["Chosen TF-IDF weight", recommendation.tfidf_weight.toFixed(2)],
              ["Noise floor", percent(data.noise_floor)],
            ].map(([term, value]) => (
              <div key={term} className="flex justify-between gap-2 border-b pb-1">
                <dt>{term}</dt>
                <dd className="font-mono">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
