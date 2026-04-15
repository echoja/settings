# Settings

개인 macOS zsh 환경 설정을 담고 있는 저장소입니다.

## 남은 할 일

- TODO.md 파일 참조

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 사용 방법

```sh
$ ./scripts/bootstrap.py --help
```

### Quick verify

`./v` 는 `./scripts/bootstrap.py verify` 의 shortcut 입니다. 환경 설정이 올바른지 빠르게 확인할 때 사용합니다.

```sh
$ ./v
```

## Manual install steps

Some dependencies require `sudo` or interactive setup and cannot be automated by the bootstrap script.

```sh
# Go (official installer)
curl -fSL -o /tmp/go.pkg https://go.dev/dl/go1.26.0.darwin-arm64.pkg
sudo installer -pkg /tmp/go.pkg -target /

# Zoom
brew install --cask zoom

# RunCat (App Store only, no brew cask)
mas install 1429033973

# Remote Login (SSH)
sudo systemsetup -f -setremotelogin on

# Screen Sharing
sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist

# Auto restart after power loss (for headless/SSH access)
sudo pmset -a autorestart 1

# Disable FileVault (prevents pre-boot password prompt blocking SSH after power loss)
sudo fdesetup disable

# Auto-login (skip login screen after boot so SSH is immediately available)
sudo defaults write /Library/Preferences/com.apple.loginwindow autoLoginUser echoja

# VS Code Settings Sync (built-in, requires interactive sign-in)
# Open VS Code → Cmd+Shift+P → "Settings Sync: Turn On..."
```

## Container runtime

이 맥의 컨테이너 런타임은 **Docker Desktop** 입니다 (DMG 직접 설치; `scripts/deps.json`의 `docker` 엔트리 참조). Apple Silicon에서 amd64 이미지를 돌리기 위해 Rosetta 2도 함께 설치해 둡니다.

### 의도적으로 쓰지 않는 것들

- **Podman (`podman machine`)** — krunkit VM이 `cpuset` cgroup을 delegate 하지 않아 k3d/k3s가 bootstrap 단계에서 `fatal: failed to find cpuset cgroup (v2)`로 죽습니다. Kind는 돌지만 생태계 전반의 호환성이 떨어져 제외했습니다.
- **Colima** — Docker Desktop이 같은 워크로드를 first-party로 처리해 별도 VM 매니저가 필요 없습니다. "대시보드를 띄우지 않는 진짜 헤드리스" 용도일 땐 고려 대상이지만, 현재는 불필요.
- **Lima 직접 사용** — Colima/Rancher Desktop이 상위 래퍼로 충분.
- **`brew install --cask docker`** — 공식 `.dmg` 채널이 최신 빌드이며 Docker 측 권장 경로입니다.
- **`brew install k3d`의 실제 cluster 생성** — k3d 바이너리는 설치돼 있어도 (관성) Podman 기반에서는 위의 cgroup 이슈로 동작 불가. Docker Desktop으로 전환한 지금은 사용 가능합니다.

## Pre-commit

- `.zshrc`에 `/Users/<name>` 또는 `/home/<name>` 형태의 하드코딩된 home 경로가 들어가면 실패합니다.
- `$HOME`을 사용하도록 강제합니다.
- 설치 후 훅 등록:
  - `brew install pre-commit`
  - `pre-commit install`
