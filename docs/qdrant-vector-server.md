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

## Create your first collection in the Qdrant Cloud dashboard

The quickest option needs no secret or API key copied into a chat:

1. Open https://cloud.qdrant.io and select your **existing** medstudy-vector
   cluster (AWS Europe). Check that its status is HEALTHY.
2. Click **Cluster UI**, then **Collections** and **Create Collection**.
3. Enter collection name **medstudy_lessons_v1**.
4. For an ordinary single dense vector, choose **vector size 384** and
   **distance Cosine**. If an on-disk option is available, enable it.
5. Save/create and verify the new collection appears in Collections.

Do not create a second Qdrant Cloud cluster. The new collection will initially
contain zero vectors until we choose and run a multilingual embeddings model.

## Optional scripted creation (prepared, not yet deployed)

The tested script at scripts/qdrant_setup.py can also create/verify the
collection without deleting existing data. Add QDRANT_URL (HTTPS cluster
endpoint) and QDRANT_API_KEY (database key) through secure environment
variables on a trusted machine or in GitHub Actions repository secrets.

Important: the newly added manual GitHub Actions workflow lives only on
this feature branch. GitHub requires a workflow file on the default
branch before its manual "Run workflow" control can be used. We have
NOT enabled manual production Actions execution or altered the
production app. Use the dashboard instructions above for now.

Never paste QDRANT_API_KEY into a chat, public GitHub file, or client
JavaScript. If an old Qdrant key is no longer needed, revoke it in the
Qdrant Cloud API Keys screen after confirming the newer key works.

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
