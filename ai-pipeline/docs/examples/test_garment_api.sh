#!/usr/bin/env bash
set -euo pipefail

API_BASE="http://localhost:8001"
FRONT_IMAGE=${1:-"/path/to/front.jpg"}
BACK_IMAGE=${2:-"/path/to/back.jpg"}
GARMENT_TYPE=${3:-"top"}
PRODUCT_ID=${4:-"12345"}
SIZE_LABEL=${5:-"M"}
HEIGHT_CM=${6:-"170"}
WEIGHT_KG=${7:-"65"}

if [[ ! -f "$FRONT_IMAGE" || ! -f "$BACK_IMAGE" ]]; then
  echo "Front/Back 이미지 경로를 인자로 넘겨주세요."
  echo "예: $0 ./front.jpg ./back.jpg top 12345 M 170 65"
  exit 1
fi

echo "[1/2] Garment process (sync)"
curl -s -X POST "${API_BASE}/api/garment/process" \
  -F "front_image=@${FRONT_IMAGE}" \
  -F "back_image=@${BACK_IMAGE}" \
  -F "garment_type=${GARMENT_TYPE}" \
  -F "product_id=${PRODUCT_ID}" \
  -F "size=${SIZE_LABEL}" \
  -F "height_cm=${HEIGHT_CM}" \
  -F "weight_kg=${WEIGHT_KG}" | jq .

echo "[2/2] Size lookup"
curl -s "${API_BASE}/api/garment/sizes/${PRODUCT_ID}" | jq .
