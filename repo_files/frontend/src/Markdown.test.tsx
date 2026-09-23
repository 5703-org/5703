import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { SafeMarkdown } from './Markdown';
import type { Evidence } from './types';

afterEach(cleanup);
const evidence: Evidence = { evidence_id: 'ev_001', chunk_id: 'chunk-one', asset_id: 'asset-one', processing_id: 'processing-one', source_title: 'Authored textbook fixture', section: 'Energy', pages: [2], locator: 'page 2', text: 'Plants use light.', text_hash: 'hash-one', context_order: 0 };
describe('safe answer rendering', () => {
  it('opens repeated references for their own exact Unicode claim ranges', () => {
    const first = '😀 First claim. [ev_001]'; const second = 'Second claim. [ev_001]';
    const text = `${first}\n\n${second}`; const open = vi.fn();
    render(<SafeMarkdown text={text} citationIds={['ev_001']} claims={[
      { claim_id: 'claim-first', answer_field: 'answer_text', start: 0, end: Array.from(first).length, text: first },
      { claim_id: 'claim-second', answer_field: 'answer_text', start: Array.from(first).length + 2, end: Array.from(text).length, text: second },
    ]} onEvidence={open} />);
    const citations = screen.getAllByRole('button', { name: 'Open source 1' });
    fireEvent.click(citations[0]); fireEvent.click(citations[1]);
    expect(open.mock.calls).toEqual([['ev_001', 'claim-first'], ['ev_001', 'claim-second']]);
  });
  it('keeps invalid claim offsets coarse and never infers a claim from a crafted link', () => {
    const open = vi.fn();
    render(<SafeMarkdown text="Actual claim. [ev_001] [other](#evidence-ev_001)" citationIds={['ev_001']} claims={[
      { claim_id: 'wrong-claim', answer_field: 'answer_text', start: 0, end: 21, text: 'Different text.' },
    ]} onEvidence={open} />);
    screen.getAllByRole('button').forEach(button => fireEvent.click(button));
    expect(open.mock.calls).toEqual([['ev_001'], ['ev_001']]);
  });
  it('does not turn a crafted uncited source link into an evidence request', () => {
    const open = vi.fn();
    render(<SafeMarkdown text="[submitted only](#evidence-ev_002) [used](#evidence-ev_001)" citationIds={['ev_001']} onEvidence={open} />);
    expect(screen.getAllByRole('button')).toHaveLength(1);
    fireEvent.click(screen.getByText('submitted only'));
    expect(open).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Open source used' }));
    expect(open).toHaveBeenCalledExactlyOnceWith('ev_001');
  });
  it('opens only citations belonging to the current answer and keeps code literal', () => {
    const open = vi.fn();
    render(<SafeMarkdown text={'Plants use light. [ev_001] Unknown [ev_099]. `literal [ev_001]`'} evidence={[evidence]} onEvidence={open} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open source 1' }));
    expect(open).toHaveBeenCalledExactlyOnceWith('ev_001');
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(document.querySelector('code')?.textContent).toBe('literal [ev_001]');
    expect(document.body.textContent).toContain('[ev_099]');
  });
  it('does not execute model HTML or unsafe link protocols', () => {
    render(<SafeMarkdown text={'<script>window.bad=true</script>\n\n[unsafe](javascript:alert(1))\n\n<img src=x onerror="alert(1)">'} />);
    expect(document.querySelector('script')).toBeNull();
    expect(document.querySelector('img')).toBeNull();
    expect(document.querySelector('a')?.getAttribute('href') || '').not.toMatch(/^javascript:/i);
  });
  it('preserves all long text and gives tables and code their own scroll regions', () => {
    const long = 'long-content-'.repeat(300);
    render(<SafeMarkdown text={`${long}\n\n| Concept | Explanation |\n| --- | --- |\n| Energy | Photosynthesis |\n\n\`\`\`text\n${long}\n\`\`\``} />);
    expect(screen.getByRole('region', { name: 'Scrollable table' }).querySelectorAll('td')).toHaveLength(2);
    expect(screen.getByLabelText('Scrollable code block').textContent).toContain(long);
    expect(document.body.textContent).toContain(long);
  });
  it('keeps a citation trigger mounted and focused when a parent callback changes', () => {
    const { rerender } = render(<SafeMarkdown text="Plants use light. [ev_001]" evidence={[evidence]} onEvidence={() => {}} />);
    const trigger = screen.getByRole('button', { name: 'Open source 1' });
    trigger.focus();
    rerender(<SafeMarkdown text="Plants use light. [ev_001]" evidence={[evidence]} onEvidence={() => {}} />);
    expect(screen.getByRole('button', { name: 'Open source 1' })).toBe(trigger);
    expect(document.activeElement).toBe(trigger);
  });
  it('retains a resolvable source control when evidence metadata was withheld', () => {
    const open = vi.fn();
    render(<SafeMarkdown text="Original citation remains. [ev_001]" evidence={[]} citationIds={['ev_001']} onEvidence={open} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open source 1' }));
    expect(open).toHaveBeenCalledExactlyOnceWith('ev_001');
  });
});
