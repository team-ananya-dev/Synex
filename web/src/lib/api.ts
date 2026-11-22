// Typed client for the Synex server. Shapes follow contracts/API.md and contracts/EVENTS.md.

export const API_BASE = process.env.NEXT_PUBLIC_SYNEX_API ?? "http://localhost:8000";

export type CaseState =
  | "DRAFT" | "PLANNED" | "SOURCING" | "AWAITING_APPROVAL" | "COLLECTING"
  | "SYNTHESIZING" | "DELIVERED" | "REFUSED" | "FAILED";

export const TERMINAL_STATES: CaseState[] = ["REFUSED", "FAILED"];

export type QuestionScreen = { verdict: "allow" | "refuse" | "rewrite"; reason: string; effective_question: string };

export type SubQuestion = {
  index: number;
  text: string;
  expertise: string;
  title_keywords: string[];
  target_companies: { name: string; basis: "named" | "inferred" }[];
};

export type Company = {
  asked: string;
  basis: "named" | "inferred";
  resolved: boolean;
  chosen?: { company_id: number; name: string; domain: string | null; size: string | null; industries: string[] };
  total_matches?: number;
};

// ---- operator view (GET /cases/{id}) ----

// Candidate fields. name, headline, profile_url and location are operator-only:
// never render them on a customer screen (Dev's note, 2026-11-22).
export type Candidate = {
  person_id: number;
  name: string;
  headline: string | null;
  location: string | null;
  profile_url: string | null;
  title: string | null;
  function: string | null;
  start_date: string | null;
  end_date: string | null;
  tenure_months: number | null;
  company_id: number;
  crustdata_fit?: string | null;
};

export type RankedCandidate = Candidate & {
  score: number;
  fit?: "strong" | "partial";
  evidence?: string[];
  reason: string;
  data_conflict?: string;
  verdict: "pass" | "review";
};

export type Excluded = { person_id: number; name: string; score: number; title: string | null; why: string };

export type RankStage = Record<string, { ranked: RankedCandidate[]; excluded?: Excluded[] }>;
export type SourceStage = Record<string, { companies: Company[]; candidates: Candidate[] }>;
export type ScreenStage = Record<string, {
  person_id: number;
  verdict: "pass" | "review" | "fail";
  results: { rule: string; passed: boolean; reason: string; flag?: boolean }[];
}[]>;

export type CaseView = {
  id: string;
  question: string;
  state: CaseState;
  refusal_reason: string | null;
  created_at: string;
  stages: {
    s1_question_screen?: QuestionScreen;
    s2_decomposer?: SubQuestion[];
    s3_sourcer?: SourceStage;
    s4_people_screen?: ScreenStage;
    s5_ranker?: RankStage;
    s5b_enrich_rerank?: RankStage;
    [stage: string]: unknown;
  };
  cost: { crustdata_credits: number; model_usd: number; credit_cap: number };
};

// ---- customer view (GET /customer/cases/{id}); never contains a name, headline, link, city or email ----

export type ExpertCard = {
  ref: string;
  role: string | null;
  company: string | null;
  tenure_months: number | null;
  left_year: string | null;
  country: string | null;
  fit: "strong" | "partial";
  score: number;
  reason: string;
  evidence: string[];
  evidence_hidden: number;
};

export type Quote = { subquestions: number; price_per_subquestion: number; hold_amount: number; currency: string };

export type LedgerEntry = {
  kind: "HOLD" | "CAPTURE" | "RELEASE";
  amount: number;
  currency: string;
  ref: string | null;
  note: string;
  created_by: string;
  created_at: string;
};

export type CustomerCase = {
  id: string;
  question: string;
  state: CaseState;
  refusal_reason: string | null;
  created_at: string;
  plan: SubQuestion[] | null;
  quote: Quote | null;
  approval: { panel_size?: number; budget?: number; hold?: number } | null;
  screening: Record<string, {
    considered: number; pass: number; review: number; fail: number;
    excluded: { ref: string; reasons: string[] }[];
  }>;
  panel: Record<string, ExpertCard[]>;
  outreach: Partial<Record<OutreachStatus, number>>;
  ledger: {
    balance: { held: number; captured: number; released: number; remaining: number; currency: string };
    entries: LedgerEntry[];
  };
  cost: { crustdata_credits: number; model_usd: number; credit_cap: number };
};

export type CaseSummary = { id: string; question: string; state: CaseState; created_at: string };

export type OutreachStatus = "DRAFTED" | "SENT" | "REJECTED" | "BLOCKED" | "FAILED";

export type Approval = {
  id: number;
  case_id: string;
  person_id: number;
  name: string;
  persona_title: string | null;
  persona_company: string | null;
  tenure_months: number | null;
  subquestion_indices: number[];
  flags: { rule: string; reason: string }[];
  to_address: string;
  subject: string;
  body: string;
  status: OutreachStatus;
  decided_by: string | null;
  decided_at: string | null;
  sent_at: string | null;
  block_reason: string | null;
  llm_call_id: string | null;
  created_at: string;
};

export type Approver = "dev" | "ananya";

export type SynexEvent = { id: number; type: string; at: string; [field: string]: unknown };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // body was not JSON; keep the status text
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createCase: (question: string) =>
    request<{ id: string; state: CaseState }>("/cases", { method: "POST", body: JSON.stringify({ question }) }),
  // customer routes
  listCustomerCases: () => request<CaseSummary[]>("/customer/cases"),
  getCustomerCase: (id: string) => request<CustomerCase>(`/customer/cases/${id}`),
  approvePlan: (id: string, panel_size: number, budget: number) =>
    request<{ id: string; state: CaseState; hold: Quote }>(`/customer/cases/${id}/approve-plan`, {
      method: "POST", body: JSON.stringify({ panel_size, budget }),
    }),
  // operator routes: real people's details, operator screens only
  getCase: (id: string) => request<CaseView>(`/cases/${id}`),
  listApprovals: (filters: { status?: OutreachStatus; case_id?: string } = {}) => {
    const q = new URLSearchParams(Object.entries(filters).filter(([, v]) => v) as [string, string][]);
    return request<Approval[]>(`/approvals${q.size ? `?${q}` : ""}`);
  },
  decide: (id: number, decision: "approve" | "reject", approver: Approver) =>
    request<Approval>(`/approvals/${id}/${decision}`, { method: "POST", body: JSON.stringify({ approver }) }),
};

export type Audience = "customer" | "operator";

export const eventsUrl = (caseId: string, audience: Audience, after = 0) =>
  `${API_BASE}${audience === "customer" ? "/customer" : ""}/cases/${caseId}/events?after=${after}`;
