# KiCadScripts

Herbruikbare scripts en workflow-documentatie voor het werken met KiCad-projecten,
projectoverstijgend bruikbaar (iMC_vX en andere PCB-projecten).

## Inhoud

### Documentatie

- **[docs/kicad-naar-eurocircuits-fabricage.md](docs/kicad-naar-eurocircuits-fabricage.md)**
  — Complete workflow van afgerond KiCad-ontwerp tot fabricage-order bij
  Eurocircuits: voorcontrole (git/DRC), genereren van Gerbers/drill-bestanden,
  bekende valkuilen (laagvolgorde-verwarring, NPTH-restring-meldingen),
  stencil-diktebepaling (IPC-7525 Area Ratio), en de git tag/release-conventie
  voor het vastleggen van bestellingen. **Begin hier** bij een nieuwe
  Eurocircuits-order.

### Scripts

- **[scripts/Export-EurocircuitsFabricatie.ps1](scripts/Export-EurocircuitsFabricatie.ps1)**
  — PowerShell-script dat de volledige fabricage-export automatiseert
  (Gerbers, drill, optioneel pick&place, native KiCad-projectzip). Implementeert
  de stappen uit bovenstaande documentatie.

  ```powershell
  .\scripts\Export-EurocircuitsFabricatie.ps1 -PcbPath "C:\projects\MijnBord\MijnBord.kicad_pcb" -IncludePosFile
  ```

- **[kicad_bom_export.py](kicad_bom_export.py)** — BOM-export met
  prijsberekening op basis van MOQ-staffels.
- **[kicad_pinmap_tool.py](kicad_pinmap_tool.py)** — Pinmap-hulpmiddel.

## Vereisten

- KiCad 9.0 (`kicad-cli.exe`), standaard verwacht op
  `C:\Program Files\KiCad\9.0\bin\kicad-cli.exe`.
- PowerShell (voor de `.ps1`-scripts) / Python 3 (voor de `.py`-scripts).
