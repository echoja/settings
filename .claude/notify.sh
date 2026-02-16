#!/bin/bash

# 1. Ensure path includes Homebrew (for terminal-notifier / git)
export PATH=$PATH:/opt/homebrew/bin:/usr/local/bin

# 2. Get Git Info
toplevel=$(git rev-parse --show-toplevel 2>/dev/null)
repo=${toplevel:+$(basename "$toplevel")}
repo=${repo:-"Unknown Repo"}

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
branch=${branch:-"N/A"}

# 3. Detect Terminal App (VS Code, iTerm, or Terminal)
#    We default to "Visual Studio Code" if unknown.
app_name="Visual Studio Code"
if [[ "$TERM_PROGRAM" == "iTerm.app" ]]; then
    app_name="iTerm2"
elif [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    app_name="Terminal"
fi

# 4. Define the Click Action
#    This is the command that runs when you CLICK the notification.
#    It runs AppleScript to find the window matching the repo name and bring it to front.
apple_script="tell application \"$app_name\"
    activate
    try
        set index of (first window whose name contains \"$repo\") to 1
    end try
end tell"

# We wrap the AppleScript inside 'osascript' so it can run from the shell
click_cmd="osascript -e '$apple_script'"

# 5. Send Notification
#    -execute takes a shell command string. We pass our 'click_cmd' variable.
terminal-notifier \
    -title "$repo [$branch]" \
    -message "Claude Done ✨" \
    -sound default \
    -execute "$click_cmd"
