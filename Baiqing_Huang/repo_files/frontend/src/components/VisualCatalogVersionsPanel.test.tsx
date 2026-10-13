import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ApiError, post, request } from '../api';
import { OriginalPageImage } from '../OriginalPage';
import { VisualCatalogVersionsPanel } from './VisualCatalogVersionsPanel';
import { VISUAL_CATALOG_PATH, catalogCandidatePath, catalogPath, visualCatalogApi, type VisualCatalogCandidate, type VisualCatalogCandidateSummary, type VisualCatalogVersion } from '../visual-catalog-api';

vi.mock('../api', async original => ({ ...await original<typeof import('../api')>(), request: vi.fn(), post: vi.fn() }));
vi.mock('../OriginalPage', () => ({ OriginalPageImage: vi.fn(() => <div>Source-page component fixture</div>) }));

const checks = { source_page_match: true, geometry_correct: true, native_text_correct: true, reading_order_correct: true, content_correct: true, notation_units_correct: true };
const catalog: VisualCatalogVersion = {
  id: 'catalog-one', book: 'chemistry', document_id: 'document-one', document_title: 'Chemistry textbook',
  document_version_id: 'source-version', source_sha256: '1'.repeat(64), catalog_sha256: '2'.repeat(64),
  manifest_sha256: '3'.repeat(64), previous_catalog_sha256: '4'.repeat(64), extractor_revision: 'parser-v3',
  catalog_schema: 'visual-catalog-v3', configuration_sha256: '5'.repeat(64), importer_id: 'importing-admin',
  source_active: true, state: 'under_review', version: 7,
  counts: { total: 8, figure_image: 2, table_candidate: 3, formula_candidate: 3, rectangular_tables: 1, unresolved_tables: 2 },
  review_history_counts: { accepted: 1, rejected: 2, needs_more: 4 }, answer_evidence_eligible: false, published: false,
};
const summary: VisualCatalogCandidateSummary = {
  id: 'candidate-one', region_id: '6'.repeat(64), previous_region_id: '7'.repeat(64), physical_pdf_page: 9,
  kind: 'table_candidate', candidate_status: 'needs_structure_review', payload_sha256: '8'.repeat(64),
  bbox_points: [10, 20, 80, 100], answer_evidence_eligible: false,
};
const candidate: VisualCatalogCandidate = {
  catalog_id: catalog.id, region_id: summary.region_id, previous_region_id: summary.previous_region_id,
  payload_sha256: summary.payload_sha256, candidate_status: summary.candidate_status, answer_evidence_eligible: false,
  raw_payload: { region_id: summary.region_id, book: 'chemistry', source_sha256: catalog.source_sha256,
    physical_pdf_page: 9, kind: 'table_candidate', bbox_points: summary.bbox_points,
    native_text: '<script>unsafe()</script> Pressure (kPa) | Temperature (°C)', status: 'needs_structure_review',
    details: { cells: [['Pressure (kPa)', 'Temperature (°C)'], ['−2.5', '3']], rows: 2, columns: 2 } },
  latest_review: { id: 'latest-review', previous_review_id: null, reviewer_id: 'prior-admin', decision: 'needs_more',
    method: 'independent_human', checks, evidence: 'Authored prior-review fixture.', payload_sha256: summary.payload_sha256, reviewed_at: '' },
};

