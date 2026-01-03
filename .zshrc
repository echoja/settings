
# Kiro CLI pre block. Keep at the top of this file.
[[ -f "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.pre.zsh" ]] && builtin source "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.pre.zsh"

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi



eval "$(/opt/homebrew/bin/brew shellenv)"



# If you come from bash you might have to change your $PATH.
export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH

# Path to your Oh My Zsh installation.
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="powerlevel10k/powerlevel10k"

if [[ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k" ]]; then
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
      "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"
fi

if [[ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting" ]]; then
    git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git \
      "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting"
fi

plugins=(git zsh-syntax-highlighting)

source $ZSH/oh-my-zsh.sh


# fzf
# brew install fzf
source <(fzf --zsh)




# direnv
eval "$(direnv hook zsh)"



# 기본 PATH
export PATH="$PATH:/opt/homebrew/opt/ruby/bin:$HOME/bin:$HOME/.yarn/bin:$HOME/.local/bin:$HOME/Library/Android/sdk/platform-tools:/Applications/Visual Studio Code.app/Contents/Resources/app/bin:/Applications"

# go (https://go.dev/doc/install)
export PATH="/usr/local/go/bin:$(go env GOPATH)/bin:$PATH"

# ##############################################################################
# ######## 사용자정의 alias 또는 function 추가 #################################
# ##############################################################################

# asdf
export PATH="${ASDF_DATA_DIR:-$HOME/.asdf}/shims:$PATH"
# append completions to fpath
fpath=(${ASDF_DATA_DIR:-$HOME/.asdf}/completions $fpath)
# initialise completions with ZSH's compinit
autoload -Uz compinit && compinit


# vscode shell integration
[[ "$TERM_PROGRAM" == "vscode" ]] && . "$(code --locate-shell-integration-path zsh)"

# aws with purple io
export AWS_PROFILE=purpleio-dev
export AWS_REGION=ap-northeast-2

# cinesopa
alias ssh-cinesopa="ssh -i ~/LightsailDefaultKey-ap-northeast-ezkorry.pem bitnami@13.209.62.19"
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH=`which chromium`

alias e="exit"

# python
alias py="python3"
alias python="python3"
alias pip="pip3"

# kubectl
# https://kubernetes.io/docs/tasks/tools/
alias k="kubectl"

# brew install kubectx
alias kx="kubectx"

# pnpm
# https://pnpm.io/installation
alias p="pnpm"

# curl 대안
# brew install curlie
alias c="curlie"

# codex
# brew install codex
alias cdx="codex -m gpt-5.2-codex -c model_reasoning_effort=xhigh --enable web_search_request"

# source
alias s="source ~/.zshrc"

# .zshrc vim으로 열기
alias vz="vim ~/.zshrc"

# .zshrc Visual Studio Code로 열기
alias cz="code ~/settings"

# skim 기본 명령어 변경
# brew install sk
export SKIM_DEFAULT_COMMAND="fd --type f || git ls-tree -r --name-only HEAD || rg --files || find ."

# brew tap hashicorp/tap
# brew install hashicorp/tap/terraform
alias tf="terraform"

# mysql
export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"

# ls 더 나은 버전
# brew install eza
# alias ls="eza"

# remove header - 헤더 행을 삭제합니다.
# alias rh="gtail -n +2"

# nvim
# brew install neovim
export LC_MESSAGES="en_US.UTF-8"
alias vim="nvim"
alias vi="nvim"

# brew install television 텍스트 fuzzy search
alias tt="tv text"
# eval "$(tv init zsh)"

# zoxide: cd 더 나은 버전
# brew install zoxide
eval "$(zoxide init zsh)"

### git
# git origin 에 있는 main을 그대로 가져오기
function gfm() {
  git fetch origin $(git_main_branch):$(git_main_branch)
}
# git origin 에 있는 최신 deploy 브랜치를 그대로 가져오기
function gfdp() {
  local target_branch=$(git branch --sort=-committerdate | grep '^  deploy' | head -n 1 | sed 's/^  //')
  echo "$target_branch 를 가져옵니다."
  git fetch origin $target_branch:$target_branch
}

# git pull
function glm() {
  echo 'git pull origin $(git_main_branch) --no-rebase --no-edit' && git pull origin $(git_main_branch) --no-rebase --no-edit
}

function glr() {
  echo 'git pull origin $(git_main_branch) --rebase --no-edit' && git pull origin $(git_main_branch) --rebase --no-edit
}

# git pull origin ${branch} --no-rebase --no-edit
# function glone() {
#   echo 'git pull origin $1 --no-rebase --no-edit' && git pull origin $1 --no-rebase --no-edit
# }
alias glone="git pull origin --no-rebase --no-edit"

function gcne() {
  echo 'git commit -v --amend --no-edit' && git commit -v --amend --no-edit
}

function gbrename() {
  echo 'git branch -m $(git_current_branch) $1' && git branch -m $(git_current_branch) $1
}

# git switch
function gs() {
  git branch | sk | xargs -I {} git switch {}
}

# go to git root
function cdgr() {
  cd $(git rev-parse --show-toplevel)
}

# KOLON 인증서 관련
alias addcert="yarn config set cafile $HOME/KOLON.crt --global; npm config set cafile $HOME/KOLON.crt --global"
alias delcert="yarn config delete cafile --global ; npm config --location=global delete cafile ; npm config delete cafile ; yarn config delete cafile"


# 포트 종료
function killport {
    readonly port=${1:?"The port must be specified."}
    readonly head=$(lsof -i tcp:"$port" | head -n 1)
    readonly gl=$(lsof -i tcp:"$port" | rg LISTEN)
    echo $head
    echo $gl
    echo $gl | choose 1 | xargs kill -9
}
 
alias killnode="ps -e | rg /bin/node | choose 0 | xargs kill -9"

# pnpm  
# export PNPM_HOME="$HOME/Library/pnpm"
# export PATH="$PNPM_HOME:$PATH"

# postgresql
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
export PKG_CONFIG_PATH="/opt/homebrew/opt/libpq/lib/pkgconfig"

# gpg
export GPG_TTY=$(tty)

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh


# Added by Windsurf
export PATH="$HOME/.codeium/windsurf/bin:$PATH"



# pnpm
export PNPM_HOME="$HOME/Library/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end

# bun completions
[ -s "$HOME/.bun/_bun" ] && source "$HOME/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"


# Added by Antigravity
export PATH="$HOME/.antigravity/antigravity/bin:$PATH"


# Kiro CLI post block. Keep at the bottom of this file.
[[ -f "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.post.zsh" ]] && builtin source "${HOME}/Library/Application Support/kiro-cli/shell/zshrc.post.zsh"
