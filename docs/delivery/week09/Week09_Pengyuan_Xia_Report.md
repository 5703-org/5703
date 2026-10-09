# Week 9 Work Report

Pengyuan Xia | 550267474 | 26 September 2026

Learner preferences and independent presentation studies

## Scope and retained work

The personalisation workstream retains typed, editable learning memories with source attribution, revision, expiry and deletion. Current explicit instructions take priority, followed by applicable subject preferences and general profile settings. Memory admission and preview continue to use their existing typed rule workflow.

Original allocation: PER-01, PER-02, PER-03, PER-04, PER-05, PER-06, PER-07, PER-08, PER-09, CHAT-07.

## Week 9 changes

Week 9 adds a versioned semantic supplement for scopes that the existing rules cannot resolve. It uses the pinned real local E5 model on CPU and requires an explicit calibrated policy. Conditional preferences reread their owned source conversation before selection. Missing runtime resources produce a recorded fallback to the rule result.

The selection study freezes separate development and reserved knowledge groups and reports correct selections, false selections and omissions. A separate paired answer pilot uses the protected Week 8 generation implementation, identical questions and real textbook context to examine preference application without mixing in the new generation changes.

Selection traces remain inside the revocable memory boundary. Public diagnostics show status and counts. The semantic supplement stays disabled by default; its actual request decisions can be inspected when explicitly enabled.

## Verification and findings

The 64-case authored selection study used actual CPU E5 embeddings. In the reserved subset, semantic selection retained 14/16 applicable memories, omitted two and falsely selected two of sixteen inapplicable entries. Each application arm delivered 6/8 answers. Independent applicability and preference-compliance scores remain blank, and semantic selection stays optional.

## Current source and responsibility

The personal archive contains complete current files for this workstream, including retained changes since the Week 7 final release. The package manifest records file ownership and hashes. Codex performed the shared implementation and automated execution; the named member is accountable for reviewing, explaining and submitting this workstream.

Selected assigned source areas

personalisation/memory_v3.py

personalisation/memory_v2.py

personalisation/compiler.py

## Week 10 goals

- Collect independent applicability and answer-compliance scores from the prepared paired materials.

- Expand unrelated-topic and close-neighbor cases before recalibrating or enabling semantic selection.

- Extend complex preference conditions and align the preview with any validated semantic policy.

## Evidence

evidence/week09-generation/20260926/memory-summary.json
