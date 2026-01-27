# GPU 서버 요청 프롬프트 - 박성민 스타일 분석

## 📍 현재 상황

CPU 서버(172.10.5.132)에서 박성민 사용자 사진을 GPU 서버로 전송했어.
이 사진을 분석해서 퍼스널 컬러와 스타일 추천을 해줘.

---

## 🖼️ 사용자 사진

**파일 위치**: `/root/MadCamp_3week/uploads/users/박성민_num1.jpg`

**사진 설명**:
- 사용자: 박성민
- 의상: Stussy 그레이 후드티 + 진청 와이드 데님
- 신발: 흰색/베이지 스니커즈
- 배경: 사무실/회의실

---

## 🎯 요청 작업

### 1. 퍼스널 컬러 분석
사진에서 사용자의 피부톤/헤어컬러 분석:
- 쿨톤/웜톤 판별
- PCCS 톤 분류 (ltg, dkg, v 등)
- 추천 색상 팔레트

### 2. 현재 스타일 분석
착용 의상 분석:
- 그레이 후드: 색상 톤, PCCS 분류
- 청바지: 톤, 워싱 정도
- 전체 코디 점수

### 3. 추천 상품 생성
무신사에서 이 스타일에 어울리는 상품 추천:
- 비슷한 스타일의 후드티 3-5개
- 어울리는 하의 3-5개
- 매칭 아우터 2-3개
- 신발/액세서리 2-3개

---

## 📡 API 활용

### 색상 분석 API 호출
```bash
curl -X POST http://localhost:8000/ai-recommend/analyze-color \
  -H "Content-Type: application/json" \
  -d '{"image_url": "file:///root/MadCamp_3week/uploads/users/박성민_num1.jpg"}'
```

### 스타일 추천 API
```bash
curl -X POST http://localhost:8000/ai-recommend/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "product": {
      "id": "user_박성민",
      "title": "사용자 스타일 분석",
      "thumbnail_url": "file:///root/MadCamp_3week/uploads/users/박성민_num1.jpg",
      "category": "user_style"
    },
    "tone_preference": "neutral",
    "limit": 10
  }'
```

---

## 📋 응답 형식

분석 완료 후 결과를 `/tmp/박성민_분석결과.json`에 저장:

```json
{
  "user": "박성민",
  "personal_color": {
    "type": "cool_tone",
    "season": "summer",
    "pccs_tone": "ltg"
  },
  "current_style": {
    "top": {"item": "Stussy 그레이 후드", "pccs": "ltg", "score": 8.5},
    "bottom": {"item": "진청 와이드 데님", "pccs": "dk", "score": 8.0}
  },
  "recommendations": [
    {"type": "top", "musinsa_id": "1234567", "title": "...", "match_score": 0.95},
    ...
  ]
}
```

---

## 📞 완료 후 알림

분석 완료되면 CPU 서버에 알려줘:
```bash
ssh root@172.10.5.132 "echo '[$(date)] 박성민 스타일 분석 완료' >> /tmp/gpu_status.txt"
```

---

## ⚠️ 참고사항

- 사진은 이미 GPU 서버에 저장됨
- CPU 서버는 AI API 호출 클라이언트 구현 완료
- 양방향 SSH 통신 설정 완료
