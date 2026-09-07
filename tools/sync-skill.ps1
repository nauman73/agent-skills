<#
.SYNOPSIS
    Copy one skill from a local skills directory into this repo's skills/ folder.

.DESCRIPTION
    The live skills directory is the single source of truth. This repo holds only
    the curated, publishable subset, so publishing is always an explicit act
    rather than a side effect of `git add -A`.

    Build residue (__pycache__, *.pyc) is never copied.

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

# A README written for this repo lives only here, so preserve it across syncs.
$existingReadme = Join-Path $to 'README.md'
$keptReadme     = $null
if (Test-Path -LiteralPath $existingReadme) {
    $keptReadme = Get-Content -LiteralPath $existingReadme -Raw
}

$didSync = $PSCmdlet.ShouldProcess($to, "replace with contents of $from")

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
}

if (-not $didSync) {
    # Test-Path is the wrong guard here: with -WhatIf over an existing copy the
    # folder is still there, and reporting a sync that did not happen is worse
    # than saying nothing.
    Write-Host "Nothing written (-WhatIf)." -ForegroundColor Yellow
    return
}

Write-Host "Synced '$Name' ->  skills\$Name" -ForegroundColor Green
Get-ChildItem -LiteralPath $to -Recurse -File |
    ForEach-Object { $_.FullName.Substring($repoRoot.Length + 1) } |
    Sort-Object
