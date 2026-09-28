#!/bin/bash
# analyze-screenshot.sh — Send a screenshot to a local LLM endpoint
# for analysis, using the config in config/screenshot-analyzer.yaml.
#
# Usage:
#   analyze-screenshot.sh [options] <screenshot.png>
#
# Options:
#   -c, --config <path>   Path to screenshot-analyzer.yaml
#                         (default: config/screenshot-analyzer.yaml)
#   -m, --message <text>  Custom user prompt (default: "Analyze this
#                         installation screenshot.")
#   -d, --debug           Dump raw API request and response to stderr
#   -h, --help            Show this help
#
# The script reads endpoint, model, system_prompt, and output_dir from
# the config, sends the screenshot as a base64 image to the LLM via
# OpenAI-compatible chat completions API, writes the analysis to
# output_dir/<basename>_analysis.md, and prints it to stdout.
# The API key is read from the env var named in config.api_key_env.
#
# Exit codes:
#   0 — Analysis completed successfully
#   1 — Missing dependency (curl, base64)
#   2 — Config or screenshot not found
#   3 — API request failed
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -Eeo pipefail

_AS_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_AS_BIN_DIR}/../lib/toolkit-common.sh"

# ── Resolve paths ──────────────────────────────────────────────────────────────
# TOOLKIT_ROOT and TOOLKIT_CONFIG_DIR come from lib/toolkit-common.sh.
DEFAULT_CONFIG="${TOOLKIT_CONFIG_DIR}/screenshot-analyzer.yaml"

# ── Defaults ────────────────────────────────────────────────────────────────────
CONFIG="$DEFAULT_CONFIG"
USER_PROMPT="Analyze this installation screenshot."
DEBUG=false

# ── Parse arguments ────────────────────────────────────────────────────────────
SCREENSHOT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--config) CONFIG="$2"; shift 2 ;;
        -m|--message) USER_PROMPT="$2"; shift 2 ;;
        -d|--debug)   DEBUG=true; shift ;;
        -h|--help)
            echo "Usage: $(basename "$0") [options] <screenshot.png>"
            echo ""
            echo "Options:"
            echo "  -c, --config <path>   Config file path"
            echo "  -m, --message <text>  Custom user prompt"
            echo "  -d, --debug           Dump raw API request/response"
            echo "  -h, --help            Show this help"
            exit 0
            ;;
        -*)
            echo "ERROR: Unknown option: $1" >&2
            echo "Usage: $(basename "$0") [options] <screenshot.png>" >&2
            exit 2
            ;;
        *)
            SCREENSHOT="$1"
            shift
            ;;
    esac
done

if [[ -z "$SCREENSHOT" ]]; then
    echo "ERROR: Screenshot path is required." >&2
    echo "Usage: $(basename "$0") [options] <screenshot.png>" >&2
    exit 2
fi

if [[ ! -f "$SCREENSHOT" ]]; then
    echo "ERROR: Screenshot not found: $SCREENSHOT" >&2
    exit 2
fi

if [[ ! -f "$CONFIG" ]]; then
    echo "ERROR: Config not found: $CONFIG" >&2
    exit 2
fi

# ── Check dependencies ──────────────────────────────────────────────────────────
for cmd in curl base64; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found. Install with: brew install $cmd" >&2
        exit 1
    fi
done

# ── Parse config ───────────────────────────────────────────────────────────────
# One key per call, read with AutoPkg's Python and PyYAML (no yq; KI-21).
config_value() {
    tk_python -c 'import sys, yaml
data = yaml.safe_load(open(sys.argv[1])) or {}
value = data.get(sys.argv[2]) if isinstance(data, dict) else None
print("" if value is None else value)' "$CONFIG" "$1"
}
ENDPOINT="$(config_value endpoint)"
MODEL="$(config_value model)"
API_KEY_ENV="$(config_value api_key_env)"
SYSTEM_PROMPT="$(config_value system_prompt)"
OUTPUT_DIR="$(config_value output_dir)"

