<#
.SYNOPSIS
    Build a portable BiliDownTrans source release zip.
#>
[CmdletBinding()]
param(
    [string]$OutputDir = ".\release",
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist-portable"
$appDir = Join-Path $dist "BiliDownTrans"
$OutputDir = Join-Path $root $OutputDir
$zipPath = Join-Path $OutputDir "BiliDownTrans-v$Version-win-x64-portable.zip"

if (Test-Path -LiteralPath $dist) {
    Remove-Item -LiteralPath $dist -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $appDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$exclude = @(
    ".git",
    ".github",
    ".venv",
    "__pycache__",
    "build-release",
    "dist-portable",
    "release",
    "test"
)

Get-ChildItem -LiteralPath $root -Force | Where-Object {
    $exclude -notcontains $_.Name
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $appDir -Recurse -Force
}

Get-ChildItem -LiteralPath $appDir -Recurse -Force -Directory | Where-Object {
    $_.Name -in @("__pycache__", ".pytest_cache", ".ruff_cache")
} | Remove-Item -Recurse -Force

$cscCandidates = @(
    (Get-Command csc -ErrorAction SilentlyContinue).Source,
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)
$csc = $cscCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

if ($csc) {
    & $csc /nologo /target:winexe `
        "/win32icon:$(Join-Path $root 'assets\pipeline_icon.ico')" `
        "/out:$(Join-Path $appDir 'BiliDownTrans.exe')" `
        (Join-Path $root "launcher\BiliDownTransLauncher.cs")

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build BiliDownTrans.exe launcher"
    }
} else {
    Write-Warning "csc.exe not found; portable package will only include BiliDownTransLauncher.cmd"
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -LiteralPath $appDir -DestinationPath $zipPath -Force

$hashPath = Join-Path $OutputDir "SHA256SUMS.txt"
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath
"$($hash.Hash)  $(Split-Path -Leaf $zipPath)" | Set-Content -LiteralPath $hashPath -Encoding UTF8

Write-Host "Portable release: $zipPath"
Write-Host "SHA256: $hashPath"
