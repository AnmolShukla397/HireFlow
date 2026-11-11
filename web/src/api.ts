export type User = { email: string; display_name: string; modes: string[]; mode: 'recruiter' | 'applicant' | null }
export type Check = { area: string; status: string; title: string; detail: string; action: string }
export type Suggestion = { id: string; kind: string; category?: string; reason: string; before?: string; after?: string; line_index?: number; skill?: string; placement?: string; source?: string }
export type Report = {
  candidate: string; filename: string; summary: string; resume_text: string; overall: number; ats: number; skill: number; semantic: number; experience: number; education: number;
  matched_skills: string[]; missing_skills: string[]; job_skills: string[]; resume_skills: string[]; suggestions: Suggestion[];
  audit?: Check[]; keyword_map?: { skill: string; status: string; detail: string }[]; sections: Record<string,string[]>;
  contact: Record<string,string>; skill_evidence: Record<string,string[]>; ats_factors: Record<string,number>; ats_weights: Record<string,number>; line_reviews: {line:string;text:string;assessment:string;reason:string}[];
  semantic_method: string; scoring_version: string; required_years: number; resume_years: number; word_count: number; headings: string[]
}
export type Project = { id: string; company: string; role: string; status: string; job_text: string; resume_text: string; cover_letter: string; notes: string; updated_at: string }
export type Version = { id: string; name: string; target_role: string; template: string; resume_text: string; source_id?: string; created_at: string }

export class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }

export async function api<T>(path: string, data?: unknown, method = data === undefined ? 'GET' : 'POST'): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method, credentials: 'same-origin',
    headers: { 'X-HireFlow-Request': '1', ...(data instanceof FormData ? {} : data === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: data === undefined ? undefined : data instanceof FormData ? data : JSON.stringify(data),
  })
  if (!response.ok) {
    let detail = `Request failed (${response.status}).`
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : Array.isArray(body.detail) ? body.detail.map((item: {msg?:string}) => item.msg || 'Invalid field').join('; ') : detail } catch { /* non-JSON error */ }
    if (response.status === 401 && path !== '/auth/login' && path !== '/session') window.dispatchEvent(new Event('hireflow:expired'))
    throw new ApiError(detail, response.status)
  }
  return response.json() as Promise<T>
}

export async function download(path: string, data: unknown): Promise<void> {
  const response = await fetch(`/api${path}`, { method:'POST', credentials:'same-origin', headers: {'X-HireFlow-Request':'1','Content-Type':'application/json'}, body:JSON.stringify(data) })
  if (!response.ok) {
    let detail = 'Export failed.'
    try { detail = (await response.json()).detail || detail } catch { /* non-JSON error */ }
    throw new Error(detail)
  }
  const blob = await response.blob()
  const name = /filename="?([^";]+)"?/.exec(response.headers.get('Content-Disposition') || '')?.[1] || 'hireflow-download'
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a'); link.href = url; link.download = name; link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export async function previewPdf(data: {text:string;template:string;options:Record<string,number>;highlights:string[]}, signal: AbortSignal): Promise<Blob> {
  const response = await fetch('/api/applicant/preview', {
    method: 'POST', credentials: 'same-origin', signal,
    headers: {'X-HireFlow-Request':'1','Content-Type':'application/json'}, body: JSON.stringify(data),
  })
  if (!response.ok) {
    let detail = 'PDF preview could not be generated.'
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : detail } catch { /* non-JSON error */ }
    if (response.status === 401) window.dispatchEvent(new Event('hireflow:expired'))
    throw new Error(detail)
  }
  return response.blob()
}

export async function readDocument(file: File): Promise<string> {
  const data = new FormData(); data.append('file', file)
  return (await api<{text:string}>('/documents/extract', data)).text
}
