---
name: hiworks-ui
description: Hiworks UI 컴포넌트 및 아이콘 라이브러리 사용 가이드. 하이웍스 제품군(office.hiworks.com, 하이웍스관리 등)에서 일관된 UI/UX를 위해 공통 디자인 시스템을 적용할 때 참고한다.
---

# Hiworks UI & Icons 가이드

## 개요

Hiworks 디자인 시스템은 **하이웍스 제품군 전용** UI/UX 라이브러리입니다.

### 적용 대상

- **Office**: office.hiworks.com (하이웍스 오피스)
- **Platform**: 경영플랫폼
- **Admin**: 하이웍스관리 (관리자)

> **Note**: 가비아 다른 서비스(gabia.com 등)에는 적용되지 않습니다.

### 라이브러리 구성

| 라이브러리 | GitLab | 문서/데모 | 패키지명 |
|------------|--------|-----------|----------|
| UI 컴포넌트 | https://gitlab.gabia.com/ui/hiworks-ui-components | https://hiworks-design-system.hiworks.com | `@aspect_hiworks/aspects-ui` |
| 아이콘 | https://gitlab.gabia.com/ui/icons.hiworks.com | https://icons.hiworks.com | `@aspect_hiworks/aspects-icons` |

### 관련 문서

| 문서 | URL |
|------|-----|
| 컴포넌트 담당자 | https://confluence.gabia.com/spaces/hfront/pages/191810741 |
| 아이콘 추가 가이드 | https://confluence.gabia.com/spaces/hfront/pages/222323374 |
| 아이콘 Figma | https://www.figma.com/design/KLBUZB2bvcQnPKfXPvTteg/하이웍스-아이콘 |

## 설치

### 1. GitLab NPM Registry 설정

`.npmrc` 파일 생성 (프로젝트 루트 또는 `~/.npmrc`):

```ini
@aspect_hiworks:registry=https://gitlab.gabia.com/api/v4/packages/npm/
//gitlab.gabia.com/api/v4/packages/npm/:_authToken=${GITLAB_NPM_TOKEN}
```

### 2. 환경변수 설정

```bash
# GitLab Personal Access Token (read_api, read_registry 권한)
export GITLAB_NPM_TOKEN="your-gitlab-token"
```

### 3. 패키지 설치

```bash
# pnpm 사용 시
pnpm add @aspect_hiworks/aspects-ui @aspect_hiworks/aspects-icons

# npm 사용 시
npm install @aspect_hiworks/aspects-ui @aspect_hiworks/aspects-icons
```

## UI 컴포넌트 (@aspect_hiworks/aspects-ui)

### 스토리북

**URL**: https://hiworks-design-system.hiworks.com

모든 컴포넌트의 Props, 사용 예시, 인터랙션을 확인할 수 있습니다.

### 제공 컴포넌트 및 담당자

| 순번 | 컴포넌트 | 담당자 (주/부) | 플랫폼 | 비고 |
|------|----------|----------------|--------|------|
| 1 | Autocomplete | 월리 / 랄프 | Office, Platform | |
| 2 | Banner | 페페 / 라임 | Office, Platform, Admin | |
| 3 | Button, IconButton | 엘리 / 위니 | Office, Platform, Admin | |
| 4 | Checkbox | 페페 / 엘리 | Office, Platform, Admin | |
| 5 | DatePicker, DateRangePicker | 이안 / 데이지 | Office, Platform, Admin | |
| 6 | Dropdown | 랄프 / 페페 | Office, Platform, Admin | |
| 7 | Input (FileInput, NumberInput, Textarea, TextInput) | 월리 / 애셔 | Office, Platform, Admin | |
| 8 | Select, MultiSelect | 모리 / 길벗 | Office, Platform, Admin | |
| 9 | Pagination | 랄프 / 월리 | Office, Platform, Admin | 동작 상이 주의 |
| 10 | Radio, BoxRadio | 에릭 / 모리 | Office, Platform, Admin | |
| 11 | Tab | 위니 / 데이지 | Office, Platform, Admin | |
| 12 | Table | 데이지 / 라임 | Office, Platform, Admin | |
| 13 | Tag, Badge | 애셔 / 엘리 | Office, Platform, Admin | |
| 14 | Toast | 길벗 / 위니 | Office, Platform, Admin | |
| 15 | Toggle | 챙 / 이안 | Office, Platform, Admin | |
| 16 | Tooltip | 라임 / 랄프 | Office, Platform, Admin | |
| 17 | Tree | 길벗 / 페페 | - | 제외 |
| 18 | Progress | 위니 / 애셔 | Platform | |
| 19 | Spinner | 엘리 / 길벗 | Platform, Admin | |
| 20 | Stepper | 애셔 / 월리 | Platform, Admin | |