function mockRecords(version = catalog, detail = candidate, userId = 'reviewing-admin') {
  vi.mocked(request).mockImplementation(async route => {
    if (route === '/users/me') return { id: userId };
    if (route === `${VISUAL_CATALOG_PATH}?offset=0&limit=30`) return { items: [version], next_offset: null };
    if (route === catalogPath(version.id)) return version;
    if (route === `${catalogPath(version.id)}/candidates?offset=0&limit=30`) return { items: [summary], next_offset: null };
    if (route === catalogCandidatePath(version.id, summary.region_id)) return detail;
    throw new Error(`Unexpected mocked route: ${route}`);
  });
}
async function openCatalog() {
  render(<VisualCatalogVersionsPanel />);
  fireEvent.click(screen.getByRole('button', { name: 'Visual catalog versions' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Inspect catalog version' }));
  const dialog = await screen.findByRole('dialog', { name: 'Visual catalog version' });
  await within(dialog).findByRole('button', { name: 'Inspect candidate' });
  return dialog;
}
async function openCandidate() {
  const dialog = await openCatalog(); fireEvent.click(within(dialog).getByRole('button', { name: 'Inspect candidate' }));
  await within(dialog).findByLabelText('Content review evidence'); return dialog;
}

beforeEach(() => {
  vi.resetAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(() => cleanup());

it('loads only when expanded and keeps catalog activity separate from retrieval eligibility', async () => {
  mockRecords({ ...catalog, state: 'active' }); render(<VisualCatalogVersionsPanel />);
  expect(request).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Visual catalog versions' }));
  await screen.findByText('Chemistry textbook');
  expect(screen.getByText('Active')).toBeTruthy();
  expect(screen.getByText('Answer evidence: excluded')).toBeTruthy();
  expect(screen.getByText(/Review history: 1 accepted · 2 rejected · 4 needing further review/)).toBeTruthy();
  expect(OriginalPageImage).not.toHaveBeenCalled(); expect(post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Visual catalog versions' }));
  expect(screen.queryByText('Chemistry textbook')).toBeNull();
});

it('imports only a safe staging bundle basename and the pinned manifest hash', async () => {
  mockRecords(); vi.mocked(post).mockResolvedValue({ items: [{ ...catalog, added: 8 }], added_candidates: 8 });
  render(<VisualCatalogVersionsPanel />); fireEvent.click(screen.getByRole('button', { name: 'Visual catalog versions' }));
  fireEvent.click(screen.getByRole('button', { name: 'Import prepared bundle' }));
  const dialog = screen.getByRole('dialog', { name: 'Import visual catalog bundle' });
  fireEvent.change(within(dialog).getByLabelText('Manifest SHA-256'), { target: { value: 'a'.repeat(64) } });
  for (const unsafe of ['../bundle', 'C:\\private\\bundle', '/tmp/bundle', 'two..dots']) {
    fireEvent.change(within(dialog).getByLabelText('Bundle name'), { target: { value: unsafe } });
    expect((within(dialog).getByRole('button', { name: 'Import bundle' }) as HTMLButtonElement).disabled).toBe(true);
  }
  expect(post).not.toHaveBeenCalled();
  fireEvent.change(within(dialog).getByLabelText('Bundle name'), { target: { value: 'prepared-visual-v3' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Import bundle' }));
  await screen.findByText('Prepared bundle imported with 8 new candidates.');
  expect(post).toHaveBeenCalledExactlyOnceWith(`${VISUAL_CATALOG_PATH}/imports`, { bundle_name: 'prepared-visual-v3', expected_manifest_sha256: 'a'.repeat(64) });
});

it('rejects unsafe bundle paths in the adapter before transport', () => {
  expect(() => visualCatalogApi.import('../source', 'a'.repeat(64))).toThrow(ApiError);
  expect(() => visualCatalogApi.import('prepared', 'not-a-hash')).toThrow(ApiError);
  expect(post).not.toHaveBeenCalled();
});

it('binds a state transition to the fetched catalog version and blocks stale retry until reload', async () => {
  mockRecords(); vi.mocked(post).mockRejectedValue(new ApiError('VERSION_CONFLICT', 'The catalog version changed.', 409));
  const dialog = await openCatalog();
  fireEvent.click(within(dialog).getByRole('button', { name: 'Activate reviewed catalog' }));
  await within(dialog).findByText('The catalog version changed.');
  expect(post).toHaveBeenCalledExactlyOnceWith(`${catalogPath(catalog.id)}/state`, { expected_version: 7, state: 'active' });
  expect((within(dialog).getByRole('button', { name: 'Activate reviewed catalog' }) as HTMLButtonElement).disabled).toBe(true);
  expect(within(dialog).queryByText('Catalog state updated. Answer evidence remains excluded.')).toBeNull();
});

it('renders exact candidate text safely and requires every type-specific check for acceptance', async () => {
  mockRecords(); vi.mocked(post).mockResolvedValue({ review_id: 'new-review', catalog_version: catalog });
  const dialog = await openCandidate(); expect(document.querySelector('script')).toBeNull();
  expect(within(dialog).getByText(candidate.raw_payload.native_text)).toBeTruthy();
  expect(within(dialog).getByLabelText('Rows, columns and cell relationships match the original')).toBeTruthy();
  expect(OriginalPageImage).not.toHaveBeenCalled();
  fireEvent.change(within(dialog).getByLabelText('Content review decision'), { target: { value: 'accepted' } });
  fireEvent.change(within(dialog).getByLabelText('Content review evidence'), { target: { value: 'I matched the grid, headings, signs and units to the original source.' } });
  expect((within(dialog).getByRole('button', { name: 'Save content review' }) as HTMLButtonElement).disabled).toBe(true);
  expect(within(dialog).getAllByRole('checkbox')).toHaveLength(6);
  for (const checkbox of within(dialog).getAllByRole('checkbox')) fireEvent.click(checkbox);
  fireEvent.click(within(dialog).getByRole('button', { name: 'Save content review' }));
  await within(dialog).findByText('Source content review saved. Answer evidence remains excluded.');
  expect(post).toHaveBeenCalledExactlyOnceWith(`${catalogCandidatePath(catalog.id, candidate.region_id)}/reviews`, { previous_review_id: 'latest-review', decision: 'accepted', checks, evidence: 'I matched the grid, headings, signs and units to the original source.' });
});

it('keeps rejected reviews honest without requiring false positive checks', async () => {
  mockRecords(); vi.mocked(post).mockResolvedValue({ review_id: 'new-review', catalog_version: catalog });
  const dialog = await openCandidate();
  fireEvent.change(within(dialog).getByLabelText('Content review decision'), { target: { value: 'rejected' } });
  fireEvent.change(within(dialog).getByLabelText('Content review evidence'), { target: { value: 'The extracted reading order loses the row labels.' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Save content review' }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({ decision: 'rejected', previous_review_id: 'latest-review', checks: { content_correct: false, notation_units_correct: false } });
});

it('prevents the importer from signing their own independent content review', async () => {
  mockRecords(catalog, candidate, catalog.importer_id); const dialog = await openCandidate();
  expect(within(dialog).getByText('This catalog requires a content review by another administrator.')).toBeTruthy();
  for (const checkbox of within(dialog).getAllByRole('checkbox')) expect((checkbox as HTMLInputElement).disabled).toBe(true);
  expect((within(dialog).getByRole('button', { name: 'Save content review' }) as HTMLButtonElement).disabled).toBe(true);
  expect(post).not.toHaveBeenCalled();
});

it('loads the historical page component only after an explicit click with the immutable source binding', async () => {
  mockRecords(); const dialog = await openCandidate(); expect(OriginalPageImage).not.toHaveBeenCalled();
  fireEvent.click(within(dialog).getByRole('button', { name: 'View original source page' }));
  expect(vi.mocked(OriginalPageImage).mock.calls[0][0]).toMatchObject({ documentId: catalog.document_id, regionId: candidate.previous_region_id, sourceHash: catalog.source_sha256, page: 9, bounds: candidate.raw_payload.bbox_points });
});

it('shows a review conflict without a success notice and requires a fresh candidate before retry', async () => {
  mockRecords(); vi.mocked(post).mockRejectedValue(new ApiError('CONFLICT', 'The previous review changed.', 409));
  const dialog = await openCandidate();
  fireEvent.change(within(dialog).getByLabelText('Content review evidence'), { target: { value: 'A conditional table label needs further inspection.' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Save content review' }));
  await within(dialog).findByText('The previous review changed.');
  expect((within(dialog).getByRole('button', { name: 'Save content review' }) as HTMLButtonElement).disabled).toBe(true);
  expect(within(dialog).queryByText('Content review saved. Answer evidence remains excluded.')).toBeNull();
});

it('keeps a withdrawn catalog terminal in the frontend', async () => {
  mockRecords({ ...catalog, state: 'withdrawn' }); const dialog = await openCatalog();
  expect(within(dialog).queryByRole('button', { name: 'Activate reviewed catalog' })).toBeNull();
  expect(within(dialog).queryByRole('button', { name: 'Begin review' })).toBeNull();
  expect(within(dialog).queryByRole('button', { name: 'Withdraw catalog' })).toBeNull();
});

it.each([
  ['formula_candidate', 'The formula and symbol relationships match the original'],
  ['figure_image', 'Figure labels and caption relationships match the original'],
])('uses the six content checks for %s', async (kind, label) => {
  mockRecords(catalog, { ...candidate, raw_payload: { ...candidate.raw_payload, kind } });
  const dialog = await openCandidate();
  expect(within(dialog).getByLabelText(label)).toBeTruthy();
  expect(within(dialog).getAllByRole('checkbox')).toHaveLength(6);
  expect(within(dialog).getByLabelText('Signs, notation and units match the original')).toBeTruthy();
});

it('prevents review and source-page loading when the source is unavailable', async () => {
  mockRecords({ ...catalog, source_active: false }); const dialog = await openCandidate();
  expect(within(dialog).getByText('The source is unavailable for content review.')).toBeTruthy();
  expect((within(dialog).getByRole('button', { name: 'View original source page' }) as HTMLButtonElement).disabled).toBe(true);
  expect((within(dialog).getByRole('button', { name: 'Save content review' }) as HTMLButtonElement).disabled).toBe(true);
  expect(OriginalPageImage).not.toHaveBeenCalled(); expect(post).not.toHaveBeenCalled();
});

it('refreshes the prior-review CAS binding before a retry after conflict', async () => {
  mockRecords(); vi.mocked(post).mockRejectedValueOnce(new ApiError('CONFLICT', 'The previous review changed.', 409)).mockResolvedValue({ review_id: 'new-review', catalog_version: catalog });
  const dialog = await openCandidate();
  fireEvent.change(within(dialog).getByLabelText('Content review evidence'), { target: { value: 'The table still needs a source-page inspection.' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Save content review' }));
  await within(dialog).findByText('The previous review changed.');
  mockRecords(catalog, { ...candidate, latest_review: { ...candidate.latest_review!, id: 'new-latest-review' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Reload saved candidate' }));
  await within(dialog).findByLabelText('Content review evidence');
  await waitFor(() => expect((within(dialog).getByRole('button', { name: 'Save content review' }) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(within(dialog).getByRole('button', { name: 'Save content review' }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
  expect(vi.mocked(post).mock.calls[1][1]).toMatchObject({ previous_review_id: 'new-latest-review', decision: 'needs_more' });
});

it('keeps the review dialog open until the pending save finishes', async () => {
  mockRecords(); let resolveSave!: (value: unknown) => void;
  vi.mocked(post).mockImplementation(() => new Promise(resolve => { resolveSave = resolve; }));
  const dialog = await openCandidate();
  fireEvent.change(within(dialog).getByLabelText('Content review evidence'), { target: { value: 'The table needs further independent inspection.' } });
  fireEvent.click(within(dialog).getByRole('button', { name: 'Save content review' }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  fireEvent.click(within(dialog).getByRole('button', { name: 'Close visual catalog version' }));
  expect(screen.getByRole('dialog', { name: 'Visual catalog version' })).toBeTruthy();
  resolveSave({ review_id: 'new-review', catalog_version: catalog });
  await within(dialog).findByText('Source content review saved. Answer evidence remains excluded.');
});

it('keeps a table reference and linked table on distinct immutable source pages', async () => {
  const target = { physical_pdf_page: 10, source_sha256: catalog.source_sha256, bbox_points: [20, 30, 400, 500], target_previous_region_id: '9'.repeat(64) };
  const reference = { ...candidate, raw_payload: { ...candidate.raw_payload, details: { record_role: 'inline_table_reference', rows: null, columns: null, cells: null, reference_target_locator: target } } };
  mockRecords(catalog, reference);
  const dialog = await openCandidate();
  expect(within(dialog).getByText('Table reference · PDF physical page 9')).toBeTruthy();
  expect((within(dialog).getByRole('option', { name: 'Accept reviewed extraction' }) as HTMLOptionElement).disabled).toBe(true);
  expect(OriginalPageImage).not.toHaveBeenCalled();
  fireEvent.click(within(dialog).getByRole('button', { name: 'View original source page' }));
  expect(vi.mocked(OriginalPageImage).mock.calls[0][0]).toMatchObject({ regionId: candidate.previous_region_id, sourceHash: catalog.source_sha256, page: 9, bounds: candidate.raw_payload.bbox_points });
  fireEvent.click(within(dialog).getByRole('button', { name: 'View linked target source page' }));
  expect(vi.mocked(OriginalPageImage).mock.calls.at(-1)?.[0]).toMatchObject({ regionId: target.target_previous_region_id, sourceHash: target.source_sha256, page: 10, bounds: target.bbox_points });
  expect(post).not.toHaveBeenCalled();
});

it('keeps source and target previews disabled for an unavailable reference source', async () => {
  const reference = { ...candidate, raw_payload: { ...candidate.raw_payload, details: { record_role: 'inline_table_reference', rows: null, columns: null, cells: null, reference_target_locator: { physical_pdf_page: 10, source_sha256: catalog.source_sha256, bbox_points: [20, 30, 400, 500], target_previous_region_id: '9'.repeat(64) } } } };
  mockRecords({ ...catalog, source_active: false }, reference);
  const dialog = await openCandidate();
  expect((within(dialog).getByRole('button', { name: 'View original source page' }) as HTMLButtonElement).disabled).toBe(true);
  expect((within(dialog).getByRole('button', { name: 'View linked target source page' }) as HTMLButtonElement).disabled).toBe(true);
  expect(OriginalPageImage).not.toHaveBeenCalled();
});
