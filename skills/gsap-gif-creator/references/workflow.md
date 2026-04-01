# GSAP GIF 제작 워크플로우

## 권장 기준

- 시간은 플랫폼별로 나누지 않는다.
- 먼저 `무엇을 보여줘야 하는가`를 정하고, 그 결과가 한 루프 안에서 충분히 보이는 길이를 잡는다.
- 기본 시작점은 `2~5초`, `12~15fps`, `폭 480~640`, `colors 64~96`이다.
- 장면이 단순한 배지나 아이콘 루프면 더 짧아도 되지만, 결과 비교나 전후 변화가 있으면 길이를 늘린다.

## 길이 결정 규칙

1. 결과가 나타나는 순간만 보여주지 말고, 변화 전 상태와 변화 후 상태를 모두 포함한다.
2. 텍스트, 숫자, 강조 포인트가 있다면 사용자가 읽을 시간을 남긴다.
3. 반복 루프라면 마지막 장면이 너무 빨리 끊겨 보이지 않도록 0.2~0.6초 정도의 여유 구간을 검토한다.
4. 길이가 길어져 용량이 커지면 시간을 먼저 잘라내기보다 `width`, `fps`, `colors`를 우선 조정한다.

## GSAP 애니메이션 구성 체크리스트

1. 장면 길이를 초 단위로 고정한다.
2. 첫 프레임과 마지막 프레임의 연결감을 확인한다.
3. `x`, `y`, `scale`, `rotation`, `autoAlpha` 위주로 구성한다.
4. layout 변화가 큰 `width`, `height`, `top`, `left` 애니메이션은 피한다.
5. ScrollTrigger, hover, drag 기반 상호작용은 autoplay timeline으로 바꾼다.

## 기존 프로토타입을 GIF용으로 바꾸는 방법

### scroll 기반

- 원본이 `ScrollTrigger`여도 GIF 버전은 별도 timeline으로 재구성한다.
- 스크롤 진행도에 따라 바뀌는 상태를 핵심 장면 2~4개로 요약한다.
- 각 장면을 `label`로 분리하고 자연스럽게 이어 붙인다.

### hover 기반

- hover in/out 상태를 timeline 두 구간으로 분리한다.
- `mouseenter`를 기다리지 말고 자동 재생 순서로 배치한다.

### 랜덤 기반

- `gsap.utils.random()`을 그대로 쓰면 캡처마다 결과가 달라질 수 있다.
- 반복 가능성이 중요하면 랜덤 대신 고정 배열이나 계산식으로 바꾼다.

## 변환 스크립트 사용 예시

기본 변환:

```bash
python3 skills/gsap-gif-creator/scripts/video_to_gif.py demo.mp4 demo.gif
```

용량을 더 줄이고 싶을 때:

```bash
python3 skills/gsap-gif-creator/scripts/video_to_gif.py demo.mp4 demo.gif \
  --width 480 \
  --fps 12 \
  --colors 64
```

앞부분 0.2초를 버리고 2초만 쓰고 싶을 때:

```bash
python3 skills/gsap-gif-creator/scripts/video_to_gif.py demo.mp4 demo.gif \
  --start 0.2 \
  --duration 2.0
```

## 자주 발생하는 문제

- 용량이 너무 큼:
  결과 전달이 유지된다면 `width`, `fps`, `colors`를 먼저 줄이고, 마지막에 `duration`을 조정한다.
- 글자가 깨져 보임:
  너무 작은 해상도에서 축소한 경우가 많다. 원본 캡처 폭을 올리고 GIF 폭은 480~640 정도로 유지한다.
- 루프가 어색함:
  마지막 장면이 첫 장면으로 자연스럽게 복귀하는지 확인하고, 필요하면 마지막 0.2~0.4초를 조정한다.
- 가장자리가 지저분함:
  GIF 투명도 한계일 수 있다. 단색 배경을 쓰거나 MP4/WebM 전환 가능 여부를 먼저 확인한다.
