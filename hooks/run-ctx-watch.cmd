: << 'CMDBLOCK'
@echo off
REM ---------------------------------------------------------------------------
REM Polyglot launcher for ctx-watch.ps1.
REM
REM cmd.exe runs the batch section below. sh/bash skips it - the leading ':' is
REM a no-op command and the heredoc swallows everything up to CMDBLOCK - and
REM runs the POSIX section at the bottom instead. Claude Code may invoke a hook
REM command either way on Windows, so BOTH sections have to reach PowerShell;
REM a launcher that only worked under one interpreter would no-op silently
REM under the other, which is the worst possible failure for this hook.
REM
REM The file is stored with LF endings because the POSIX section requires them.
REM The batch section is therefore written without parenthesised blocks or
REM labels - those are the constructs cmd.exe mishandles in an LF-only file.
REM ---------------------------------------------------------------------------
set "HOOK_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%HOOK_DIR%ctx-watch.ps1" 2>nul
REM Always succeed. This hook is advisory, and a non-zero exit is surfaced to
REM the user as a hook failure. If PowerShell is somehow absent, the line above
REM fails silently and we still exit clean.
exit /b 0
CMDBLOCK

# POSIX section - also reached by Git Bash on Windows.
#
# Only Windows carries powershell.exe / pwsh.exe. Git Bash sets OS=Windows_NT;
# WSL and real POSIX hosts do not. Gating on that keeps this a no-op everywhere
# the .ps1 could not work anyway (it reads USERPROFILE and Windows paths), and
# avoids an every-turn error for anyone who installs the plugin on macOS or
# Linux.
if [ "$OS" = "Windows_NT" ]; then
  DIR="$(cd "$(dirname "$0")" && pwd)"
  for ps in powershell.exe pwsh.exe; do
    if command -v "$ps" >/dev/null 2>&1; then
      exec "$ps" -NoProfile -ExecutionPolicy Bypass -File "$DIR/ctx-watch.ps1"
    fi
  done
fi

# Nothing to run. Exit 0 with EMPTY stdout: on UserPromptSubmit any stdout at
# all is injected into the model's context as an instruction.
exit 0
