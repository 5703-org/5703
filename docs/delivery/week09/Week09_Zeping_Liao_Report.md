# Week 9 Work Report

Zeping Liao | 540626434 | 26 September 2026

Accounts, model settings, durable chat, diagnostics and operations

## Scope and retained work

The backend workstream retains accounts, managed model settings, durable jobs, conversations, teaching tasks and administrator diagnostics. Week 8 bound learner replies to pending tutor questions and task revisions, with cancellation and source-publication checks. Existing database records and historical request versions remain intact.

Original allocation: BE-01, BE-02, BE-03, BE-04, BE-05, BE-06, BE-07, BE-08, BE-09, BE-10, BE-11, BE-12, BE-13, BE-14, BE-15, BE-16, BE-17, CHAT-02, CHAT-03, CHAT-08.

## Week 9 changes

New submissions freeze the Week 9 generation, teaching and memory policy identities with their current managed model settings. Task input, current step and pending-question versions remain fixed through execution. Existing frozen commands continue through their recorded compatibility paths.

The request pipeline records plan preparation, context coverage and the single supplementary-retrieval pass. Administrator projections expose bounded counts and versioned decisions. Private memory text and source conversations stay within the owner-controlled memory store.

An optional semantic-memory policy file is validated before its fields enter a request. Unreadable or invalid configuration becomes an explicit optional-memory preparation status. The application preserves the primary question flow and its recorded failure conditions.

## Verification and findings

The six-step real HTTP journey delivered four responses. Both managed-provider role probes passed, and the first hint and bound learner attempt completed. The comparison hit a context limit and the explicit full answer failed semantic checking; both records remain available. Learner access to administrator diagnostics was denied and saved answers reloaded consistently.

After the experiments, we added versioned, lossless checker-input encoding for new requests. It selects the smallest complete representation while preserving source text, actual citation bindings, support checks and the configured model window. In the DNA/RNA replay, checker input fell from 13,151 to 12,094 reserved tokens, within the 12,288-token allowance. Four scheduled workflow replays produced four responses using 10 calls and 74,821 tokens. The full-answer action completed, with the osmosis response explicitly identifying evidence gaps beyond its core definition. These are operational results; independent human quality ratings remain pending. The original experiments and their exact executable source archive remain preserved separately from this release successor.

## Current source and responsibility

The personal archive contains complete current files for this workstream, including retained changes since the Week 7 final release. The package manifest records file ownership and hashes. Codex performed the shared implementation and automated execution; the named member is accountable for reviewing, explaining and submitting this workstream.

Selected assigned source areas

backend/app/modules/answering/service.py

backend/app/modules/learning_state/memory_v3.py

backend/app/modules/learning_state/memory.py

backend/app/core/config.py

## Week 10 goals

- Exercise simultaneous retries, task changes and source or memory revocation under realistic request load.

- Verify external database installation, backup and recovery on a separate Windows computer.

- Review administrator traces with the team and refine failure explanations from actual operating incidents.

## Evidence

evidence/week09-generation/20260926/http-final-01.json

evidence/week09-generation/20260926/http-successor-01.json
