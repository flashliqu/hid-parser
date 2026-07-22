param(
    [ValidateSet("win-x64", "win-arm64")]
    [string]$Runtime = "win-x64",

    [switch]$FrameworkDependent
)

$ErrorActionPreference = "Stop"

$project = Join-Path $PSScriptRoot "HidDescriptorDecoder\HidDescriptorDecoder.csproj"
$output = Join-Path $PSScriptRoot "..\artifacts\$Runtime"
$selfContained = if ($FrameworkDependent) { "false" } else { "true" }

dotnet publish $project `
    --configuration Release `
    --runtime $Runtime `
    --self-contained $selfContained `
    -p:PublishSingleFile=true `
    -p:DebugType=None `
    -p:DebugSymbols=false `
    --output $output

if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE"
}

Write-Host "Windows app published to $output"
