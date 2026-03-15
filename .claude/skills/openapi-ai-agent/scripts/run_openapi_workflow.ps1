param(
    [string]$BaseUrl,

    [string]$SpecSource,

    [string]$SwaggerUrl,

    [string]$Workspace = "."
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "run_openapi_workflow.py"

$candidates = @(
    (Join-Path (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path ".venv\Scripts\python.exe"),
    "python",
    "py"
)

$pythonExe = $null
foreach ($candidate in $candidates) {
    try {
        if ($candidate -like "*.exe" -and -not (Test-Path $candidate)) {
            continue
        }

        $versionOutput = & $candidate --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = $candidate
            break
        }
    } catch {
        continue
    }
}

if (-not $pythonExe) {
    Write-Error "No usable Python interpreter was found. Install Python 3.11+ or repair the project's .venv before running the OpenAPI workflow."
    exit 1
}

$arguments = @($pythonScript, "--workspace", $Workspace)
if ($BaseUrl) {
    $arguments += @("--base-url", $BaseUrl)
}
if ($SpecSource) {
    $arguments += @("--spec-source", $SpecSource)
}
if ($SwaggerUrl) {
    $arguments += @("--swagger-url", $SwaggerUrl)
}

if (-not $SpecSource -and -not $SwaggerUrl) {
    Write-Error "Provide either -SpecSource or -SwaggerUrl."
    exit 1
}

& $pythonExe @arguments
exit $LASTEXITCODE
