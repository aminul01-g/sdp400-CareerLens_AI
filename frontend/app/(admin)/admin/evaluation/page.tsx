"use client";

/**
 * The evaluation report, charted.
 *
 * Reads the **committed** report from `GET /api/admin/evaluation` rather than
 * re-running the harness. That is deliberate: if the chart re-ran the evaluation it
 * could disagree with the document in the repository, and the document is the
 * artefact of record. When the report is absent the page shows the command to
 * generate it instead of a 500.
 *
 * Every number here came from a measurement. Nothing on this page is illustrative.
 */
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
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
import { useEvaluation } from "@/lib/hooks/use-admin";

const CHART_COLOURS = ["#6366f1", "#22c55e", "#f59e0b"];

export default function AdminEvaluationPage() {
  const report = useEvaluation();

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
                . The harness reads the 24 hand-labelled profiles and the version-controlled job
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

  const data = report.data;
  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evaluation"
        description="The matching engine measured against 24 hand-labelled profiles. These are measured results, not projections."
        actions={<Badge variant="outline">generated {new Date(data.generated_at).toLocaleDateString()}</Badge>}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Top-1 accuracy", value: percent(data.metrics.top1_accuracy), hint: "the expected role ranked first" },
          { label: "Top-3 hit rate", value: percent(data.metrics.top3_hit_rate), hint: `target ≥ ${percent(data.target.top3_hit_rate)}` },
          { label: "Top-5 hit rate", value: percent(data.metrics.top5_hit_rate), hint: "headroom above the target" },
          { label: "Mean reciprocal rank", value: data.metrics.mean_reciprocal_rank.toFixed(3), hint: "rewards correct ordering" },
        ].map((metric) => (
          <Card key={metric.label}>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">{metric.label}</p>
              <p className="mt-1 text-3xl font-bold">{metric.value}</p>
              <p className="text-xs text-muted-foreground">{metric.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Alert variant={data.target.met ? "default" : "destructive"}>
        {data.target.met ? (
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
        ) : (
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
        )}
        <AlertTitle>
          {data.target.met
            ? `Target met — top-3 hit rate is ${percent(data.metrics.top3_hit_rate)} against a target of ${percent(data.target.top3_hit_rate)}`
            : `Target missed — top-3 hit rate is ${percent(data.metrics.top3_hit_rate)} against a target of ${percent(data.target.top3_hit_rate)}`}
        </AlertTitle>
        <AlertDescription>
          Measured over {data.profiles} profiles. The same gate runs as a test, so a regression
          fails the build rather than going unnoticed.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Metrics by role family</CardTitle>
          <CardDescription>Where the engine is strong and where it is not</CardDescription>
        </CardHeader>
        <CardContent>
          {data.per_family.length === 0 ? (
            <p className="text-sm text-muted-foreground">No per-family breakdown recorded.</p>
          ) : (
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.per_family} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
                  <XAxis dataKey="family" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={70} interval={0} />
                  <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                  <Tooltip
                    formatter={(value: number, name: string) =>
                      [name === "top3" ? percent(value) : value.toFixed(2), name]
                    }
                  />
                  <Legend />
                  <Bar dataKey="top1" name="top-1 accuracy" fill={CHART_COLOURS[0]} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="top3" name="top-3 hit rate" fill={CHART_COLOURS[1]} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="mrr" name="MRR" fill={CHART_COLOURS[2]} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
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
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.weight_sweep.map((row) => {
                const chosen = row.coverage_weight === 0.6;
                return (
                  <TableRow key={row.coverage_weight} className={chosen ? "bg-primary/5" : undefined}>
                    <TableCell className="font-mono tabular-nums">
                      {row.coverage_weight.toFixed(2)}
                      {chosen ? <Badge className="ml-2" variant="secondary">chosen</Badge> : null}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">{row.tfidf_weight.toFixed(2)}</TableCell>
                    <TableCell className="text-right tabular-nums">{percent(row.top1)}</TableCell>
                    <TableCell className="text-right tabular-nums">{percent(row.top3)}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.mrr.toFixed(3)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.weight_sweep} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
                <XAxis dataKey="coverage_weight" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v.toFixed(1)}`} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} />
                <Tooltip formatter={(value: number, name: string) => [percent(value), name]} labelFormatter={(label) => `coverage weight ${label}`} />
                <Legend />
                <Bar dataKey="top3" name="top-3 hit rate" radius={[3, 3, 0, 0]}>
                  {data.weight_sweep.map((row) => (
                    <Cell key={row.coverage_weight} fill={row.coverage_weight === 0.6 ? "#6366f1" : "#c7d2fe"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
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
                  <TableHead>Top 3 predicted</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.per_profile.map((profile) => (
                  <TableRow key={profile.id}>
                    <TableCell>
                      <p className="font-medium">{profile.id}</p>
                      <p className="max-w-48 truncate text-xs text-muted-foreground">{profile.name}</p>
                    </TableCell>
                    <TableCell>
                      <p className="text-sm">{profile.expected_role}</p>
                      <p className="text-xs text-muted-foreground">{profile.expected_family}</p>
                    </TableCell>
                    <TableCell className="text-right">
                      {profile.expected_rank == null ? (
                        <Badge variant="secondary">not in top 10</Badge>
                      ) : profile.expected_rank <= 3 ? (
                        <Badge>{profile.expected_rank}</Badge>
                      ) : (
                        <span className="tabular-nums">{profile.expected_rank}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <ol className="list-decimal space-y-0.5 pl-4 text-xs text-muted-foreground">
                        {profile.top3.map((role) => (
                          <li key={role.job_role_id}>
                            {role.title}{" "}
                            <span className="font-mono tabular-nums">{role.compatibility_pct}%</span>
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
            What this does and does not claim
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
            {data.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
          <dl className="mt-4 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            {Object.entries(data.environment).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-2 border-b pb-1">
                <dt>{key}</dt>
                <dd className="font-mono">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
