<#
.SYNOPSIS
    Genereert complete Eurocircuits-fabricagebestanden uit een KiCad 9 PCB-project:
    Gerbers (X2, met job file), Excellon drill (PTH/NPTH apart + maps), optioneel
    pick&place, en een zip met het native KiCad-project als alternatieve upload.

.DESCRIPTION
    Vastgelegde werkwijze: zie docs/kicad-naar-eurocircuits-fabricage.md in deze
    repository voor de achtergrond, bekende valkuilen en de redenering achter de
    gekozen kicad-cli-aanroepen (met name de 2-staps Gerber-export).

.PARAMETER PcbPath
    Volledig pad naar het .kicad_pcb-bestand.

.PARAMETER KicadCliPath
    Pad naar kicad-cli.exe. Standaard: KiCad 9.0 standaardinstallatiepad.

.PARAMETER IncludePosFile
    Genereer ook een pick&place (.pos) bestand — nodig als Eurocircuits ook de
    assembly verzorgt.

.PARAMETER SkipDrc
    Sla de DRC-controle voorafgaand aan het genereren over (niet aanbevolen).

.EXAMPLE
    .\Export-EurocircuitsFabricatie.ps1 -PcbPath "C:\projects\MijnBord\MijnBord.kicad_pcb" -IncludePosFile
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PcbPath,

    [string]$KicadCliPath = "C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",

    [switch]$IncludePosFile,

    [switch]$SkipDrc
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KicadCliPath)) {
    throw "kicad-cli.exe niet gevonden op '$KicadCliPath'. Geef -KicadCliPath mee."
}
if (-not (Test-Path $PcbPath)) {
    throw "PCB-bestand niet gevonden: $PcbPath"
}

$PcbPath     = (Resolve-Path $PcbPath).Path
$ProjectDir  = Split-Path $PcbPath -Parent
$ProjectName = [System.IO.Path]::GetFileNameWithoutExtension($PcbPath)
$ProPath     = Join-Path $ProjectDir "$ProjectName.kicad_pro"
$Date        = Get-Date -Format "yyyyMMdd"

$FabDir      = Join-Path $ProjectDir "fabrication"
$GerberDir   = Join-Path $FabDir "gerbers"
$DrillDir    = Join-Path $FabDir "drill"
$NativeDir   = Join-Path $FabDir "native_kicad_project"

Write-Host "=== Eurocircuits-fabricatie export: $ProjectName ===" -ForegroundColor Cyan

# --- 1. Voorcontrole: git-status en DRC (uitgevoerd in de projectmap zelf,
#        zodat relatieve fp-lib-table/sym-lib-table-paden kloppen) ------------
Push-Location $ProjectDir
try {
    $gitRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0) {
        $gitStatus = git status --porcelain
        if ($gitStatus) {
            Write-Warning "Git working tree is NIET schoon. Overweeg eerst te committen/stashen:"
            Write-Host $gitStatus
        } else {
            Write-Host "Git working tree is schoon." -ForegroundColor Green
        }
    }

    New-Item -ItemType Directory -Force -Path $FabDir, $GerberDir, $DrillDir, $NativeDir | Out-Null

    if (-not $SkipDrc) {
        Write-Host "`n--- DRC-controle (respecteert project-exclusions/severities) ---"
        & $KicadCliPath pcb drc --output (Join-Path $FabDir "DRC_report.rpt") --format report $PcbPath
        Select-String -Path (Join-Path $FabDir "DRC_report.rpt") -Pattern "Found \d+ DRC" | ForEach-Object { Write-Host $_.Line }
        Write-Host "Zie $FabDir\DRC_report.rpt voor details." -ForegroundColor Yellow
    }

    # --- 2. Gerbers: TWEE aanroepen (zie docs, dit is bewust) -----------------
    Write-Host "`n--- Gerbers: stap 1/2 (volledige laag-lijst incl. paste) ---"
    & $KicadCliPath pcb export gerbers --output "$GerberDir\" `
        --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" `
        $PcbPath

    Write-Host "`n--- Gerbers: stap 2/2 (board-plot-params, genereert .gbrjob) ---"
    & $KicadCliPath pcb export gerbers --output "$GerberDir\" --board-plot-params $PcbPath

    # --- 3. Drill files (PTH/NPTH apart + maps) -------------------------------
    Write-Host "`n--- Drill files ---"
    & $KicadCliPath pcb export drill --output "$DrillDir\" `
        --format excellon --excellon-units mm --excellon-separate-th `
        --generate-map --map-format pdf `
        $PcbPath

    # --- 4. Pick & place (optioneel) ------------------------------------------
    if ($IncludePosFile) {
        Write-Host "`n--- Pick & place ---"
        & $KicadCliPath pcb export pos --output (Join-Path $FabDir "$ProjectName-pos.csv") `
            --format csv --units mm --side both --use-drill-file-origin `
            $PcbPath
    }

    # --- 5. Native KiCad-project (aanbevolen upload bij Eurocircuits) ---------
    Write-Host "`n--- Native KiCad-project kopiëren ---"
    Copy-Item $PcbPath $NativeDir -Force
    if (Test-Path $ProPath) {
        Copy-Item $ProPath $NativeDir -Force
    } else {
        Write-Warning "Geen .kicad_pro gevonden naast het board-bestand; alleen .kicad_pcb meegenomen."
    }

    # --- 6. Zippen -------------------------------------------------------------
    Write-Host "`n--- Zip-bestanden bouwen ---"
    $gerberZip = Join-Path $FabDir "${ProjectName}_Eurocircuits_$Date.zip"
    $nativeZip = Join-Path $FabDir "${ProjectName}_NativeKiCad_$Date.zip"
    Compress-Archive -Path "$GerberDir\*", "$DrillDir\*" -DestinationPath $gerberZip -Force
    Compress-Archive -Path "$NativeDir\*" -DestinationPath $nativeZip -Force

    Write-Host "`n=== Klaar ===" -ForegroundColor Green
    Write-Host "Gerber/drill-zip : $gerberZip"
    Write-Host "Native KiCad-zip : $nativeZip (AANBEVOLEN upload bij Eurocircuits, zie docs §3.1)"
}
finally {
    Pop-Location
}
