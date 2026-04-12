import { useEffect, useMemo, useState, type FormEvent } from "react"
import {
  BadgeCheck,
  BriefcaseBusiness,
  CircleAlert,
  Gauge,
  GraduationCap,
  LoaderCircle,
  Sparkles,
  Target,
  Upload,
} from "lucide-react"

import { ThemeToggle } from "@/components/theme-toggle"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { demoResult } from "@/lib/demo-result"
import type {
  ComparisonResult,
  JobResultResponse,
  JobStatusResponse,
  SkillMatch,
  UploadResponse,
} from "@/lib/types"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"

type Theme = "light" | "dark"
type JobPhase = "idle" | "processing" | "completed" | "failed"

interface JobState {
  jobId: string | null
  status: JobPhase
  error: string | null
  startedAt: number | null
}

interface MatchRow extends SkillMatch {
  importance: "required" | "preferred"
}

function getInitialTheme(): Theme {
  if (typeof window === "undefined") {
    return "light"
  }

  const storedTheme = window.localStorage.getItem("job-prep-theme")

  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

function formatScore(score: number) {
  return `${Math.round(score)}%`
}

function formatMatchType(matchType: SkillMatch["match_type"]) {
  if (matchType === "exact") {
    return "Exact"
  }

  if (matchType === "related") {
    return "Adjacent"
  }

  return "Missing"
}

function getMatchBadgeVariant() {
  return "outline" as const
}

function getMatchBadgeClassName(matchType: SkillMatch["match_type"]) {
  if (matchType === "exact") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
  }

  if (matchType === "related") {
    return "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300"
  }

  if (matchType === "none") {
    return "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
  }

  return ""
}

function getStatusSnapshot(job: JobState) {
  if (job.status === "completed") {
    return { progress: 100, label: "Completed" }
  }

  if (job.status === "failed") {
    return { progress: 100, label: "Failed" }
  }

  if (job.status === "processing") {
    return { progress: 50, label: "In progress" }
  }

  return { progress: 0, label: "Waiting" }
}

function formatJobStatus(status: JobPhase) {
  if (status === "idle") {
    return "Waiting"
  }

  if (status === "processing") {
    return "In progress"
  }

  if (status === "completed") {
    return "Completed"
  }

  return "Failed"
}

function getJobStatusBadgeClassName(status: JobPhase) {
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
  }

  if (status === "failed") {
    return "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300"
  }

  return ""
}

async function parseError(response: Response) {
  const message = await response.text()
  return message || `Request failed with status ${response.status}.`
}

