export type MatchType = "exact" | "related" | "none"

export interface SkillMatch {
  skill: string
  match_type: MatchType
  score: number
  matched_to: string | null
}

export interface UpskillingRecommendation {
  skill: string
  reason: string
  resource: string
}

export interface InterviewQuestion {
  question: string
  category: string
}

export interface ComparisonResult {
  overall_score: number
  skill_score: number
  experience_score: number
  education_matched: boolean
  required_skill_matches: SkillMatch[]
  preferred_skill_matches: SkillMatch[]
  missing_required_skills: string[]
  missing_preferred_skills: string[]
  strengths_summary: string
  gaps_summary: string
  upskilling_recommendations: UpskillingRecommendation[]
  interview_questions: InterviewQuestion[]
  salary_insight: string
  errors: string[]
}

export interface UploadResponse {
  job_id: string
  message: string
}

export interface JobStatusResponse {
  job_id: string
  status: "processing" | "completed" | "failed"
  error?: string | null
}

export interface JobResultResponse {
  job_id: string
  status: "processing" | "completed" | "failed"
  result?: ComparisonResult | null
  error?: string | null
}
