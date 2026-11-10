# MedStudy AI: Qdrant Cloud vector database

## Existing cluster: reuse it

The Qdrant Cloud Free cluster **medstudy-vector** was previously created in
AWS Europe (eu-west-2) and was last seen HEALTHY. Reuse this cluster; no
additional account or second paid cluster is necessary.

The setup script in this branch prepares an empty vector collection:

- Collection name: **medstudy_lessons_v1**
- Vector dimensions: **384**
- Similarity metric: **Cosine**
- Vector storage: on disk
- Intended contents: public/approved curriculum passages only
- NEVER store student IDs, contact details, clinical records, passwords,
  access tokens, test history or private chats in this collection.

The size 384 was selected as an inexpensive prototype vector dimension.
A future embedding model must generate exactly 384-dimensional vectors.
We have not yet selected or evaluated the embedding model for Uzbek teaching
content. Creating an empty collection does not produce semantic search.

## Create the collection through GitHub Actions

1. Open https://cloud.qdrant.io and select the **existing** medstudy-vector
   cluster. Check that it is HEALTHY (not suspended).
2. Copy the HTTPS **Cluster Endpoint** from its details page (not the Qdrant
   console page). In your GitHub repository:
   Settings > Secrets and variables > Actions > New repository secret.
   Add **QDRANT_URL**, containing the endpoint, including :6333 if supplied.
3. In Qdrant Cloud, open the cluster's Database API Keys. Use an active
   key with manage/write permission; if the old key is uncertain, create
   a fresh one. Store it as GitHub Actions secret **QDRANT_API_KEY**.
   Never paste any key into ChatGPT, a public link, a README or the Mini App.
   Revoke any unused or exposed old keys after confirming the new key works.
4. GitHub > Actions > **Qdrant Cloud collection setup for MedStudy AI**
   > Run workflow. Choose branch **feature/qdrant-vector-setup-20261110**
   and operation **status**. You should see exists: false if empty.
5. Repeat Run workflow with operation **create**. This action is
   idempotent: it creates the collection only if it is missing. It never
   deletes other collections, resets settings, or uploads student content.
6. Go to Qdrant Cloud > Cluster UI > Collections and verify
   **medstudy_lessons_v1**, vector size 384, similarity Cosine.

GitHub Actions secrets remain encrypted in GitHub, but who can trigger an
Actions workflow and which repository branches may access secrets should be
limited to trusted collaborators.

## Next stage after the empty collection exists

1. Pick and test a multilingual embedding model for Uzbek, Russian and
   English materials. It must output exactly 384 dimensions.
2. Break the 81 lessons into source-linked text passages and assign
   stable identifiers and metadata (subject, lesson, section, version).
3. Generate embeddings offline or in trusted backend processing and upload
   only approved nonpersonal educational content.
4. Add semantic search to the FastAPI backend, with a fallback to local
   lesson search. Authenticate user requests on the backend, not in Qdrant.
5. Evaluate accuracy and repeatability before using Qdrant for AI Ustoz.
   A vector database retrieves context; it does NOT generate tutoring answers.

## Important free plan caveats

Qdrant Cloud Free provides approximately 1 GB RAM, 0.5 vCPU and 4 GB disk.
It is a single-node prototype service and does not include an uptime SLA.
Unused free clusters can suspend after 7 days and be deleted after 4
weeks if not reactivated. Keep original learning material and an indexing
script so the collection can be rebuilt.

Qdrant is a **separate vector database**. It does not host FastAPI, Telegram
webhooks, the Mini App, or the SQLite account and quiz history. Do not
disconnect Railway expecting Qdrant to take over the application.

Official docs:
- https://qdrant.tech/documentation/cloud/create-cluster/
- https://qdrant.tech/documentation/cloud/cluster-access/
- https://qdrant.tech/documentation/cloud/authentication/
- https://qdrant.tech/documentation/manage-data/collections/
