#!/usr/bin/env bash
# ==============================================================================
# ShelterWise — BigQuery Connection, Vector Table & Views Automated Setup
# Member 1 (Sarav) - Data Lane
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "${PROJECT_ID}" ]]; then
  echo "Error: PROJECT_ID not found. Run 'gcloud config set project <PROJECT_ID>'." >&2
  exit 1
fi

DATASET="${BQ_DATASET:-a4i_housing}"
LOCATION="${BQ_LOCATION:-US}"
CONNECTION_NAME="a4i-vertex"

echo "=== 1. Checking Vertex AI Connection ${LOCATION}.${CONNECTION_NAME} ==="
if ! bq show --connection --project_id="${PROJECT_ID}" --location="${LOCATION}" "${CONNECTION_NAME}" >/dev/null 2>&1; then
  echo "Creating connection ${CONNECTION_NAME} in ${LOCATION}..."
  bq mk --connection --location="${LOCATION}" --project_id="${PROJECT_ID}" \
    --connection_type=CLOUD_RESOURCE "${CONNECTION_NAME}"
else
  echo "Connection ${CONNECTION_NAME} already exists."
fi

echo "=== 2. Granting IAM Role roles/aiplatform.user to Connection Service Account ==="
SA="$(bq show --format=json --connection "${PROJECT_ID}.${LOCATION}.${CONNECTION_NAME}" \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["cloudResource"]["serviceAccountId"])')"
echo "Connection Service Account: ${SA}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user" \
  --condition=None >/dev/null

echo "=== 3. Executing sql/setup_vector_and_views.sql ==="
bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" < "${ROOT_DIR}/sql/setup_vector_and_views.sql"

echo "=== BigQuery Setup Complete! ==="
