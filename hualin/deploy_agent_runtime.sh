#!/usr/bin/env bash
# Deploy Hualin's ShelterWise version to Vertex AI Agent Runtime.
#
#   bash hualin/deploy_agent_runtime.sh          # first run creates, later runs update the same instance
#
# Separation from teammates: own display name, own service account, own BigQuery dataset.
set -euo pipefail

PROJECT="${PROJECT:-qwiklabs-gcp-04-99fa355171e1}"
REGION="${REGION:-us-central1}"        # Agent Runtime + Gemini region
PREFIX="${HUALIN_DEPLOY_PREFIX:-hualin-shelterwise}"
DISPLAY_NAME="${PREFIX}-navigator"
SA="${PREFIX}-agent@${PROJECT}.iam.gserviceaccount.com"

HERE="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$HERE/agent/shelterwise_hualin"
ID_FILE="$HERE/.agent_runtime_id"      # git-ignored; holds the reasoningEngines resource ID
ADK="$HERE/agent/.venv/bin/adk"

# Runtime env vars (no secrets). adk deploy reads .env from the agent folder; .env is git-ignored.
cat > "$AGENT_DIR/.env" <<EOF
GOOGLE_CLOUD_PROJECT=${PROJECT}
GOOGLE_CLOUD_LOCATION=${REGION}
GOOGLE_GENAI_USE_VERTEXAI=TRUE
HUALIN_GCP_PROJECT=${PROJECT}
SHELTERWISE_DATA=bigquery
SHELTERWISE_ENABLE_MCP=true
A4I_DATASET=a4i_housing
A4I_LOCATION=US
HUALIN_DATASET=hualin_shelterwise
HUALIN_DEPLOY_PREFIX=${PREFIX}
EOF

ARGS=(--project="$PROJECT" --region="$REGION" --display_name="$DISPLAY_NAME"
      --description="Hualin's ShelterWise housing-stability navigator (SF, Today at intake)"
      --service_account="$SA" --temp_folder="/tmp/${PREFIX}-deploy")
if [[ -s "$ID_FILE" ]]; then
  ARGS+=(--agent_engine_id="$(cat "$ID_FILE")")
  echo "Updating existing Agent Runtime instance $(cat "$ID_FILE")"
fi

"$ADK" deploy agent_engine "${ARGS[@]}" "$AGENT_DIR" 2>&1 | tee /tmp/${PREFIX}-deploy.log

ID="$(grep -oE 'reasoningEngines/[0-9]+' /tmp/${PREFIX}-deploy.log | tail -1 | cut -d/ -f2 || true)"
if [[ -n "$ID" ]]; then
  echo "$ID" > "$ID_FILE"
  echo "Agent Runtime resource: projects/${PROJECT}/locations/${REGION}/reasoningEngines/${ID}"
fi
