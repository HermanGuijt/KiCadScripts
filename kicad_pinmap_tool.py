import os
import sys
import re

def print_menu():
    print("\nKiCad Symbol Pin Mapping Tool")
    print("1. Exporteer pin-mapping uit .kicad_sym bestand naar tekst")
    print("2. Importeer pin-mapping uit tekstbestand naar .kicad_sym bestand")
    print("3. Stoppen")

def parse_kicad_symbol_file(sym_path):
    """Parseert een .kicad_sym bestand en haalt de pin-mapping op volgens de S-Expression specificatie."""
    pins = []
    with open(sym_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Handmatig parsen van pin-blokken (haakjesniveau)
    pins = []
    idx = 0
    while True:
        idx = content.find('(pin ', idx)
        if idx == -1:
            break
        # Vind het einde van het pin-blok (haakjes balanceren)
        depth = 0
        end = idx
        while end < len(content):
            if content[end] == '(': depth += 1
            elif content[end] == ')': depth -= 1
            end += 1
            if depth == 0:
                break
        pin_block = content[idx:end]
        # Zoek (name "NAME") en (number "NUMBER")
        name_match = re.search(r'\(name\s+"([^"]+)"', pin_block)
        number_match = re.search(r'\(number\s+"([^"]+)"', pin_block)
        if name_match and number_match:
            pins.append((number_match.group(1), name_match.group(1)))
        idx = end
    return pins

def export_pins(sym_path, txt_path):
    pins = parse_kicad_symbol_file(sym_path)
    print("\nPin mapping:")
    for pin in pins:
        print(f"{pin[0]}: {pin[1]}")
    with open(txt_path, 'w', encoding='utf-8') as f:
        for pin in pins:
            f.write(f"{pin[0]}: {pin[1]}\n")
    print(f"\nPin mapping opgeslagen in {txt_path}")

def import_pins(txt_path, sym_path):
    # Leest mapping uit tekstbestand en vult aan in symboolbestand
    with open(txt_path, 'r', encoding='utf-8') as f:
        mapping = dict(line.strip().split(': ', 1) for line in f if ': ' in line)
    with open(sym_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Functie om een enkele pin-block te vervangen
    def replace_pin_name(match):
        pin_block = match.group(0)
        number_match = re.search(r'\(number\s+"([^"]+)"', pin_block)
        if number_match:
            number = number_match.group(2)
            if number in mapping:
                # Vervang alleen de naam
                pin_block_new = re.sub(r'(\(name\s+")[^"]+("\s+\(effects)', r'\1' + mapping[number] + r'\2', pin_block)
                return pin_block_new
        return pin_block
    # Vervang alle pin-blokken
    new_content = re.sub(r'\(pin\s+.*?\)', replace_pin_name, content, flags=re.DOTALL)
    with open(sym_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Pin-namen bijgewerkt in {sym_path}")

def main():
    while True:
        print_menu()
        keuze = input("Maak een keuze (1-3): ").strip()
        if keuze == '1':
            sym_path = input("Voer pad naar .kicad_sym bestand in: ").strip()
            txt_path = input("Voer pad in voor export tekstbestand: ").strip()
            export_pins(sym_path, txt_path)
        elif keuze == '2':
            txt_path = input("Voer pad naar mapping tekstbestand in: ").strip()
            sym_path = input("Voer pad naar .kicad_sym bestand in: ").strip()
            import_pins(txt_path, sym_path)
        elif keuze == '3':
            print("Programma gestopt.")
            break
        else:
            print("Ongeldige keuze. Probeer opnieuw.")

if __name__ == "__main__":
    main()