function App() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jobDescriptionFile, setJobDescriptionFile] = useState<File | null>(null)
  const [job, setJob] = useState<JobState>({
    jobId: null,
    status: "idle",
    error: null,
    startedAt: null,
  })
  const [report, setReport] = useState<ComparisonResult | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
    window.localStorage.setItem("job-prep-theme", theme)
  }, [theme])

  useEffect(() => {
    if (job.status !== "processing" || !job.jobId) {
      return
    }

    let cancelled = false

    async function pollJob() {
      try {
        const statusResponse = await fetch(`${API_BASE_URL}/status/${job.jobId}`)

        if (!statusResponse.ok) {
          throw new Error(await parseError(statusResponse))
        }

        const statusData = (await statusResponse.json()) as JobStatusResponse

        if (cancelled || statusData.status === "processing") {
          return
        }

        if (statusData.status === "failed") {
          setJob((currentJob) => ({
            ...currentJob,
            status: "failed",
            error: statusData.error ?? "The backend job failed.",
          }))
          return
        }

        const resultResponse = await fetch(`${API_BASE_URL}/result/${job.jobId}`)

        if (!resultResponse.ok) {
          throw new Error(await parseError(resultResponse))
        }

        const resultData = (await resultResponse.json()) as JobResultResponse

        if (!resultData.result) {
          throw new Error("The backend completed, but no comparison payload was returned.")
        }

        setReport(resultData.result)
        setJob((currentJob) => ({
          ...currentJob,
          status: "completed",
          error: null,
        }))
      } catch (error) {
        if (cancelled) {
          return
        }

        setJob((currentJob) => ({
          ...currentJob,
          status: "failed",
          error: error instanceof Error ? error.message : "Unable to refresh job status.",
        }))
      }
    }

    void pollJob()
    const intervalId = window.setInterval(() => {
      void pollJob()
    }, 3000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [job.jobId, job.status])

  const visibleReport = report ?? demoResult
  const statusSnapshot = getStatusSnapshot(job)

  const matchRows = useMemo<MatchRow[]>(() => {
    const requiredRows = visibleReport.required_skill_matches.map((match) => ({
      ...match,
      importance: "required" as const,
    }))
    const preferredRows = visibleReport.preferred_skill_matches.map((match) => ({
      ...match,
      importance: "preferred" as const,
    }))

    return [...requiredRows, ...preferredRows]
  }, [visibleReport])

  const scoreCards = [
    {
      label: "Overall fit",
      value: formatScore(visibleReport.overall_score),
      detail: "Combined fit across the full comparison pipeline.",
      icon: Target,
    },
    {
      label: "Skill alignment",
      value: formatScore(visibleReport.skill_score),
      detail: "Coverage of required and preferred skills.",
      icon: Gauge,
    },
    {
      label: "Experience depth",
      value: formatScore(visibleReport.experience_score),
      detail: "Experience fit against the role requirements.",
      icon: BriefcaseBusiness,
    },
    {
      label: "Education match",
      value: visibleReport.education_matched ? "Aligned" : "Review",
      detail: "Education overlap with the job criteria.",
      icon: GraduationCap,
    },
  ] as const

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!resumeFile || !jobDescriptionFile) {
      setJob({
        jobId: null,
        status: "failed",
        error: "Select both files before starting the analysis.",
        startedAt: null,
      })
      return
    }

    const formData = new FormData()
    formData.append("resume", resumeFile)
    formData.append("job_description", jobDescriptionFile)

    setIsUploading(true)
    setReport(null)

    try {
      const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      })

      if (!uploadResponse.ok) {
        throw new Error(await parseError(uploadResponse))
      }

      const uploadData = (await uploadResponse.json()) as UploadResponse

      setJob({
        jobId: uploadData.job_id,
        status: "processing",
        error: null,
        startedAt: Date.now(),
      })
    } catch (error) {
      setJob({
        jobId: null,
        status: "failed",
        error: error instanceof Error ? error.message : "Upload failed.",
        startedAt: null,
      })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-4 py-6 md:px-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="font-heading text-2xl tracking-tight md:text-3xl">
            Aligno
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground md:text-base">
            Upload a resume and job description to review fit, gaps, and interview prep.
          </p>
        </div>
        <ThemeToggle checked={theme === "dark"} onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload documents</CardTitle>
          <CardDescription>
            Start a new analysis run.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="resume">Resume</FieldLabel>
                <Input
                  id="resume"
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(event) => setResumeFile(event.target.files?.[0] ?? null)}
                />
                <FieldDescription>
                  Select a PDF or image file.
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="job-description">Job description</FieldLabel>
                <Input
                  id="job-description"
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={(event) => setJobDescriptionFile(event.target.files?.[0] ?? null)}
                />
                <FieldDescription>
                  Select the target role document.
                </FieldDescription>
              </Field>
            </FieldGroup>

            <div className="flex flex-col gap-3 rounded-lg border p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium">Status</span>
                <Badge
                  variant="outline"
                  className={getJobStatusBadgeClassName(job.status)}
                >
                  {formatJobStatus(job.status)}
                </Badge>
              </div>
              <Progress value={statusSnapshot.progress} className="h-2" />
            </div>

            {job.error ? (
              <Alert variant="destructive">
                <CircleAlert className="size-4" />
                <AlertTitle>Processing issue</AlertTitle>
                <AlertDescription>{job.error}</AlertDescription>
              </Alert>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={isUploading || job.status === "processing"}>
                {isUploading || job.status === "processing" ? (
                  <LoaderCircle className="animate-spin" data-icon="inline-start" />
                ) : (
                  <Upload data-icon="inline-start" />
                )}
                {job.status === "processing" ? "Processing" : "Start analysis"}
              </Button>
              {job.jobId ? (
                <span className="text-sm text-muted-foreground">Job ID: {job.jobId}</span>
              ) : null}
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {scoreCards.map((card) => {
          const Icon = card.icon

          return (
            <Card key={card.label}>
              <CardHeader className="gap-2">
                <div className="flex items-center justify-between gap-3">
                  <CardDescription>{card.label}</CardDescription>
                  <Icon className="size-4 text-muted-foreground" />
                </div>
                <CardTitle className="text-3xl tracking-tight">{card.value}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{card.detail}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Tabs defaultValue="overview" className="gap-4">
        <TabsList variant="line">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="skills">Skill gaps</TabsTrigger>
          <TabsTrigger value="prep">Align</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="flex flex-col gap-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Strengths summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3 rounded-lg border p-4">
                  <BadgeCheck className="mt-0.5 size-4 text-muted-foreground" />
                  <p className="text-sm leading-7 text-muted-foreground">
                    {visibleReport.strengths_summary}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Gap summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3 rounded-lg border p-4">
                  <Sparkles className="mt-0.5 size-4 text-muted-foreground" />
                  <p className="text-sm leading-7 text-muted-foreground">
                    {visibleReport.gaps_summary}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Missing skills</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <span className="text-sm font-medium">Required</span>
                <div className="flex flex-wrap gap-2">
                  {visibleReport.missing_required_skills.length > 0 ? (
                    visibleReport.missing_required_skills.map((skill) => (
                      <Badge key={skill} variant="destructive">
                        {skill}
                      </Badge>
                    ))
                  ) : (
                    <Badge>No required gaps</Badge>
                  )}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <span className="text-sm font-medium">Preferred</span>
                <div className="flex flex-wrap gap-2">
                  {visibleReport.missing_preferred_skills.length > 0 ? (
                    visibleReport.missing_preferred_skills.map((skill) => (
                      <Badge key={skill} variant="outline">
                        {skill}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="secondary">Covered preferred signals</Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {visibleReport.errors.length > 0 ? (
            <Alert>
              <CircleAlert className="size-4" />
              <AlertTitle>Pipeline notes</AlertTitle>
              <AlertDescription>{visibleReport.errors.join(" ")}</AlertDescription>
            </Alert>
          ) : null}
        </TabsContent>

        <TabsContent value="skills">
          <Card>
            <CardHeader>
              <CardTitle>Skill coverage</CardTitle>
              <CardDescription>Required and preferred matches.</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Skill</TableHead>
                    <TableHead>Importance</TableHead>
                    <TableHead>Coverage</TableHead>
                    <TableHead>Matched evidence</TableHead>
                    <TableHead className="text-right">Score</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {matchRows.map((row) => (
                    <TableRow key={`${row.importance}-${row.skill}`}>
                      <TableCell className="font-medium">{row.skill}</TableCell>
                      <TableCell>
                        <Badge variant={row.importance === "required" ? "default" : "outline"}>
                          {row.importance}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={getMatchBadgeVariant()}
                          className={getMatchBadgeClassName(row.match_type)}
                        >
                          {formatMatchType(row.match_type)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {row.matched_to ?? "No matching evidence found"}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatScore(row.score * 100)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="prep" className="grid gap-4 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Upskilling recommendations</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {visibleReport.upskilling_recommendations.map((recommendation) => (
                <div key={recommendation.skill} className="rounded-lg border p-4">
                  <p className="text-sm font-medium">{recommendation.skill}</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {recommendation.reason}
                  </p>
                  <p className="mt-4 text-sm font-semibold text-foreground">
                    Recommended resource
                  </p>
                  <p className="mt-1 text-sm font-medium text-muted-foreground">
                    {recommendation.resource}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Interview questions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {visibleReport.interview_questions.map((question, index) => (
                <div key={`${question.category}-${index}`} className="rounded-lg border p-4">
                  <p className="text-sm font-medium leading-6">{question.question}</p>
                  <p className="mt-2 text-xs uppercase tracking-wide text-muted-foreground">
                    {question.category}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </main>
  )
}

export default App