### 플랫폼별 import 접두어

스토리북 내 import 문 규칙:
- **Platform**: `P_` 접두어 (예: `P_Button`)
- **Office**: `O_` 접두어 (예: `O_Button`)
- **HiworksAdmin**: `A_` 접두어 (예: `A_Button`)

### 사용 예시

```tsx
import { Button, Input, Modal } from '@aspect_hiworks/aspects-ui';

function MyComponent() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div>
      <Input placeholder="이름을 입력하세요" />
      <Button variant="primary" onClick={() => setIsOpen(true)}>
        모달 열기
      </Button>

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
        <Modal.Header>제목</Modal.Header>
        <Modal.Body>내용</Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setIsOpen(false)}>
            취소
          </Button>
          <Button variant="primary">확인</Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}
```

### 스토리 작성 가이드

1. **import 경로**: 상대 경로를 `@` alias로 변경
   ```tsx
   // Bad
   import { X } from '../../../components/Radio'
   // Good
   import { X } from '@components/Radio'
   ```

2. **스토리 구성 요소**:
   - 프리뷰 (Preview)
   - 컨트롤러 (Controller)

3. **개발자 전용 내용**: 프론트엔드 개발자만 참고할 부분은 이모티콘(🔧) 추가

4. **설명 추가 시**:
   ```tsx
   import { MdxDescription } from '@stories/shared/components/MdxDescription/MdxDescription'

   <MdxDescription>
     드랍다운 아이템 개수가 3개만 보입니다.
   </MdxDescription>
   ```

5. **복수 컴포넌트 스토리**: `<div>` 태그로 감싸고 `gap: 16` 적용

## 아이콘 (@aspect_hiworks/aspects-icons)

### 아이콘 검색

**URL**: https://icons.hiworks.com

### 아이콘 구조

```
/src/
├── file/
│   ├── 18/      # 파일 아이콘 18px
│   ├── 36/      # 파일 아이콘 36px
│   └── 60/      # 파일 아이콘 60px
├── solid/
│   └── 16/      # Solid 아이콘 16px
└── line/
    └── 16/      # Line 아이콘 16px
```

### 사용 방법

```tsx
import { IconSearch, IconUser, IconSettings } from '@aspect_hiworks/aspects-icons';

function MyComponent() {
  return (
    <div>
      <IconSearch size={24} color="#333" />
      <IconUser size={20} />
      <IconSettings className="text-gray-500" />
    </div>
  );
}
```

### 아이콘 추가 가이드

#### 1단계: Figma에서 SVG 내보내기

