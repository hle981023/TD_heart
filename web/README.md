# Guardian Heart — WebGL

수호 캐릭터 **알**과 **자물쇠**를 손짓으로 소환하는 실시간 브라우저 AR.
TouchDesigner 버전을 웹으로 옮긴 것 — Three.js(WebGL) + MediaPipe Hands(브라우저 손 인식).

## 실행

정적 파일이라 빌드가 필요 없다. 카메라는 **HTTPS 또는 localhost**에서만 동작한다.

```bash
cd web
python3 -m http.server 5533
# http://localhost:5533/  → "시작하기" 클릭 → 카메라 허용
```

CDN(jsDelivr)에서 Three.js와 MediaPipe를 불러오므로 인터넷 연결이 필요하다.

### 카메라 없이 보기 (데모)

```
http://localhost:5533/?demo=1
```

알·자물쇠·이펙트가 스크립트대로 순환한다. `&phase=summon` 또는 `&phase=fuse`로 한 단계 고정.

## 제스처

| 손짓 | 효과 |
|------|------|
| 왼손 검지 | 알 소환 (회전·둥둥 + 하트 구름) |
| 오른손 검지 | 자물쇠 소환 (금색·오팔 클로버) |
| 두 검지 포개기 | **융합** — 자물쇠만 중앙에, 무지개 발광 + 방사 광선 + 궤도 오브 |
| 핑거 하트(엄지 붙임) | 작은 하트 발사 |
| 두 손바닥 펼치기 | 큰 하트 발사 |

## 구성

- `index.html` — 웹캠 비디오 + WebGL 캔버스 + importmap(Three.js / MediaPipe)
- `src/main.js` — 씬, 손 인식, 제스처 분류, 알/자물쇠, 파티클 이펙트
- `assets/lock_touchdesigner.fbx` — 자물쇠 3D 모델(베이크드 텍스처 포함)
- `assets/hand_landmarker.task` — MediaPipe 손 랜드마크 모델

알은 절차적으로 생성(빨강 셸 + 하트 밴드), 자물쇠는 FBX의 베이크드 텍스처를 언릿으로 사용한다.
