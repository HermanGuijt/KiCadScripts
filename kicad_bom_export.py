#!/usr/bin/env python3
"""
KiCAD 9 BOM Export Tool
Exports Bill of Materials with pricing calculations based on MOQ tiers
"""

import os
import sys
import re
import csv
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple


class Component:
    """Represents a component with all its properties"""
    def __init__(self):
        self.references = []
        self.value = ""
        self.description = ""
        self.footprint = ""
        self.sheet_name = ""
        self.mfr = ""
        self.mfr_part_number = ""
        self.supplier_part_number = ""
        self.price_qty_1 = 0.0
        self.price_qty_10 = 0.0
        self.price_qty_100 = 0.0
        
    @property
    def qty(self):
        return len(self.references)
    
    @property
    def reference(self):
        """Returns sorted comma-separated references"""
        return ", ".join(sorted(self.references, key=lambda x: (re.sub(r'\d+', '', x), int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)))
    
    def calculate_unit_price(self, num_devices: int = 1) -> float:
        """Calculate unit price based on total quantity needed (qty per device * num_devices)"""
        total_qty = self.qty * num_devices
        
        # Determine which price tier applies based on total quantity
        if total_qty >= 100 and self.price_qty_100 > 0:
            return self.price_qty_100
        elif total_qty >= 10 and self.price_qty_10 > 0:
            return self.price_qty_10
        elif self.price_qty_1 > 0:
            return self.price_qty_1
        else:
            return 0.0
    
    def calculate_moq_price(self, num_devices: int) -> float:
        """Calculate total price when making num_devices devices
        
        Args:
            num_devices: Number of devices being manufactured (1, 10, 100, etc.)
        
        Returns:
            Total price for this component for num_devices devices
        """
        total_qty = self.qty * num_devices
        
        # Determine which price tier applies based on total quantity needed
        if total_qty >= 100 and self.price_qty_100 > 0:
            return total_qty * self.price_qty_100
        elif total_qty >= 10 and self.price_qty_10 > 0:
            return total_qty * self.price_qty_10
        elif self.price_qty_1 > 0:
            return total_qty * self.price_qty_1
        else:
            return 0.0


def parse_property(content: str, property_name: str) -> str:
    """Extract property value from KiCAD S-expression"""
    # Escape special regex characters in property name
    escaped_name = re.escape(property_name)
    pattern = rf'\(property\s+"{escaped_name}"\s+"([^"]*)"'
    match = re.search(pattern, content)
    return match.group(1) if match else ""


