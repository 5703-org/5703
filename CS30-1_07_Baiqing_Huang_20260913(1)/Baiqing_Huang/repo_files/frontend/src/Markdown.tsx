import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { useMemo, useRef } from 'react';
import type { Components } from 'react-markdown';
import type { Evidence } from './types';

type Node = { type: string; value?: string; url?: string; children?: Node[] };
export function citationPlugin(validIds: string[]) {
  return () => (tree: Node) => {
    const visit = (node: Node) => {
      if (!node.children || node.type === 'link' || node.type === 'code' || node.type === 'inlineCode') return;
      node.children = node.children.flatMap(child => {
        if (child.type !== 'text' || !child.value) { visit(child); return [child]; }
        const pattern = /\[(ev_\d{3,})\]/g;
        const result: Node[] = []; let end = 0;
        for (const match of child.value.matchAll(pattern)) {
          if (!validIds.includes(match[1])) continue;
          if (match.index! > end) result.push({ type: 'text', value: child.value.slice(end, match.index) });
          result.push({ type: 'link', url: `#evidence-${match[1]}`, children: [{ type: 'text', value: `[${validIds.indexOf(match[1]) + 1}]` }] });
          end = match.index! + match[0].length;
        }
        if (!end) return [child];
        if (end < child.value.length) result.push({ type: 'text', value: child.value.slice(end) });
        return result;
      });
    }; visit(tree);
  };
}
export function SafeMarkdown({ text, evidence = [], citationIds, onEvidence }: { text: string; evidence?: Evidence[]; citationIds?: string[]; onEvidence?: (id: string) => void }) {
  const openEvidence = useRef(onEvidence); openEvidence.current = onEvidence;
  const ids = (citationIds || evidence.map(item => item.evidence_id)).join(',');
  const plugins = useMemo(() => [remarkGfm, remarkMath, citationPlugin(ids ? ids.split(',') : [])], [ids]);
  const components = useMemo<Components>(() => ({
    a: ({ href, children }) => href?.startsWith('#evidence-') ? (openEvidence.current && ids.split(',').includes(href.slice(10)) ? <button className="citation" aria-label={`Open source ${String(children).replace(/[\[\]]/g, '')}`} onClick={() => openEvidence.current?.(href.slice(10))}>{children}</button> : <span>{children}</span>) : <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>,
    table: ({ children }) => <div className="local-scroll" tabIndex={0} role="region" aria-label="Scrollable table"><table>{children}</table></div>,
    pre: ({ children }) => <pre tabIndex={0} aria-label="Scrollable code block">{children}</pre>,
    img: ({ alt }) => <span className="secondary">[Image: {alt || 'No description provided'}]</span>,
  }), [ids]);
  return <div className="prose"><Markdown skipHtml remarkPlugins={plugins} rehypePlugins={[[rehypeKatex, { trust: false, throwOnError: false }]]} components={components}>{text}</Markdown></div>;
}
