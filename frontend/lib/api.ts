// API client，包装 backend /api/* 接口
// 通过 next.config.mjs 的 rewrite，请求会代理到 backend

const API_BASE = "/api";

// ============================================================
// 类型（跟 backend/models 对齐）
// ============================================================
export interface GrepHit {
  rule_id: string;
  rule_name: string;
  line_no: number;
  line_content: string;
  matched_text: string;
  is_exception: boolean;
}

export interface GrepReport {
  can_publish: boolean;
  total_hits: number;
  rule_summary: Record<string, number>;
  hits: GrepHit[];
  exceptions: GrepHit[];
}

export interface WriteRequest {
  topic: string;
  material?: string;
  angle?: string;
}

export interface WriteResponse {
  session_id: number | null;
  article_markdown: string;
  article_path: string;
  char_count: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  grep_report: GrepReport;
}

export interface TopicsRequest {
  direction: string;
  seed_links?: string[];
  avoid_topics?: string[];
}

export interface TopicsResponse {
  candidates_markdown: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  web_search_count: number;
}

export interface OpsRequest {
  article_path: string;
  topic: string;
  session_id?: number;
}

export interface OpsResponse {
  ops_markdown: string;
  ops_path: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  grep_report: GrepReport;
}

export interface ImageSpec {
  image_id: string;
  image_title: string;
  prompt_zh: string | null;
  prompt_en: string | null;
  negative_words: string | null;
  is_required: boolean;
}

export interface ImagesParseResponse {
  specs: ImageSpec[];
  estimated_cost_usd: number;
}

export interface GeneratedImage {
  index: number;
  image_path: string;
  revised_prompt: string;
}

export interface ImagesGenerateResponse {
  images_dir: string;
  by_spec: Record<string, GeneratedImage[]>;
  total_cost_usd: number;
}

export interface Session {
  id: number;
  topic: string;
  angle: string | null;
  material: string | null;
  stage: string;
  can_publish: boolean;
  grep_hits: number;
  article_path: string | null;
  ops_path: string | null;
  images_dir: string | null;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost_usd: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
}

// ============================================================
// HTTP helpers
// ============================================================
async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`API ${path} failed (${resp.status}): ${detail}`);
  }
  return resp.json();
}

async function get<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`);
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`API ${path} failed (${resp.status}): ${detail}`);
  }
  return resp.json();
}

// ============================================================
// API 客户端
// ============================================================
export const api = {
  topics: (req: TopicsRequest) =>
    post<TopicsRequest, TopicsResponse>("/topics", req),

  write: (req: WriteRequest) => post<WriteRequest, WriteResponse>("/write", req),

  ops: (req: OpsRequest) => post<OpsRequest, OpsResponse>("/ops", req),

  imagesParse: (ops_path: string, required_only = true) =>
    post<{ ops_path: string; required_only: boolean }, ImagesParseResponse>(
      "/images/parse",
      { ops_path, required_only },
    ),

  imagesGenerate: (params: {
    ops_path: string;
    required_only?: boolean;
    candidates?: number;
    size?: string;
    quality?: string;
  }) =>
    post<typeof params, ImagesGenerateResponse>("/images/generate", params),

  listSessions: (limit = 50, stage?: string) =>
    get<{ sessions: Session[]; total: number }>(
      `/sessions?limit=${limit}${stage ? `&stage=${stage}` : ""}`,
    ),

  getSession: (id: number) => get<Session>(`/sessions/${id}`),
};

// 成本估算（Sonnet 4.5 定价，跟 backend session.py 一致）
export function estimateCost(
  inputTokens: number,
  outputTokens: number,
  cacheRead = 0,
  cacheCreation = 0,
): number {
  return (
    (inputTokens / 1_000_000) * 3.0 +
    (outputTokens / 1_000_000) * 15.0 +
    (cacheRead / 1_000_000) * 0.3 +
    (cacheCreation / 1_000_000) * 3.75
  );
}