def parse_kicad_schematic(sch_path: str) -> List[Dict]:
    """Parse KiCAD 9 .kicad_sch file and extract component data"""
    components = []
    
    with open(sch_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract sheet name from title_block or filename
    sheet_name_match = re.search(r'\(title\s+"([^"]*)"', content)
    sheet_name = sheet_name_match.group(1) if sheet_name_match else Path(sch_path).stem
    
    # Find all symbol instances in the schematic (KiCAD 9 format)
    idx = 0
    while True:
        # Look for "(symbol" - can be indented with tabs or spaces
        # First try to find with tab (most common), then with spaces
        idx_tab = content.find('\n\t(symbol', idx)
        idx_space = content.find('\n    (symbol', idx)  # 4 spaces  
        idx_space2 = content.find('\n       (symbol', idx)  # 7 spaces (less common)
        
        # Use whichever comes first (if found)
        candidates = [i for i in [idx_tab, idx_space, idx_space2] if i != -1]
        if not candidates:
            break
        
        idx = min(candidates)
        idx += 1  # Skip the newline
        
        # Find the start of (symbol - skip whitespace
        symbol_start_pos = idx
        while symbol_start_pos < len(content) and content[symbol_start_pos] in ' \t':
            symbol_start_pos += 1
        
        # Find the matching closing parenthesis (skip strings)
        depth = 0
        pos = symbol_start_pos
        in_string = False
        escape_next = False
        
        while pos < len(content):
            char = content[pos]
            
            # Handle string escaping
            if escape_next:
                escape_next = False
                pos += 1
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                pos += 1
                continue
            
            # Toggle string mode
            if char == '"':
                in_string = not in_string
                pos += 1
                continue
            
            # Only count parentheses outside of strings
            if not in_string:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        pos += 1
                        break
            
            pos += 1
        
        symbol_block = content[symbol_start_pos:pos]
        
        # Move index forward for next search
        idx = pos
        
        # Check if this is an actual component (has lib_id and in_bom yes)
        if '(in_bom yes)' not in symbol_block:
            continue
        
        # Extract component properties
        reference = parse_property(symbol_block, "Reference")
        value = parse_property(symbol_block, "Value")
        footprint = parse_property(symbol_block, "Footprint")
        description = parse_property(symbol_block, "Description")
        mfr = parse_property(symbol_block, "MFR")
        mfr_part = parse_property(symbol_block, "MFR Part Number")
        supplier_part = parse_property(symbol_block, "Supplier Part Number")
        
        # Extract pricing information - try both property names
        price_1_str = parse_property(symbol_block, "Unit Price (EUR)")
        if not price_1_str:
            price_1_str = parse_property(symbol_block, "Price Quantity 1")
        
        price_10_str = parse_property(symbol_block, "Price @ MOQ 10 (EUR)")
        if not price_10_str:
            price_10_str = parse_property(symbol_block, "Price Quantity 10")
            
        price_100_str = parse_property(symbol_block, "Price @ MOQ 100 (EUR)")
        if not price_100_str:
            price_100_str = parse_property(symbol_block, "Price Quantity 100")
        
        # Convert prices to float
        def parse_price(price_str: str) -> float:
            try:
                # Remove currency symbols and convert
                price_str = re.sub(r'[^\d.,]', '', price_str)
                price_str = price_str.replace(',', '.')
                return float(price_str) if price_str else 0.0
            except ValueError:
                return 0.0
        
        price_1 = parse_price(price_1_str)
        price_10 = parse_price(price_10_str)
        price_100 = parse_price(price_100_str)
        
        # Skip power symbols and other non-physical components
        if reference and not reference.startswith('#'):
            components.append({
                'reference': reference,
                'value': value,
                'description': description,
                'footprint': footprint,
                'sheet_name': sheet_name,
                'mfr': mfr,
                'mfr_part_number': mfr_part,
                'supplier_part_number': supplier_part,
                'price_qty_1': price_1,
                'price_qty_10': price_10,
                'price_qty_100': price_100,
            })
    
    return components


def deduplicate_multi_unit_components(components: List[Dict]) -> List[Dict]:
    """Remove duplicate entries for multi-unit components (same reference)
    
    Multi-unit components (like multi-gate ICs) appear multiple times in the schematic
    with the same reference but different units. We only want to count them once.
    Keep the unit that has pricing information if available.
    """
    unique_components = {}
    duplicates_found = []
    
    for comp in components:
        ref = comp['reference']
        if ref in unique_components:
            # Already seen this reference - this is a duplicate unit
            existing = unique_components[ref]
            
            # Update sheet names
            if comp['sheet_name'] not in existing['sheet_name']:
                existing['sheet_name'] = f"{existing['sheet_name']}, {comp['sheet_name']}"
            
            # If current component has pricing info and existing doesn't, use current
            if comp['price_qty_1'] > 0 and existing['price_qty_1'] == 0:
                existing['price_qty_1'] = comp['price_qty_1']
                existing['price_qty_10'] = comp['price_qty_10']
                existing['price_qty_100'] = comp['price_qty_100']
                existing['mfr'] = comp['mfr'] or existing['mfr']
                existing['mfr_part_number'] = comp['mfr_part_number'] or existing['mfr_part_number']
                existing['supplier_part_number'] = comp['supplier_part_number'] or existing['supplier_part_number']
                existing['description'] = comp['description'] or existing['description']
            
            # Track this duplicate
            duplicates_found.append({
                'reference': ref,
                'value': comp['value'],
                'sheet': comp['sheet_name']
            })
        else:
            # First time seeing this reference
            unique_components[ref] = comp
    
    # Print found duplicates
    if duplicates_found:
        print(f"\nMulti-unit componenten gedetecteerd ({len(duplicates_found)} extra units verwijderd):")
        # Group by reference
        by_ref = {}
        for dup in duplicates_found:
            ref = dup['reference']
            if ref not in by_ref:
                by_ref[ref] = []
            by_ref[ref].append(dup['sheet'])
        
        for ref, sheets in sorted(by_ref.items()):
            comp_info = unique_components[ref]
            all_sheets = comp_info['sheet_name']
            print(f"  {ref} ({comp_info['value']}) - gevonden op: {all_sheets}")
    
    return list(unique_components.values())


def group_components(components: List[Dict]) -> List[Component]:
    """Group components by value, footprint, and other identifying properties"""
    groups = defaultdict(Component)
    
    for comp_data in components:
        # Create grouping key
        key = (
            comp_data['value'],
            comp_data['footprint'],
            comp_data['mfr_part_number'],
            comp_data['description']
        )
        
        comp = groups[key]
        comp.references.append(comp_data['reference'])
        comp.value = comp_data['value']
        comp.description = comp_data['description']
        comp.footprint = comp_data['footprint']
        comp.sheet_name = comp_data['sheet_name']
        comp.mfr = comp_data['mfr']
        comp.mfr_part_number = comp_data['mfr_part_number']
        comp.supplier_part_number = comp_data['supplier_part_number']
        
        # Use the pricing from the first component in the group
        if comp.price_qty_1 == 0:
            comp.price_qty_1 = comp_data['price_qty_1']
            comp.price_qty_10 = comp_data['price_qty_10']
            comp.price_qty_100 = comp_data['price_qty_100']
    
    return list(groups.values())


def export_bom_to_csv(components: List[Component], output_path: str):
    """Export BOM to CSV file with all requested columns (European format)"""
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Reference',
            'Qty',
            'Value',
            'Description',
            'Sheet Name',
            'Unit Price (EUR)',
            'MFR Part Number',
            'MFR',
            'Supplier Part Number',
            'Unit Price @ Qty 1',
            'Unit Price @ Qty 10',
            'Unit Price @ Qty 100',
            'Total Price Quantity 1',
            'Total Price Quantity 10',
            'Total Price Quantity 100'
        ]
        
        # Use semicolon as delimiter for European CSV format
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        
        # Sort components by reference
        sorted_components = sorted(components, key=lambda c: c.reference)
        
        for comp in sorted_components:
            # Unit price for making 1 device
            unit_price = comp.calculate_unit_price(num_devices=1)
            
            # Total prices for different production quantities
            price_moq_1 = comp.calculate_moq_price(num_devices=1)
            price_moq_10 = comp.calculate_moq_price(num_devices=10)
            price_moq_100 = comp.calculate_moq_price(num_devices=100)
            
            # Calculate price per device at different production volumes
            price_per_device_1 = price_moq_1 / 1
            price_per_device_10 = price_moq_10 / 10
            price_per_device_100 = price_moq_100 / 100
            
            # Format numbers with comma as decimal separator (European format)
            writer.writerow({
                'Reference': comp.reference,
                'Qty': comp.qty,
                'Value': comp.value,
                'Description': comp.description,
                'Sheet Name': comp.sheet_name,
                'Unit Price (EUR)': f"{unit_price:.4f}".replace('.', ','),
                'MFR Part Number': comp.mfr_part_number,
                'MFR': comp.mfr,
                'Supplier Part Number': comp.supplier_part_number,
                'Unit Price @ Qty 1': f"{comp.price_qty_1:.4f}".replace('.', ','),
                'Unit Price @ Qty 10': f"{comp.price_qty_10:.4f}".replace('.', ','),
                'Unit Price @ Qty 100': f"{comp.price_qty_100:.4f}".replace('.', ','),
                'Total Price Quantity 1': f"{price_per_device_1:.4f}".replace('.', ','),
                'Total Price Quantity 10': f"{price_per_device_10:.4f}".replace('.', ','),
                'Total Price Quantity 100': f"{price_per_device_100:.4f}".replace('.', ',')
            })


