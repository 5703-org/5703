import type { Answer, Evidence } from './types';

/** An empty citation list is authoritative, including refused responses. */
export function responseSources(answer: Answer) {
  const recorded = Array.isArray(answer.response?.citations);
  const values = recorded ? answer.response.citations : answer.evidence.map(item => item.evidence_id);
  return { ids: [...new Set(values.filter(value => typeof value === 'string' && value.length > 0))], recorded };
}

export function sourceLocator(evidence: Evidence) {
  const locator = evidence.locator || '';
  const section = evidence.section && !locator.toLowerCase().includes(evidence.section.toLowerCase()) ? evidence.section : '';
  const pages = evidence.pages.length && !/\bpages?\b/i.test(locator) ? `Page${evidence.pages.length > 1 ? 's' : ''} ${evidence.pages.join(', ')}` : '';
  return [section, locator, pages].filter(Boolean).join(' · ');
}
