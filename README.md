# Settings

개인 macOS zsh 환경 설정을 담고 있는 저장소입니다.

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

## Pre-commit
- `.zshrc`에 `/Users/<name>` 또는 `/home/<name>` 형태의 하드코딩된 home 경로가 들어가면 실패합니다.
- `$HOME`을 사용하도록 강제합니다.
- 설치 후 훅 등록:
  - `brew install pre-commit`
  - `pre-commit install`
