import { ApiError, post, request } from './api';

export type VisualCatalogState = 'staged' | 'under_review' | 'active' | 'withdrawn';
export type VisualReviewDecision = 'accepted' | 'rejected' | 'needs_more';
export interface VisualContentChecks {
  source_page_match: boolean;
  geometry_correct: boolean;
  native_text_correct: boolean;
  reading_order_correct: boolean;
  content_correct: boolean;
  notation_units_correct: boolean;
}
export interface VisualCatalogVersion {
  id: string;
  book: string;
  document_id: string;
  document_title: string;
  document_version_id: string;
  source_sha256: string;
  catalog_sha256: string;
  manifest_sha256: string;
  previous_catalog_sha256: string;
  extractor_revision: string;
  catalog_schema: string;
  configuration_sha256: string;
  importer_id: string;
  source_active: boolean;
  state: VisualCatalogState;
  version: number;
  counts: {
    total: number;
    table_candidate: number;
    figure_image: number;
    formula_candidate: number;
    rectangular_tables: number;
    unresolved_tables: number;
    inline_table_references?: number;
  };
  review_history_counts: { accepted: number; rejected: number; needs_more: number };
  answer_evidence_eligible: false;
  published: false;
}
export interface VisualCatalogReview {
  id: string;
  previous_review_id: string | null;
  reviewer_id: string;
  decision: VisualReviewDecision;
  method: 'independent_human';
  checks: VisualContentChecks;
  evidence: string;
  payload_sha256: string;
  reviewed_at: string;
}
export interface VisualCatalogCandidateSummary {
  id: string;
  region_id: string;
  previous_region_id: string;
  physical_pdf_page: number;
  kind: 'table_candidate' | 'figure_image' | 'formula_candidate';
  candidate_status: 'needs_structure_review' | 'needs_visual_review' | 'needs_formula_review';
  payload_sha256: string;
  bbox_points: number[];
  answer_evidence_eligible: false;
}
export interface VisualCatalogCandidate {
  catalog_id: string;
  region_id: string;
  previous_region_id: string;
  payload_sha256: string;
  candidate_status: 'needs_structure_review' | 'needs_visual_review' | 'needs_formula_review';
  answer_evidence_eligible: false;
  latest_review: VisualCatalogReview | null;
  raw_payload: {
    region_id: string;
    book: string;
    source_sha256: string;
    physical_pdf_page: number;
    kind: string;
    bbox_points: number[];
    native_text: string;
    status: string;
    details: Record<string, unknown>;
    [key: string]: unknown;
  };
}
export interface VisualCatalogPage<T> { items: T[]; next_offset: number | null }
export interface VisualCatalogImport { items: (VisualCatalogVersion & { added: number })[]; added_candidates: number }
export interface VisualCatalogReviewReceipt { review_id: string; catalog_version: VisualCatalogVersion }

export const VISUAL_CATALOG_PATH = '/admin/source-quality/catalog-versions';
export const catalogPath = (id: string) => `${VISUAL_CATALOG_PATH}/${encodeURIComponent(id)}`;
export const catalogCandidatePath = (id: string, region: string) => `${catalogPath(id)}/candidates/${encodeURIComponent(region)}`;
export function validVisualBundleName(value: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$/.test(value) && !value.includes('..');
}
export function validManifestHash(value: string): boolean { return /^[0-9a-f]{64}$/.test(value); }
export const visualCatalogApi = {
  list: (offset = 0) => request<VisualCatalogPage<VisualCatalogVersion>>(`${VISUAL_CATALOG_PATH}?offset=${offset}&limit=30`),
  detail: (id: string) => request<VisualCatalogVersion>(catalogPath(id)),
  candidates: (id: string, offset = 0) => request<VisualCatalogPage<VisualCatalogCandidateSummary>>(`${catalogPath(id)}/candidates?offset=${offset}&limit=30`),
  candidate: (id: string, region: string) => request<VisualCatalogCandidate>(catalogCandidatePath(id, region)),
  import: (bundleName: string, manifestHash: string) => {
    if (!validVisualBundleName(bundleName) || !validManifestHash(manifestHash)) {
      throw new ApiError('VALIDATION_FAILED', 'Enter a prepared bundle name and its 64-character SHA-256.');
    }
    return post<VisualCatalogImport>(`${VISUAL_CATALOG_PATH}/imports`, { bundle_name: bundleName, expected_manifest_sha256: manifestHash });
  },
  transition: (catalog: VisualCatalogVersion, state: Exclude<VisualCatalogState, 'staged'>) => post<VisualCatalogVersion>(`${catalogPath(catalog.id)}/state`, { expected_version: catalog.version, state }),
  review: (catalogId: string, candidate: VisualCatalogCandidate, decision: VisualReviewDecision, checks: VisualContentChecks, evidence: string) => post<VisualCatalogReviewReceipt>(`${catalogCandidatePath(catalogId, candidate.region_id)}/reviews`, { previous_review_id: candidate.latest_review?.id || null, decision, checks, evidence }),
};
