# Week10 configuration guide

Use the complete package's new local installation. Python Settings load local configuration; the public Windows launcher clears inherited application/provider variables, validates the explicit target ports and generates fresh installation secrets. .env.example is an example, not a credential-bearing runtime file. Never reuse preserved development .env/database files for these checks.

The startup provider is MODEL_MODE=mock / LLM_PROVIDER=mock / authored-extractive-v1. It exercises product persistence and visible citations; it is not a real scientific evaluator. Model administration lets a user save, test and explicitly activate a real provider. Enter its credential privately through that interface; no API key is included in this release.

The current ordinary supported configuration retains anchored_reference_v22, relevance/cache gates and typed_joint_v5 with source relation off unless explicitly configured. Worker startup prewarming defaults false; V23 query preparation is opt-in. chat_qualification_source_transport, its session/question binding and checker schema/output opt-ins are not enabled by packaging. Activation of a provider or opt-in requires its separate documented acceptance scope.

Default complete-package retrieval uses the bundled corpus, E5 assets and configured hybrid/MiniLM resources. Device cpu avoids an optional GPU dependency environment. The startup wrapper materializes pinned local model caches from resources/model-assets; tiktoken files are already present at artifacts/tiktoken. Visual catalogs retain their candidate/unapproved state.

Keep the generated API/worker settings and model encryption-key file consistent within this fresh installation. Keep secrets, private backups, real histories and database files outside any exported source archive. Stop/restart only owned services identified by artifacts/runtime/processes.json. Dependencies and external account credentials are intentionally not shipped.
