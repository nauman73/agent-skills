<#
.SYNOPSIS
    Copy the live hooks folder into this repo's hooks/ folder.

.DESCRIPTION
    The live hooks directory (~/.claude/hooks) is the single source of truth,
    exactly as ~/.claude/skills is for skills. Edit there, run the tests there,
    then publish with this script. Never edit hooks\ in this repo - the next
    sync overwrites it without warning.

    What this syncs, and what it does not, follows from where each file runs:

      ctx-watch.ps1        runs locally AND in the plugin  -> synced
      run-ctx-watch.cmd    runs locally AND in the plugin  -> synced
      test-ctx-watch.ps1   sits beside the script in both  -> synced

      hooks.json           plugin wiring only. Locally the same job is done by
                           ~/.claude/settings.json, so there is no live copy
                           to sync from                     -> repo-owned
      README.md            written for this repo            -> repo-owned
      .syncignore          paths this repo must not publish -> repo-owned

    Repo-owned files are read before the destination is wiped and written back
    afterwards. Backups (*.bak*) and build residue are never copied - a backup
    left in the live folder must not become a published file.

    .syncignore holds one path per line, relative to hooks\, and is applied
    after the copy so it wins over whatever was just copied. Blank lines and
    lines starting with # are ignored. A listed path that does not exist after
    the copy is reported as a warning, since a typo there would publish the
    very file it was meant to withhold.

.PARAMETER Source
    Directory holding your live hooks. Defaults to $env:USERPROFILE\.claude\hooks.

.PARAMETER Check
    Report drift between the live folder and this repo without writing
    anything. Use it to catch the mistake this whole convention exists to
    prevent: editing the repo copy instead of the live one.

.PARAMETER WhatIf
    Show what would be copied without writing anything.

.EXAMPLE
    ./tools/sync-hook.ps1 -Check

.EXAMPLE
    ./tools/sync-hook.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $Source = (Join-Path $env:USERPROFILE '.claude\hooks'),

    [switch] $Check
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$to       = Join-Path $repoRoot 'hooks'

# Written for this repo, with no counterpart in the live folder.
$repoOwned = @('hooks.json', 'README.md', '.syncignore')

# Never published, whatever the live folder happens to contain.
$excluded = @('*.bak', '*.bak-*', '*.pyc')

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Live hooks folder not found: $Source"
}

function Get-SyncableFiles {
    param([string] $Root)
    Get-ChildItem -LiteralPath $Root -File -Force |
        Where-Object {
            $name = $_.Name
            if ($repoOwned -contains $name) { return $false }
            foreach ($pattern in $excluded) { if ($name -like $pattern) { return $false } }
            return $true
        }
}

$sourceFiles = @(Get-SyncableFiles -Root $Source)
if ($sourceFiles.Count -eq 0) {
    throw "Nothing to sync: $Source holds no publishable files."
}

# ---- drift check --------------------------------------------------------
if ($Check) {
    $drift = 0
    Write-Host "Live:  $Source"
    Write-Host "Repo:  $to`n"

    foreach ($f in $sourceFiles) {
        $mirror = Join-Path $to $f.Name
        if (-not (Test-Path -LiteralPath $mirror)) {
            Write-Host "  MISSING IN REPO  $($f.Name)" -ForegroundColor Yellow
            $drift++
            continue
        }
        $a = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
        $b = (Get-FileHash -LiteralPath $mirror     -Algorithm SHA256).Hash
        if ($a -eq $b) {
            Write-Host "  same             $($f.Name)" -ForegroundColor DarkGray
        }
        else {
            Write-Host "  DIFFERS          $($f.Name)" -ForegroundColor Red
            $drift++
        }
    }

    # A repo file with no live counterpart is either repo-owned or a leftover.
    if (Test-Path -LiteralPath $to) {
        $liveNames = $sourceFiles.Name
        foreach ($f in (Get-ChildItem -LiteralPath $to -File -Force)) {
            if ($repoOwned -contains $f.Name) {
                Write-Host "  repo-owned       $($f.Name)" -ForegroundColor DarkGray
            }
            elseif ($liveNames -notcontains $f.Name) {
                Write-Host "  STALE IN REPO    $($f.Name) - no live counterpart" -ForegroundColor Yellow
                $drift++
            }
        }
    }

    Write-Host ""
    if ($drift -eq 0) { Write-Host "In sync." -ForegroundColor Green }
    else { Write-Host "$drift file(s) out of sync - run ./tools/sync-hook.ps1" -ForegroundColor Yellow }
    return
}

# ---- sync ---------------------------------------------------------------
$kept = @{}
foreach ($name in $repoOwned) {
    $p = Join-Path $to $name
    if (Test-Path -LiteralPath $p) { $kept[$name] = Get-Content -LiteralPath $p -Raw }
}

if (-not $PSCmdlet.ShouldProcess($to, "replace with publishable contents of $Source")) {
    # Test-Path is the wrong guard here: with -WhatIf over an existing copy the
    # folder is still there, and reporting a sync that did not happen is worse
    # than saying nothing.
    Write-Host "Nothing written (-WhatIf). Would copy:" -ForegroundColor Yellow
    $sourceFiles | ForEach-Object { Write-Host "  $($_.Name)" -ForegroundColor Yellow }
    return
}

if (Test-Path -LiteralPath $to) { Remove-Item -LiteralPath $to -Recurse -Force }
New-Item -ItemType Directory -Path $to -Force | Out-Null

foreach ($f in $sourceFiles) {
    Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $to $f.Name) -Force
}

foreach ($name in $kept.Keys) {
    Set-Content -LiteralPath (Join-Path $to $name) -Value $kept[$name] -NoNewline
}

$removed = @()
$missing = @()
if ($kept.ContainsKey('.syncignore')) {
    # Applied last, so the exclusions win over whatever was just copied.
    foreach ($line in ($kept['.syncignore'] -split "`r?`n")) {
        $entry = $line.Trim()
        if ($entry -eq '' -or $entry.StartsWith('#')) { continue }

        $target = Join-Path $to ($entry -replace '/', '\')
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Recurse -Force
            $removed += $entry
        }
        else {
            $missing += $entry
        }
    }
}

Write-Host "Synced hooks  ->  hooks\" -ForegroundColor Green

if ($removed.Count -gt 0) {
    Write-Host "Excluded by .syncignore:" -ForegroundColor Cyan
    $removed | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
}
if ($missing.Count -gt 0) {
    Write-Host "WARNING - listed in .syncignore but not present after the copy:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Write-Host "  Check for a typo: a path that does not match publishes the file it was meant to withhold." -ForegroundColor Yellow
}

Get-ChildItem -LiteralPath $to -File -Force |
    ForEach-Object { $_.FullName.Substring($repoRoot.Length + 1) } |
    Sort-Object