# Resolve output_dir: if relative, make it relative to toolkit root
if [[ -n "$OUTPUT_DIR" ]]; then
    if [[ "$OUTPUT_DIR" != /* ]]; then
        OUTPUT_DIR="${TOOLKIT_ROOT}/${OUTPUT_DIR}"
    fi
else
    # Fallback: alongside the screenshot file
    OUTPUT_DIR="$(dirname "$SCREENSHOT")"
fi

if [[ -z "$ENDPOINT" ]]; then
    echo "ERROR: endpoint not set in config: $CONFIG" >&2
    exit 2
fi
if [[ -z "$MODEL" ]]; then
    echo "ERROR: model not set in config: $CONFIG" >&2
    exit 2
fi

# ── API key ─────────────────────────────────────────────────────────────────────
API_KEY=""
if [[ -n "$API_KEY_ENV" ]]; then
    API_KEY="${!API_KEY_ENV:-}"
fi

# ── Encode screenshot to base64 ────────────────────────────────────────────────
# Write base64 to a temp file to avoid "Argument list too long" on large images.
BASE64_TMP="$(mktemp 2>/dev/null || mktemp -t aas)"
base64 -i "$SCREENSHOT" | tr -d '\n' > "$BASE64_TMP"

MIME_TYPE=""
lower_screenshot="$(echo "$SCREENSHOT" | tr '[:upper:]' '[:lower:]')"
case "$lower_screenshot" in
    *.png)  MIME_TYPE="image/png" ;;
    *.jpg|*.jpeg) MIME_TYPE="image/jpeg" ;;
    *)      MIME_TYPE="image/png" ;;
esac

# ── Build JSON payload via python3, reading base64 from temp file ──────────────
PAYLOAD="$(tk_python -c "
import json, sys

with open('${BASE64_TMP}', 'r') as f:
    image_b64 = f.read().strip()
model = '''${MODEL}'''
system_prompt = '''${SYSTEM_PROMPT}'''
user_prompt = '''${USER_PROMPT}'''
mime_type = '''${MIME_TYPE}'''

messages = []
if system_prompt:
    messages.append({'role': 'system', 'content': system_prompt})

messages.append({
    'role': 'user',
    'content': [
        {'type': 'text', 'text': user_prompt},
        {
            'type': 'image_url',
            'image_url': {
                'url': f'data:{mime_type};base64,{image_b64}'
            }
        }
    ]
})

payload = {
    'model': model,
    'messages': messages,
    'max_tokens': 1024,
    'temperature': 0.1
}

json.dump(payload, sys.stdout, indent=2)
")" || {
    rm -f "$BASE64_TMP"
    echo "ERROR: Failed to build JSON payload" >&2
    exit 3
}
rm -f "$BASE64_TMP"

if $DEBUG; then
    echo "=== DEBUG: Payload sent to ${ENDPOINT}/v1/chat/completions ===" >&2
    echo "$PAYLOAD" >&2
    echo "=== END DEBUG ===" >&2
fi

# ── Send request ───────────────────────────────────────────────────────────────
CONTENT_TYPE="Content-Type: application/json"
AUTH_HEADER=""
if [[ -n "$API_KEY" ]]; then
    AUTH_HEADER="Authorization: Bearer ${API_KEY}"
fi

CHAT_URL="${ENDPOINT}/v1/chat/completions"

RESPONSE="$(curl -s -w "\n%{http_code}" \
    "${CHAT_URL}" \
    -H "${CONTENT_TYPE}" \
    ${AUTH_HEADER:+-H "$AUTH_HEADER"} \
    -d "$PAYLOAD" 2>/dev/null)" || true

# ── Parse response ──────────────────────────────────────────────────────────────
HTTP_CODE="$(echo "$RESPONSE" | tail -1)"
BODY="$(echo "$RESPONSE" | sed '$d')"

if $DEBUG; then
    echo "=== DEBUG: Raw response (HTTP ${HTTP_CODE}) ===" >&2
    echo "$BODY" | tk_python -m json.tool 2>/dev/null || echo "$BODY" >&2
    echo "=== END DEBUG ===" >&2
fi

if [[ "$HTTP_CODE" != "2"* ]]; then
    echo "ERROR: API returned HTTP ${HTTP_CODE}" >&2
    if ! $DEBUG; then
        echo "       Use -d for full response dump." >&2
    fi
    echo "$BODY" | tk_python -m json.tool 2>/dev/null || echo "$BODY" >&2
    exit 3
fi

# Extract content from response using python3
ANALYSIS="$(echo "$BODY" | tk_python -c "
import sys, json
data = json.load(sys.stdin)
msg = data['choices'][0]['message']['content']
print(msg)
" 2>/dev/null)" || {
    echo "ERROR: Could not parse API response" >&2
    echo "$BODY" >&2
    exit 3
}

# ── Save analysis to file ──────────────────────────────────────────────────────
mkdir -p "$OUTPUT_DIR" 2>/dev/null || true
SCREENSHOT_BASENAME="$(basename "$SCREENSHOT")"
SCREENSHOT_NAME="${SCREENSHOT_BASENAME%.*}"
ANALYSIS_FILE="${OUTPUT_DIR}/${SCREENSHOT_NAME}_analysis.md"

{
    echo "# Screenshot Analysis — ${SCREENSHOT_BASENAME}"
    echo ""
    echo "**Model:** ${MODEL}  "
    echo "**Endpoint:** ${ENDPOINT}  "
    echo "**Date:** $(date '+%Y-%m-%d %H:%M:%S')  "
    echo "**User prompt:** ${USER_PROMPT}"
    echo ""
    echo "---"
    echo ""
    echo "$ANALYSIS"
} > "$ANALYSIS_FILE"

echo "---"
echo "Analysis saved to: ${ANALYSIS_FILE}"
echo ""
echo "$ANALYSIS"
exit 0
