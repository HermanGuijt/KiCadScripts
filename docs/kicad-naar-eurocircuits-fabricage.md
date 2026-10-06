# Workflow: van KiCad-ontwerp naar Eurocircuits-bestelling

Deze workflow legt stap voor stap vast hoe je vanuit een afgerond KiCad PCB-ontwerp
komt tot een correcte, complete fabricage-order bij Eurocircuits (PCB + eventueel
stencil), inclusief de valkuilen die we onderweg zijn tegengekomen en hoe je ze
voorkomt of herkent. Gebruik dit document als checklist bij élk nieuw project
(iMC_vX of anders) dat bij Eurocircuits wordt besteld.

Bijbehorend herbruikbaar script: [`scripts/Export-EurocircuitsFabricatie.ps1`](../scripts/Export-EurocircuitsFabricatie.ps1).

> Herkomst: deze workflow is vastgelegd n.a.v. de Processor Module V0.2-bestelling
> (iMC_vX, oktober 2026) — zie commit/tag `v0.2-PCBA-Order-EmbedTech_iMC_vX_Processor_Module_V02`
> in [iMC_vX_Processor_Module_PCBA](https://github.com/HermanGuijt/iMC_vX_Processor_Module_PCBA).

## Overzicht van de stappen

1. [Voorcontrole: git-status en DRC](#1-voorcontrole-git-status-en-drc)
2. [Fabricagebestanden genereren met kicad-cli](#2-fabricagebestanden-genereren-met-kicad-cli)
3. [Bekende valkuilen bij Eurocircuits](#3-bekende-valkuilen-bij-eurocircuits)
4. [Stencil-dikte bepalen](#4-stencil-dikte-bepalen)
5. [Vastleggen in git: commit, tag en release](#5-vastleggen-in-git-commit-tag-en-release)

---

## 1. Voorcontrole: git-status en DRC

Voordat je iets genereert:

```powershell
git status                 # moet "nothing to commit, working tree clean" zijn
git log -1 --oneline        # noteer de laatste commit-hash, dit is je referentie
```

Draai daarna een verse DRC-check **in-place** (dus niet op een gekopieerd bestand in
een andere map — de `fp-lib-table`/`sym-lib-table` zijn relatief aan de projectmap,
en een kopie elders geeft valse `lib_footprint_issues`-meldingen):

```powershell
& "C:\Program Files\KiCad\9.0\bin\kicad-cli.exe" pcb drc `
  --output "fabrication\DRC_report.rpt" --format report `
  "<project>.kicad_pcb"
```

**Let op:** dit commando respecteert de per-violation "exclusions" die in de
`.kicad_pro` staan (`drc_exclusions`, gekoppeld aan object-UUID's) én de globale
`rule_severities` (bv. een regel op `"ignore"` gezet). Gebruik **`--severity-all`**
alleen om een volledig beeld te krijgen inclusief uitgesloten/genegeerde items —
niet als basis voor de uiteindelijke beoordeling, want dat forceert ook severities
die het project bewust op "ignore" heeft staan.

⚠️ **Valkuil: een pad bewerken breekt soms een bestaande DRC-exclusie.** Exclusies
worden deels gematcht op een herberekende markerpositie. Als je een pad wijzigt
(zoals in §3 hieronder), kan een *al eerder bekeken en geaccepteerde* violation
plotseling weer "actief" lijken. Controleer dit met een side-by-side vergelijking
(`git stash` / `git stash pop` rondom een proef-DRC-run) voordat je concludeert dat
er een nieuw probleem is. Zo niet: gewoon opnieuw uitsluiten in de KiCad-GUI
(rechtsklik op de violation → *Exclude this violation*).

---

## 2. Fabricagebestanden genereren met kicad-cli

Gebruik `kicad-cli` (KiCad 9, `C:\Program Files\KiCad\9.0\bin\kicad-cli.exe`) in
plaats van de GUI-plotdialoog: reproduceerbaar, geen vergeten instellingen, en
scriptbaar. Zie het kant-en-klare script
[`Export-EurocircuitsFabricatie.ps1`](../scripts/Export-EurocircuitsFabricatie.ps1)
voor een uitvoerbare versie van onderstaande stappen.

### 2.1 Gerbers (twee stappen — belangrijk!)

```powershell
# Stap 1: expliciete laag-lijst (zorgt dat Paste-lagen worden meegenomen)
kicad-cli pcb export gerbers --output "fabrication\gerbers\" `
  --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" `
  "<project>.kicad_pcb"

# Stap 2: met --board-plot-params (gebruikt de in het bord opgeslagen
# pcbplotparams, en genereert daarbij het Gerber X2 Job File .gbrjob)
kicad-cli pcb export gerbers --output "fabrication\gerbers\" `
  --board-plot-params "<project>.kicad_pcb"
```

Waarom twee stappen: `--layers` en `--board-plot-params` combineren in één aanroep
werkt niet betrouwbaar (de board-opgeslagen laagselectie kan de expliciete lijst
overschrijven, waardoor Paste-lagen of het job-bestand ontbreken). Door beide
los te draaien krijg je altijd een compleet setje **en** het `.gbrjob`-bestand.

### 2.2 Boorbestanden

```powershell
kicad-cli pcb export drill --output "fabrication\drill\" `
  --format excellon --excellon-units mm --excellon-separate-th `
  --generate-map --map-format pdf `
  "<project>.kicad_pcb"
```

`--excellon-separate-th` geeft aparte PTH/NPTH-bestanden zoals Eurocircuits
verwacht.

### 2.3 Pick & place (alleen nodig bij assembly-order)

```powershell
kicad-cli pcb export pos --output "fabrication\<project>-pos.csv" `
  --format csv --units mm --side both --use-drill-file-origin `
  "<project>.kicad_pcb"
```

### 2.4 Native KiCad-project (aanbevolen upload-formaat, zie §3)

```powershell
Copy-Item "<project>.kicad_pcb","<project>.kicad_pro" "fabrication\native_kicad_project\"
Compress-Archive -Path "fabrication\native_kicad_project\*" `
  -DestinationPath "fabrication\<project>_NativeKiCad_<datum>.zip" -Force
```

### 2.5 Gerber/drill-zip

```powershell
Compress-Archive -Path "fabrication\gerbers\*","fabrication\drill\*" `
  -DestinationPath "fabrication\<project>_Eurocircuits_<datum>.zip" -Force
```

De `fabrication\`-map hoort in `.gitignore` (genereerbare output, niet versiebeheren).

---

## 3. Bekende valkuilen bij Eurocircuits

### 3.1 Laagvolgorde lijkt verwisseld bij custom binnenlaag-namen

**Symptoom:** als binnenlagen een eigen naam hebben (bv. "GND"/"VCC" i.p.v.
"In1.Cu"/"In2.Cu"), kan Eurocircuits' automatische Gerber-laagherkenning in de war
raken en lagen in de verkeerde volgorde tonen (top↔bottom verwisseld, binnenlagen
geshift). Dit is een **bekend KiCad/Eurocircuits-probleem**, geen fout in het
ontwerp — zie [KiCad-forumdraad](https://forum.kicad.info/t/eurocircuits-top-and-bottom-layers-swapped-when-uploading-gerber-set-from-kicad-project/50171).

**Oplossing (in volgorde van voorkeur):**
1. **Upload het native KiCad-project** (§2.4) in plaats van Gerbers — Eurocircuits
   leest dan je echte stackup rechtstreeks in, zonder interpretatiestap.
   Eurocircuits zelf geeft aan native CAD-formaten te verkiezen boven Gerbers.
2. Als Gerbers toch nodig zijn: controleer het `.gbrjob`-bestand (`FilesAttributes`
   → `FileFunction`) voor de onbetwistbaar correcte laagvolgorde, en corrigeer
   de laagtoewijzing handmatig in Eurocircuits' upload-tool (ze bieden hiervoor
   een laag-editor) als de auto-detectie het fout doet.
3. Controleer of je KiCad-versie geen *nightly/.99*-build is — Eurocircuits
   weigert soms dat soort projectbestanden.

### 3.2 "Restring op binnenlagen (IAR) = 0,000 mm" bij montagegaten

**Oorzaak:** footprints met niet-geplateerde montagegaten (NPTH, bv. connector-
bevestigingspennen) hebben soms per ongeluk `*.Cu` in hun pad-laagtoewijzing,
terwijl padgrootte = boordiameter (bedoeld: 0 mm ring, want niet geplateerd).
Dat genereert een zinloze 0-breedte koperflits op alle koperlagen inclusief de
binnenlagen, wat Eurocircuits' boardcheck signaleert.

**Fix (echte footprint-fout, wel oplossen):**
```
(pad "" np_thru_hole circle (at X Y) (size D D) (drill D) (layers "*.Mask"))
```
d.w.z. **geen** `*.Cu` in de `layers`-lijst van een NPTH-pad — dit is de
KiCad-standaard voor een zuiver mechanisch gat (vergelijk met de ingebouwde
`MountingHole`-footprints).

**Als de melding tóch verschijnt** (bv. bij een andere connector, of in
toekomstige projecten): dit is **inherent** aan elk niet-geplateerd gat — een
restring van exact 0 mm past per definitie niet in Eurocircuits' vaste
dropdown-categorieën. Het "Negeren"-knopje ernaast is precies hiervoor bedoeld.
Geen verdere actie nodig zolang het om een NPTH-gat gaat.

### 3.3 Checklist samengevat

| Controle | Actie |
|---|---|
| Git werkdirectory schoon? | `git status` → clean voordat je exporteert |
| DRC schoon (op echte problemen)? | `kicad-cli pcb drc` in-place, exclusies gerespecteerd |
| Binnenlagen met custom namen? | Upload native KiCad-project, of controleer `.gbrjob` |
| NPTH-footprints? | Check `layers` bevat geen `*.Cu` |
| `.gbrjob` aanwezig in zip? | Ja → voorkomt laag-misinterpretatie |
| PTH/NPTH apart? | `--excellon-separate-th` gebruikt |

---

## 4. Stencil-dikte bepalen

Bepaal de stencildikte op basis van de **Area Ratio** (IPC-7525) van de kleinste
footprint-pad op het bord, niet op gevoel:

```
Area Ratio = (L × W) / (2 × T × (L + W))
```
waarbij `L`,`W` = aperture-afmetingen (mm) en `T` = stencildikte (mm).

- **Minimum (IPC-7525):** Area Ratio ≥ 0,66
- **Voorkeur voor betrouwbare yield:** ≥ 0,75

**Werkwijze:**
1. Zoek de kleinste *echte* SMD-pad op het bord (sluit placeholder/0-mm pads van
   bv. SOM-referentie-footprints uit).
2. Bereken de Area Ratio voor de beschikbare stencildiktes (bv. 100 µm en 130 µm).
3. Kies de dunste optie die voor **alle** pads ≥ 0,66 geeft (bij voorkeur ≥ 0,75
   voor de kritieke/fijnste pads).
4. Controleer dat de gekozen pasta (deeltjesgrootte / "Type") geen klontering
   geeft: kleinste aperture-breedte ≥ ~4-5× de deeltjesgrootte.
   - Type 3 (25-45 µm): geschikt vanaf ~0,5 mm pitch
   - Type 4 (20-38 µm): geschikt vanaf ~0,4 mm pitch (meest gebruikte paste)
   - Type 5 (15-25 µm): nodig voor 0201/01005 en <0,4 mm pitch

**Vuistregel per pitch (indicatief, IPC-7525):**

| Component-pitch | Richtlijn stencildikte |
|---|---|
| ≥ 0,8 mm | 150 µm |
| 0,65 mm | 127 µm |
| 0,5 mm | 100 µm |
| 0,4 mm (fijne QFN) | 80–100 µm |

Bij twijfel: reken de Area Ratio voor de *specifieke* kleinste pad op jouw bord
uit — de vuistregel per pitch is een startpunt, geen vervanging van de
berekening.

---

## 5. Vastleggen in git: commit, tag en release

**Commit:** beschrijf wat er is aangepast en waarom (zie voorbeeld in
`iMC_vX_Processor_Module_PCBA` commit `00b5d5c`), met een `Co-authored-by:
Copilot <223556219+Copilot@users.noreply.github.com>`-trailer indien de wijziging
(mede) door Copilot is gemaakt.

**Tag-conventie** (gebaseerd op bestaande tags in de iMC_vX-projecten):
```
v<versie>-PCBA-Order-<referentie>
```
bv. `v0.2-PCBA-Order-EmbedTech_iMC_vX_Processor_Module_V02`,
`v1.0-PCBA-Order-B5246234`, `io-module-v01-eurocircuits-E1785035`.

Annotated tag met bestelgegevens in de message:
```powershell
git tag -a "v<versie>-PCBA-Order-<referentie>" -m @"
PCBA <ProjectNaam> v<versie> - Bestelling <referentie> - <datum>

PCB naam: <...>
Aankoopreferentie: <...>
Projectreferentie: <...>
Fabricant: Eurocircuits (<lagen>-laags, <finish>, <stencil-info>)
"@
git push origin "v<versie>-PCBA-Order-<referentie>"
```

**GitHub Release** met de twee fabricage-zips als assets:
```powershell
gh release create "v<versie>-PCBA-Order-<referentie>" `
  "fabrication\<project>_Eurocircuits_<datum>.zip" `
  "fabrication\<project>_NativeKiCad_<datum>.zip" `
  --title "<ProjectNaam> V<versie> - Eurocircuits order" `
  --notes-file <notities.md>
```

Zo is voor elk toekomstig project terug te vinden: welke bestanden exact zijn
besteld, bij welke revisie van het ontwerp, met welke bestelreferentie.
