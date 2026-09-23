import { Fragment } from 'react';
import type { TextSegment } from './learning-types';

/** Render only server-approved text. Source HTML and offsets never become DOM markup. */
export function SourceSegments({ segments }: { segments: TextSegment[] }) {
  return <div className="source-passage" aria-label="Source passage">{segments.map((segment, index) => segment.highlight === true
    ? <mark key={index} className="source-highlight">{segment.text}</mark>
    : <Fragment key={index}>{segment.text}</Fragment>)}</div>;
}
