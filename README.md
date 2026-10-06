# KiCadScripts (gearchiveerd)

Deze repo is gearchiveerd en leeg gemaakt. De inhoud is geconsolideerd in
**[bom_tools](https://github.com/HermanGuijt/bom_tools)**, de centrale,
klant-onafhankelijke tools-repo:

- `kicad_pinmap_tool.py` → [bom_tools/kicad_pinmap_tool.py](https://github.com/HermanGuijt/bom_tools/blob/master/kicad_pinmap_tool.py)
- Eurocircuits-fabricageworkflow + script → [bom_tools/docs/kicad-naar-eurocircuits-fabricage.md](https://github.com/HermanGuijt/bom_tools/blob/master/docs/kicad-naar-eurocircuits-fabricage.md)
  en [bom_tools/Export-EurocircuitsFabricatie.ps1](https://github.com/HermanGuijt/bom_tools/blob/master/Export-EurocircuitsFabricatie.ps1)

Verwijderd (verouderd, niet meer nodig):
- `DART-6UL_grouped.kicad_sym` — symboolbibliotheek van een uiteindelijk niet
  gebruikte SOM.
- `kicad_bom_export.py` — legacy BOM/pricing-script, functioneel vervangen door
  `mouser_pricing.py`/`bom_config.py` in `bom_tools`.

Gebruik voortaan **bom_tools** voor nieuwe/bestaande KiCad-tooling.
