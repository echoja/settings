# Settings

개인 macOS zsh 환경 설정을 담고 있는 저장소입니다.

## 구성
- `.zshrc`: Oh My Zsh 기반 설정과 자주 쓰는 alias, 함수가 포함되어 있습니다.
- `link_home_zshrc.sh`: 현재 저장소의 `.zshrc`를 `~/.zshrc`로 심볼릭 링크합니다.

## 사용 방법
1. 저장소를 `~/settings` 경로에 clone합니다. 
2. `./link_home_zshrc.sh`를 실행합니다.
   - 기존 `~/.zshrc`를 삭제하므로 주의합니다.
   - 진행 전 `[y/N]:` 확인을 요청하며 `y`/`Y` 입력 시에만 진행됩니다. 그 외 입력(Enter 포함)은 모두 취소됩니다.
3. 터미널을 다시 열거나 `source ~/.zshrc`로 설정을 반영합니다.

## Pre-commit
- `.zshrc`에 `/Users/<name>` 또는 `/home/<name>` 형태의 하드코딩된 home 경로가 들어가면 실패합니다.
- `$HOME`을 사용하도록 강제합니다.
- 설치 후 훅 등록:
  - `brew install pre-commit`
  - `pre-commit install`
