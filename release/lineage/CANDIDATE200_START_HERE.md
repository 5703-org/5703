# Candidate200 preparation — pending final source freeze

This directory is being assembled as one complete public learning-assistant candidate. Resource staging and public model hydration have passed their preparation checks. The application source overlay, final manifest and acceptance results are still pending. Keep this candidate separate from existing installations and retain earlier ZIPs and their evidence.

The bundle contains the four official OpenStax PDFs—Biology 2e, Chemistry 2e, Anatomy & Physiology 2e and Concepts of Biology—together with the manifest-bound corpus, source objects and vectors, visual catalogs, public E5/MiniLM model files, tokenizers and required sidecars. Preserve their package-relative paths and manifests. No provider keys, private encryption keys, learner history or database contents are shipped.

## Prerequisites and public-file verification

Use Windows with Python **3.13.x**, PowerShell, and a compatible Node release: **22.x from 22.12**, **24.x**, or **26.x and later**. Docker Desktop must be running with **Linux containers** and Docker Compose available for the normal managed PostgreSQL path.

Open PowerShell in this directory and first verify the prepared public files:

```powershell
.\start_candidate.ps1 -VerifyOnly
```

`-VerifyOnly` performs public-file verification. It does not install dependencies, start application or database services, or send model requests. A passing verification result establishes the checked file inventory, not installation or application acceptance.

## Install dependencies and start

This is a source-and-resource bundle, **not an offline dependency installer**. Locked Python and npm dependencies, and any missing Docker image, still require their configured registries. Python virtual environments and `node_modules` must be installed locally; do not copy them from another installation.

After the final source freeze is recorded, use free ports for a fresh installation. For example:

```powershell
.\start_candidate.ps1 -Install -Device cpu -DatabasePort 15592 -ApiPort 18092 -FrontendPort 15192
```

The normal entry installs locked dependencies, builds the frontend, prepares the installation-owned database and corpus, and starts the API, interactive worker, background worker and frontend. These are real installation and startup actions. Existing `.env` files are retained and validated; they are not silently replaced. Use configuration and ports belonging to this installation.

After successful readiness, open `http://127.0.0.1:15192`. Sign in as `admin@example.com` using the locally generated password file identified by startup, normally `.secrets/initial-admin-password.txt`, and change the password. Keep its contents private. Preserve this installation's persistent model-encryption key under `.secrets` once created.

A fresh installation starts with labelled mock answers. To use a real provider, enter its API key privately in **Administration > Models**, save the revision, and use the application's normal test and activation controls. Provider tests and real answers can make chargeable requests; run them only when you choose. Public-file verification and installation do not authorize or perform live-model acceptance.

## Candidate behavior and validation status

New ordinary-chat drafts start with **Check answer off**. Turn it on deliberately when an additional check is wanted. The intended fresh defaults include v3 citation handling and the new lossless CHECK transport; final default qualification remains conditional on Root's recorded acceptance. General-knowledge and calculation requests retain their supported routes and safe fallback behavior.

| Check | Preparation status |
| --- | --- |
| Public resource staging and model hydration | PASS for preparation scope |
| Complete source overlay, final freeze and package manifest | PENDING |
| New ten-cell live validation | PENDING |
| Normal-entry acceptance for the final candidate | PENDING |
| Clean-PC dependency downloads, full corpus import and startup | NOT ESTABLISHED |

Root will replace pending entries with the actual final results and their limits. Preparation checks do not establish teaching quality, semantic support, performance or complete-course acceptance.

## Recovery and preservation

If startup fails, inspect `artifacts/runtime/processes.json` and the corresponding role logs. A failed launch can leave owned processes running; identify this installation's recorded processes before stopping or restarting them. Do not delete or move a user's database, keys, history or older packages to recover this candidate. Retain earlier ZIPs, manifests and failed-run evidence. Keep any later source update separate from a deliberate runtime restart or database operation.
