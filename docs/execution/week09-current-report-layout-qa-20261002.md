# Current Week 9 report layout verification

All nine current English DOCX reports passed actual inspection of their 65 rendered pages. The [current verification receipt](../../evidence/week09-continuation/20261001/report-qa-gate05-current-65-pages-20261002.json) binds the exact DOCX, PDF and individual page hashes. Each original page image was viewed, including odd and even pages, complete project-name footers, page numbers, tables, text and evidence lists. No clipping, overlap or missing glyphs were observed.

| Report | Inspected pages |
| --- | --- |
| Overall | 14 |
| Xianshu Zhang | 7 |
| Hongle Yang | 5 |
| Chengzhou Liu | 6 |
| Sijin Lu | 8 |
| Pengyuan Xia | 5 |
| Zeping Liao | 6 |
| Baiqing Huang | 5 |
| Chong Zhang | 9 |
| Total | 65 |

Fonts, styles, geometry, headers, footers and retained historical body text remain unchanged. Current Markdown counterparts match the updated report narrative. Native Word opened the sources read-only in a proven new instance, exported PDFs and closed that instance. The packaged documents renderer rasterized those PDFs. All eighteen report files remained hash exact during rendering. The first attempt stopped before any report export because the window handle was read from the wrong Word object; its failure receipt is retained. The corrected attempt generated all nine reports without stopping shared Word processes.

This is layout and file-identity verification by Codex agents. Independent answer correctness, citation support, teaching usefulness and learning effects require their own labels; human ratings remain zero. The earlier 63-page report checkpoint retains its previous document identities. Complete and personal archives use the current nine DOCX hashes and receive separate archive verification.
