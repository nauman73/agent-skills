<#
.SYNOPSIS
    Copy one skill from a local skills directory into this repo's skills/ folder.

.DESCRIPTION
    The live skills directory is the single source of truth. This repo holds only
    the curated, publishable subset, so publishing is always an explicit act
    rather than a side effect of `git add -A`.

    Build residue (__pycache__, *.pyc) is never copied.

    Two files are owned by this repo rather than by the source folder, and are
    preserved across a sync:

      skills\<name>\README.md     human-facing notes written for this repo
      skills\<name>\.syncignore   paths this repo must NOT publish

    .syncignore holds one path per line, relative to the skill folder, and is
    applied after the copy. Blank lines and lines starting with # are ignored.
    Use it when a skill ships something that belongs in one repo but not another
    - an employer-specific convention file, say. A listed path that does not
    exist after the copy is reported as a warning, since a silent typo there
    would publish the very file it was meant to withhold.

.PARAMETER Name
    Skill folder name, e.g. session-handoff.

.PARAMETER Source
    Directory holding your skills. Defaults to $env:USERPROFILE\.claude\skills.

.PARAMETER WhatIf
    Show what would be copied without writing anything.

.EXAMPLE
    ./tools/sync-skill.ps1 -Name session-handoff

.EXAMPLE
    ./tools/sync-skill.ps1 -Name session-handoff -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string] $Name,

    [string] $Source = (Join-Path $env:USERPROFILE '.claude\skills')
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$from     = Join-Path $Source $Name
$to       = Join-Path $repoRoot "skills\$Name"

if (-not (Test-Path -LiteralPath $from -PathType Container)) {
    throw "Skill not found: $from"
}
if (-not (Test-Path -LiteralPath (Join-Path $from 'SKILL.md'))) {
    throw "No SKILL.md in $from - that is not a skill folder."
}

# These two files are written for this repo and live only here, so preserve them
# across syncs. Read them before the destination is wiped.
$existingReadme = Join-Path $to 'README.md'
$keptReadme     = $null
if (Test-Path -LiteralPath $existingReadme) {
    $keptReadme = Get-Content -LiteralPath $existingReadme -Raw
}

$existingIgnore = Join-Path $to '.syncignore'
$keptIgnore     = $null
if (Test-Path -LiteralPath $existingIgnore) {
    $keptIgnore = Get-Content -LiteralPath $existingIgnore -Raw
}

$didSync  = $PSCmdlet.ShouldProcess($to, "replace with contents of $from")
$excluded = @()
$missing  = @()

if ($didSync) {
    if (Test-Path -LiteralPath $to) {
        Remove-Item -LiteralPath $to -Recurse -Force
    }
    New-Item -ItemType Directory -Path $to -Force | Out-Null

    # Trailing \* copies the CONTENTS of $from, preserving subfolders such as
    # scripts\. Without it, Copy-Item nests the folder inside $to.
    Copy-Item -Path (Join-Path $from '*') -Destination $to -Recurse -Force

    # Prune build residue after the copy: -Exclude is unreliable with -Recurse
    # and does not prune directories at all.
    Get-ChildItem -LiteralPath $to -Recurse -Force -Directory -Filter '__pycache__' |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $to -Recurse -Force -File -Filter '*.pyc' |
        Remove-Item -Force

    if ($null -ne $keptReadme) {
        Set-Content -LiteralPath $existingReadme -Value $keptReadme -NoNewline
    }
    if ($null -ne $keptIgnore) {
        Set-Content -LiteralPath $existingIgnore -Value $keptIgnore -NoNewline

        # Apply the exclusions last, so they win over whatever was just copied.
        foreach ($line in ($keptIgnore -split "`r?`n")) {
            $entry = $line.Trim()
            if ($entry -eq '' -or $entry.StartsWith('#')) { continue }

            $target = Join-Path $to ($entry -replace '/', '\')
            if (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Recurse -Force
                $excluded += $entry
            }
            else {
                $missing += $entry
            }
        }
    }
}

if (-not $didSync) {
    # Test-Path is the wrong guard here: with -WhatIf over an existing copy the
    # folder is still there, and reporting a sync that did not happen is worse
    # than saying nothing.
    Write-Host "Nothing written (-WhatIf)." -ForegroundColor Yellow
    return
}

Write-Host "Synced '$Name' ->  skills\$Name" -ForegroundColor Green

if ($excluded.Count -gt 0) {
    Write-Host "Excluded by .syncignore:" -ForegroundColor Cyan
    $excluded | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
}
if ($missing.Count -gt 0) {
    Write-Host "WARNING - listed in .syncignore but not present after the copy:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Write-Host "  Check for a typo: a path that does not match publishes the file it was meant to withhold." -ForegroundColor Yellow
}

Get-ChildItem -LiteralPath $to -Recurse -File |
    ForEach-Object { $_.FullName.Substring($repoRoot.Length + 1) } |
    Sort-Object
