# Settings

개인 macOS zsh 환경 설정을 담고 있는 저장소입니다.

## 구성
- `.zshrc`: Oh My Zsh 기반 설정과 자주 쓰는 alias, 함수가 포함되어 있습니다.
- `.codex/config.toml`: Codex CLI 설정 파일입니다.
- `scripts/bootstrap.py`: 저장소의 설정 파일을 홈 디렉터리에 심볼릭 링크합니다.

## 사용 방법
1. 저장소를 `~/settings` 경로에 clone합니다. 
2. `./scripts/bootstrap.py`를 실행합니다.
   - 인터랙티브 위자드가 실행됩니다.
   - `.zshrc`, `.codex/config.toml`을 `~`에 링크합니다.
   - 비인터랙티브로 실행하려면 `./scripts/bootstrap.py link --all --mode backup`를 사용합니다.
3. 터미널을 다시 열거나 `source ~/.zshrc`로 설정을 반영합니다.

## Pre-commit
- `.zshrc`에 `/Users/<name>` 또는 `/home/<name>` 형태의 하드코딩된 home 경로가 들어가면 실패합니다.
- `$HOME`을 사용하도록 강제합니다.
- 설치 후 훅 등록:
  - `brew install pre-commit`
  - `pre-commit install`
