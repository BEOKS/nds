---
name: gsap-gif-creator
description: GSAP 기반 애니메이션을 짧은 루프 GIF로 설계, 캡처, 변환, 최적화하는 스킬. 사용자가 GSAP/HTML/React 애니메이션을 GIF로 만들어 달라고 하거나, 데모·랜딩·프로토타입 모션을 문서나 Slack에 넣을 GIF로 내보내야 하거나, 기존 MP4를 GSAP 작업물 기준으로 GIF로 다듬어야 할 때 사용한다. gsap-core, gsap-timeline, gsap-react, gsap-performance 스킬을 조합하고 scripts/video_to_gif.py로 MP4를 GIF로 변환한다.
---

# GSAP GIF Creator

짧고 반복 가능한 GSAP 애니메이션을 최종 GIF 산출물로 마무리할 때 사용한다. 인터랙티브 프로토타입을 그대로 녹화하지 말고, 캡처 가능한 deterministic timeline으로 다시 구성한 뒤 GIF로 변환한다.

## 기본 흐름

1. GIF 스펙을 먼저 고정한다.
   - 기본 확인 항목: `용도`, `가로폭`, `길이`, `반복 여부`, `배경색`, `목표 용량`
   - 정보가 없으면 플랫폼별 고정값보다 `생성 결과를 충분히 보여줄 수 있는 최소 길이`를 먼저 잡는다. 기본값은 `2~5초`, `12~15fps`, `폭 480~640px`, `무한 반복`을 우선 제안한다.
2. 애니메이션 구현 방식을 고른다.
   - 단일 tween, easing, stagger 중심이면 `gsap-core`
   - 여러 장면을 이어야 하면 `gsap-timeline`
   - React/Next.js 컴포넌트면 `gsap-react`
   - 성능 최적화가 중요하면 `gsap-performance`
   - ScrollTrigger 기반 원본이라면 `gsap-scrolltrigger`를 참고하되, GIF 버전은 반드시 자동 재생 timeline으로 재구성한다.
3. GIF 친화적으로 애니메이션을 바꾼다.
   - 시작과 끝이 명확한 `timeline`을 만든다.
   - `transform`, `opacity` 위주로 애니메이션한다.
   - hover, scroll, drag, resize 같은 사용자 입력 의존성을 제거한다.
   - 무한 루프가 필요하면 끝 프레임과 첫 프레임이 자연스럽게 이어지도록 만든다.
4. 애니메이션을 캡처 가능한 산출물로 준비한다.
   - HTML/React 데모 페이지 또는 MP4를 만든다.
   - 이미 MP4가 있으면 바로 `scripts/video_to_gif.py`를 사용한다.
5. GIF로 변환하고 최적화한다.
   - `fps`, `width`, `colors`, `duration`을 줄이면서 용량과 선명도를 맞춘다.

## GSAP 스킬 조합 규칙

- `gsap-core`: 진입 모션, fade, move, scale, easing 기본기
- `gsap-timeline`: 장면 순서, label, overlap, seamless loop
- `gsap-react`: `useGSAP()`, scope, cleanup, SSR 회피
- `gsap-performance`: transform 우선, 불필요한 layout 회피, 동시 작업 축소
- `gsap-utils`: 랜덤값, clamp, mapRange, wrap 같은 계산 보조
- `gsap-plugins`: SplitText, DrawSVG, MorphSVG, Flip 등 특수 효과

## GIF로 내보낼 때의 판단 기준

- 길이는 플랫폼이 아니라 결과 전달력 기준으로 정한다. 사용자가 무엇을 봐야 하는지 한 번에 이해할 수 있을 만큼은 충분히 보여준다.
- 불필요하게 길게 만들지는 않는다. 다만 핵심 결과가 잘리지 않는 한도에서는 짧게 줄인다.
- 배경을 단순하게 만든다. 사진 배경, 노이즈, 반투명 그림자는 GIF 압축 효율이 낮다.
- 스크롤 기반 인터랙션은 그대로 녹화하지 않는다. 핵심 장면만 timeline으로 옮긴다.
- 반투명 가장자리가 중요하면 GIF보다 MP4/WebM/APNG가 더 적합하다. 사용자가 GIF를 고정 요구할 때만 제한을 감수한다.

## 빠른 사용법

MP4가 준비되어 있으면 아래 스크립트로 변환한다.

```bash
python3 skills/gsap-gif-creator/scripts/video_to_gif.py input.mp4 output.gif \
  --width 640 \
  --fps 15 \
  --colors 96
```

특정 구간만 자르려면:

```bash
python3 skills/gsap-gif-creator/scripts/video_to_gif.py input.mp4 output.gif \
  --start 0.3 \
  --duration 2.4 \
  --width 480 \
  --fps 12
```

## 작업 원칙

- deterministic animation을 우선한다.
- 사용자 입력 없이도 같은 결과가 재생되게 만든다.
- 시간은 플랫폼별 preset으로 고정하지 않는다. 결과 확인에 필요한 장면이 모두 보이는 길이를 우선한다.
- 기본값이 필요하면 `timeline + repeat: -1 + yoyo 최소화`를 우선 검토한다.
- 과한 랜덤 효과를 쓰면 루프 경계가 깨질 수 있으므로 seed 또는 고정값을 선호한다.

## 추가 참고

- 세부 워크플로우와 preset은 [references/workflow.md](references/workflow.md)를 읽는다.
- 변환 스크립트 옵션은 `python3 skills/gsap-gif-creator/scripts/video_to_gif.py --help`로 확인한다.
