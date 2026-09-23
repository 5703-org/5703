import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { SourceSegments } from './SourceSegments';

afterEach(cleanup);

it('preserves exact approved Unicode text and separate highlights without interpreting HTML', () => {
  const segments = [
    { text: 'Context α😀\n', highlight: false },
    { text: '<img src=x onerror=alert(1)>', highlight: true, fragment_ids: ['fragment-a'] },
    { text: '\nH₂O = water\n', highlight: false },
    { text: 'Second supported span.', highlight: true, fragment_ids: ['fragment-b'] },
  ];
  render(<SourceSegments segments={segments} />);
  expect(screen.getByLabelText('Source passage').textContent).toBe(segments.map(item => item.text).join(''));
  expect(document.querySelectorAll('mark')).toHaveLength(2);
  expect(document.querySelector('img')).toBeNull();
  expect(document.querySelector('script')).toBeNull();
});

it('removes the prior passage completely when a different approved projection arrives', () => {
  const { rerender } = render(<SourceSegments segments={[{ text: 'Approved first preview', highlight: true }]} />);
  rerender(<SourceSegments segments={[{ text: 'Approved second preview', highlight: false }]} />);
  expect(document.body.textContent).toBe('Approved second preview');
  expect(document.querySelector('mark')).toBeNull();
  expect(document.body.innerHTML).not.toContain('Approved first preview');
});