[아이콘 Figma 문서](https://www.figma.com/design/KLBUZB2bvcQnPKfXPvTteg/하이웍스-아이콘)에서 내보내기(export)로 SVG 파일 저장

#### 2단계: SVG 파일 이동

저장한 SVG 파일을 `/src/(유형)/(크기)/` 위치로 이동

#### 3단계: meta.js 수정

`packages/hiworks-icons/meta.js` 파일에 아이콘 정보 추가:

```javascript
exports.meta = {
  ['file/18']: {
    '아이콘이름': {
      isDeprecated: false,        // deprecated 여부
      description: '아이콘 설명',
      version: '25-11-05',        // 추가된 날짜
      category: 'Data',           // 분류 (Data, Building & Commerce 등)
      order: 250                  // 표시 순서 (10단위 권장)
    }
  },
  ['solid/16']: { ... },
  ['line/16']: { ... },
};
```

**meta 필드 설명**:
- `isDeprecated`: true일 경우 web에 deprecated 뱃지 표시
- `version`: 추가 날짜, web에 NEW 뱃지로 표시
- `category`: Figma 시안 기준 분류명
- `order`: Figma 문서와 동일한 순서 유지, 미지정시 기본값 99999

#### 4단계: 폰트 아이콘 수정

[IcoMoon 폰트 아이콘 관리 가이드](https://confluence.gabia.com/pages/viewpage.action?pageId=159269644) 참고

#### 5단계: 배포

master 머지 후 tag 배포

### 아이콘 추가 FAQ

**Q. Figma 문서에 없는 아이콘은?**

A. 먼저 안나/린다에게 아이콘 라이브러리 추가 가능 여부 문의 → 불가능하면 SVG 태그 또는 개별 아이콘 컴포넌트 사용 권장

## 프로젝트 설정 가이드

### Vite + React + TypeScript

```bash
# 프로젝트 생성
pnpm create vite my-app --template react-ts
cd my-app

# Hiworks UI 설치
pnpm add @aspect_hiworks/aspects-ui @aspect_hiworks/aspects-icons
```

### 스타일 설정

```tsx
// src/main.tsx
import '@aspect_hiworks/aspects-ui/dist/styles.css'; // UI 스타일
import './index.css'; // 프로젝트 스타일
```

## 사용 전략

### 1. 우선 사용 원칙

하이웍스 UI 컴포넌트 라이브러리에서 제공하는 컴포넌트를 우선 사용합니다.

```tsx
// Good - 라이브러리 컴포넌트 사용
import { Button, Input, Modal } from '@aspect_hiworks/aspects-ui';

// Avoid - 직접 구현 (라이브러리에 있는 경우)
const MyButton = styled.button`...`;
```

### 2. 커스터마이징

필요시 래핑하여 프로젝트에 맞게 확장합니다.

```tsx
// components/ui/AppButton.tsx
import { Button, ButtonProps } from '@aspect_hiworks/aspects-ui';

interface AppButtonProps extends ButtonProps {
  isLoading?: boolean;
}

export function AppButton({ isLoading, children, ...props }: AppButtonProps) {
  return (
    <Button {...props} disabled={isLoading || props.disabled}>
      {isLoading ? <Spinner size="sm" /> : children}
    </Button>
  );
}
```

### 3. 신규 개발

라이브러리에 없는 프로젝트 특화 컴포넌트만 신규 개발합니다.

## 트러블슈팅

### 패키지 설치 실패

```bash
# 1. 토큰 확인
echo $GITLAB_NPM_TOKEN

# 2. .npmrc 확인
cat .npmrc

# 3. 캐시 정리 후 재설치
pnpm store prune
pnpm install
```

### 스타일 미적용

```tsx
// main.tsx에서 스타일 import 확인
import '@aspect_hiworks/aspects-ui/dist/styles.css';
```

## 참고 링크

| 리소스 | URL |
|--------|-----|
| UI 스토리북 | https://hiworks-design-system.hiworks.com |
| 아이콘 검색 | https://icons.hiworks.com |
| UI GitLab | https://gitlab.gabia.com/ui/hiworks-ui-components |
| Icons GitLab | https://gitlab.gabia.com/ui/icons.hiworks.com |
| 컴포넌트 담당자 | https://confluence.gabia.com/spaces/hfront/pages/191810741 |
| 아이콘 추가 가이드 | https://confluence.gabia.com/spaces/hfront/pages/222323374 |
| 아이콘 Figma | https://www.figma.com/design/KLBUZB2bvcQnPKfXPvTteg |

---

**마지막 업데이트**: 2026-02-06
**참고**: 실제 패키지명과 API는 GitLab 저장소 및 스토리북에서 최신 정보를 확인하세요.