def find_schematic_files(project_dir: str) -> List[str]:
    """Find all .kicad_sch files in the project directory"""
    sch_files = []
    for file in Path(project_dir).glob('*.kicad_sch'):
        sch_files.append(str(file))
    return sch_files


def main():
    print("KiCAD 9 BOM Export Tool")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nGebruik:")
        print(f"  python {sys.argv[0]} <project_directory>")
        print(f"  python {sys.argv[0]} <schematic_file.kicad_sch>")
        print("\nOf draai het script zonder argumenten voor interactieve modus:")
        
        project_path = input("\nVoer het pad in naar de KiCAD project directory of .kicad_sch bestand: ").strip()
    else:
        project_path = sys.argv[1]
    
    # Remove quotes if present
    project_path = project_path.strip('"\'')
    
    if not os.path.exists(project_path):
        print(f"Fout: Pad '{project_path}' bestaat niet!")
        sys.exit(1)
    
    # Determine if it's a file or directory
    all_components = []
    
    if os.path.isfile(project_path) and project_path.endswith('.kicad_sch'):
        print(f"\nParsing schematic: {project_path}")
        components = parse_kicad_schematic(project_path)
        all_components.extend(components)
        output_path = project_path.replace('.kicad_sch', '_BOM.csv')
    
    elif os.path.isdir(project_path):
        sch_files = find_schematic_files(project_path)
        
        if not sch_files:
            print(f"Geen .kicad_sch bestanden gevonden in {project_path}")
            sys.exit(1)
        
        print(f"\nGevonden {len(sch_files)} schematic bestand(en):")
        for sch_file in sch_files:
            print(f"  - {Path(sch_file).name}")
        
        # Parse all schematic files
        for sch_file in sch_files:
            print(f"\nParsing: {Path(sch_file).name}")
            components = parse_kicad_schematic(sch_file)
            all_components.extend(components)
        
        # Output path based on project directory
        project_name = Path(project_path).name
        output_path = os.path.join(project_path, f"{project_name}_BOM.csv")
    
    else:
        print("Fout: Specificeer een .kicad_sch bestand of een project directory")
        sys.exit(1)
    
    if not all_components:
        print("\nGeen componenten gevonden!")
        sys.exit(0)
    
    print(f"\nTotaal aantal componenten gevonden: {len(all_components)}")
    
    # Remove duplicates from multi-unit components (e.g., U1A, U1B, U1C should count as 1x U1)
    all_components = deduplicate_multi_unit_components(all_components)
    print(f"Na verwijderen multi-unit duplicaten: {len(all_components)}")
    
    # Group components
    grouped_components = group_components(all_components)
    print(f"Aantal unieke component types: {len(grouped_components)}")
    
    # Export to CSV
    export_bom_to_csv(grouped_components, output_path)
    
    print(f"\n✓ BOM succesvol geëxporteerd naar: {output_path}")
    
    # Display summary
    total_qty = sum(comp.qty for comp in grouped_components)
    print(f"\nSamenvatting:")
    print(f"  Unieke componenten: {len(grouped_components)}")
    print(f"  Totaal aantal: {total_qty}")
    
    # Calculate total cost at different production quantities
    total_moq_1 = sum(comp.calculate_moq_price(1) for comp in grouped_components)
    total_moq_10 = sum(comp.calculate_moq_price(10) for comp in grouped_components)
    total_moq_100 = sum(comp.calculate_moq_price(100) for comp in grouped_components)
    
    if total_moq_1 > 0:
        print(f"\nGeschatte kosten:")
        print(f"  @ 1 apparaat:    €{total_moq_1:.2f}")
        print(f"  @ 10 apparaten:  €{total_moq_10:.2f}")
        print(f"  @ 100 apparaten: €{total_moq_100:.2f}")


if __name__ == "__main__":
    main()
