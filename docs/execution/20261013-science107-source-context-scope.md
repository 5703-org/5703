# Science107: one generic source-context generation correction

Scope: E:/5703/learning-assistant only. New provider requests, credential reads and database connections: **0**. The three saved same-S01 answers from Native105 remain unchanged. This science change is recorded separately from Native106's Engine-bound prewarm correction.

## Evidence and the actual cause

The Native106 results JSON preserves each original answer and every actually submitted OpenStax passage. For102/104, Anatomy and Physiology2e ev_001 literally says catalysts increase the rate and force of collisions, are unchanged themselves, and describes activation energy in terms of breaking reactant bonds. For103, the same paragraph is ev_002. These phrases were **not invented by the generator**. It copied a teaching simplification into an unqualified mechanism/definition. The context already available to the generator supplies the needed distinctions:

- Biology2e / Concepts of Biology explain lowering the barrier to the transition state, substrate positioning and unchanged reactant/product free energies. Chemistry2e in102/104 additionally explains a different reaction mechanism with a lower-energy transition state.
- Anatomy and Physiology2e and Biology2e describe induced fit, temporary conformational adjustments and transient participation/binding. An overall unchanged catalyst is not a claim that every intermediate state remains unchanged.
- The general definition and a particular bond-breaking or collision illustration have different scopes. Preserve the actual subject: an enzyme-specific explanation does not automatically establish a statement about every catalyst.

Thus the three causes differ: **source teaching simplification** is directly present in the textbook; **generation scope broadening** presents that wording without reconciling the supplied detailed context; **checker limitation** lets selected-source fidelity pass without surfacing the broader contextual qualification. Every saved online checker assigns supported and requested-help completeness. That establishes the recorded source-based publication result, not calibrated scientific quality. A faithfully copied source simplification is not automatically a provenance failure or proof of a fabricated scientific claim. Human ratings remain null, and no new checker verdict is manufactured here.

## Exactly one production change

Appended one **CONTEXTUAL SCOPE AND CHANGE** paragraph to `generation/prompts/source_relation_generation_v2.txt`. It preserves the complete2475-byte original prefix and adds1086 bytes. The new rule requires source-grounded subject/condition preservation, distinguishes overall outcome from intermediate states, and separates a general definition from an illustrative route/motion/step. It retains compatible supported content, each claim's own contributing citations, and a specific conflict/limitation only when required knowledge really conflicts. It forbids an invented reconciliation, uncited background knowledge and blanket refusal.

No S01 scientific answer, entity or mechanism was added to the generic paragraph. No new extraction module or semantic classifier was created. The existing V2 system template already accompanies both initial generation and the current local claim-patch call, so one prompt edit reaches both. No repair eligibility, claim compiler, protected text, schema, source selection, checker prompt, budgets or publication gate changed. Default requests without SourceRelationV2 do not receive this paragraph. The prewarm helper, production cache and Native106 files were not modified.

The new prompt SHA256 is `783636de019da97e2b6b7ee7995c2bf41faf1e6a5b69ca6f2519ee71b757b95f`; its original prefix hash is `79f9933cc4a74cedab05dee07fef53c619f52657bef66c730374167c25a28597`. Existing checked.py remains ce58 and cache.py remains85706. Historical closed scopes cannot be replayed as a current-prompt experiment; any future live scope must rebind the new source pin.

## Small affected free verification

Added `tests/unit/test_source_context_scope107.py`, SHA256 `d838d4ffc9ed2813748e73c237750daad3568ff3bd06946788a7ea4192b64482`:

- Three adjacent authored science pairs: dynamic-equilibrium ongoing reactions versus unchanged overall concentration; one algal population under a stated condition versus an unconditional all-organisms statement; heat's general definition versus one conduction route.
- Existing sentence-local citation and source-unit gates retain each complete supported statement and block an authored partial/condition defect despite optimistic aggregate coverage. The authored negative verdicts preserve the existing requirement IDs; optimistic full coverage cannot discharge a source defect.
- Existing local claim patch receives the same generic policy, retains its authorized edit boundary and requires a fresh full check; an authored remaining condition failure still blocks publication.
- A default request does not adopt the V2 paragraph.

Final **installed Main** verification:43 passed in0.71s (34 existing SourceRelationV2 cases plus9 new controls), no failures/errors/skips; Ruff passed for the new test. Candidate verification also passed43 in0.76s before installation. The tests use explicitly authored scripted judgments and synthetic source text, not a model, gold labels or a database. They prove policy wiring, citation preservation and unchanged negative/recheck gates; they do **not** prove the model will detect scope errors or produce scientifically better wording. The readback preserves25 frozen files during the two-file installation.

## Remaining real verification

No historical answer is replaced and no native quality or speed gain is claimed. A future separately scoped S01 generation/full-check page run must determine whether the model now avoids the three simplifications while answering all requested facts with actual own citations. Keep the corrected Engine prewarm, model, corpus, retrieval and checker constant when assessing this prompt version; record startup and complete DOM separately. One sample can demonstrate the corrected behavior, not establish a causal improvement or p95. A controlled old/new prompt comparison would require additional separately admitted requests; the original six-slot batch stays closed. The checker can still miss genuine source or condition gaps, and local repair was not triggered in the old three answers. Default activation and whole-project qualification remain unchanged.

Source-to-target: one reviewed prompt append and one new authored test installed by exact pins/fstat/prefix/fsync checks; public report/results/evidence added separately. All old answers, inputs, experiment failures, earlier deliveries, protected staging and other projects remain preserved. No API, upload, push, deploy, dependency installation or course submission occurred; project_complete=false.
