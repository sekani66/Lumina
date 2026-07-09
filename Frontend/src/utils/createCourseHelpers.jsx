const BASE_URL = import.meta.env.VITE_API_BASE

/**
 * POST /create/course/extract-pdf
 * Sends the raw PDF file via multipart/form-data.
 * Returns { extraction_meta, source_summary, preliminary_plan, key_concepts }
 */
export async function uploadPdf(file) {
  const form = new FormData()
  form.append('file', file)
  // model is optional — backend defaults to gpt-4o-mini
  const res = await fetch(`${BASE_URL}/create/course/extract-pdf`, {
    method: 'POST',
    body: form,
    // Do NOT set Content-Type — browser sets it with the correct multipart boundary
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `PDF extraction failed (${res.status})`)
  }
  return res.json()
}

/**
 * POST /create/course/prerequisites
 * AI path  : { topic, goal }
 * PDF path : { topic, goal, source_summary }
 * Returns array of { id, label } prerequisite objects.
 */
export async function fetchPrerequisites({ topic, goal, sourceSummary }) {
  const res = await fetch(`${BASE_URL}/create/course/prerequisites`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic,
      goal,
      ...(sourceSummary ? { source_summary: sourceSummary } : {}),
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error ${res.status}`)
  }
  return res.json()
}

/**
 * POST /create/course
 * AI path  : { topic, goal, no_source: true,  prerequisites }
 * PDF path : { topic, goal, no_source: false, prerequisites, source_summary }
 * Returns { course_details, prerequisites, course_plan }
 */
export async function fetchCoursePlan({ topic, goal, noSource, ratings, sourceSummary }) {
  const res = await fetch(`${BASE_URL}/create/course`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic,
      goal,
      no_source:     noSource,
      prerequisites: ratings,
      ...(!noSource && sourceSummary ? { source_summary: sourceSummary } : {}),
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Server error ${res.status}`)
  }
  return res.json()
}