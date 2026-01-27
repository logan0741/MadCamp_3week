#!/bin/bash
# AI Pipeline API 테스트 스크립트
# 모든 엔드포인트를 테스트하고 결과를 출력합니다.

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API Configuration
API_BASE_URL="${AI_API_URL:-http://localhost:8001}"

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  AI Pipeline API 테스트${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "API URL: $API_BASE_URL\n"

# ============================================
# 1. Health Check
# ============================================
echo -e "${YELLOW}[1/8] Health Check 테스트...${NC}"
curl -s "$API_BASE_URL/health" | jq '.'
echo -e "${GREEN}✓ Health Check 성공${NC}\n"

# ============================================
# 2. VRAM Status
# ============================================
echo -e "${YELLOW}[2/8] VRAM 상태 조회...${NC}"
curl -s "$API_BASE_URL/vram-status" | jq '.'
echo -e "${GREEN}✓ VRAM 상태 조회 성공${NC}\n"

# ============================================
# 3. VTON Model Status
# ============================================
echo -e "${YELLOW}[3/8] VTON 모델 상태 확인...${NC}"
curl -s "$API_BASE_URL/api/vton/model/status" | jq '.'
echo -e "${GREEN}✓ 모델 상태 확인 성공${NC}\n"

# ============================================
# 4. Synchronous VTON (URL)
# ============================================
echo -e "${YELLOW}[4/8] 동기 VTON 테스트 (URL)...${NC}"

# 테스트 이미지 URL (실제 이미지로 교체 필요)
PERSON_URL="https://example.com/person.jpg"
GARMENT_URL="https://example.com/garment.jpg"

RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/vton/try-on" \
  -H "Content-Type: application/json" \
  -d "{
    \"person_image_url\": \"$PERSON_URL\",
    \"garment_image_url\": \"$GARMENT_URL\",
    \"num_inference_steps\": 30,
    \"guidance_scale\": 7.5,
    \"enhance_output\": true,
    \"restore_face\": true
  }" 2>&1)

if echo "$RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
  echo -e "${GREEN}✓ 동기 VTON 성공${NC}"
  echo "$RESPONSE" | jq '.'
else
  echo -e "${RED}✗ 동기 VTON 실패 (이미지 URL 확인 필요)${NC}"
  echo "$RESPONSE"
fi
echo ""

# ============================================
# 5. Asynchronous VTON
# ============================================
echo -e "${YELLOW}[5/8] 비동기 VTON 테스트...${NC}"

ASYNC_RESPONSE=$(curl -s -X POST "$API_BASE_URL/api/vton/try-on/async" \
  -H "Content-Type: application/json" \
  -d "{
    \"person_image_url\": \"$PERSON_URL\",
    \"garment_image_url\": \"$GARMENT_URL\",
    \"num_inference_steps\": 30
  }")

if echo "$ASYNC_RESPONSE" | jq -e '.task_id' > /dev/null 2>&1; then
  TASK_ID=$(echo "$ASYNC_RESPONSE" | jq -r '.task_id')
  echo -e "${GREEN}✓ 비동기 작업 제출 성공${NC}"
  echo "$ASYNC_RESPONSE" | jq '.'
  echo ""

  # ============================================
  # 6. Task Status Check
  # ============================================
  echo -e "${YELLOW}[6/8] 작업 상태 조회 (Task ID: $TASK_ID)...${NC}"

  # 폴링 (최대 60초)
  MAX_WAIT=60
  WAIT_TIME=0

  while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    STATUS_RESPONSE=$(curl -s "$API_BASE_URL/api/vton/tasks/$TASK_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')

    echo "$STATUS_RESPONSE" | jq '.'

    if [ "$STATUS" = "SUCCESS" ]; then
      echo -e "${GREEN}✓ 작업 완료!${NC}"
      break
    elif [ "$STATUS" = "FAILURE" ]; then
      echo -e "${RED}✗ 작업 실패${NC}"
      break
    elif [ "$STATUS" = "PROGRESS" ]; then
      PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress // 0')
      echo -e "${YELLOW}진행 중... ${PROGRESS}%${NC}"
    fi

    sleep 2
    WAIT_TIME=$((WAIT_TIME + 2))
  done

  if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}⚠ 타임아웃 (작업이 아직 진행 중)${NC}"
  fi
  echo ""

else
  echo -e "${RED}✗ 비동기 작업 제출 실패${NC}"
  echo "$ASYNC_RESPONSE"
  echo ""
fi

# ============================================
# 7. File Upload Test (스킵 - 실제 파일 필요)
# ============================================
echo -e "${YELLOW}[7/8] 파일 업로드 테스트 (스킵 - 실제 파일 필요)${NC}"
echo -e "${YELLOW}수동 테스트 방법:${NC}"
echo "curl -X POST \"$API_BASE_URL/api/vton/try-on/upload\" \\"
echo "  -F \"person_image=@/path/to/person.jpg\" \\"
echo "  -F \"garment_image=@/path/to/garment.jpg\" \\"
echo "  -F \"num_inference_steps=50\""
echo ""

# ============================================
# 8. API Documentation
# ============================================
echo -e "${YELLOW}[8/8] API 문서 확인...${NC}"
echo -e "${GREEN}Swagger UI: ${API_BASE_URL}/docs${NC}"
echo -e "${GREEN}ReDoc: ${API_BASE_URL}/redoc${NC}"
echo ""

# ============================================
# Summary
# ============================================
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  테스트 완료${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "다음 단계:"
echo "  1. 브라우저에서 Swagger UI 확인: $API_BASE_URL/docs"
echo "  2. 실제 이미지로 테스트"
echo "  3. 프론트엔드 통합"
echo ""
