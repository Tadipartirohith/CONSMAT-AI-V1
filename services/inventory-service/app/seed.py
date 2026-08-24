"""Seed the materials reference data (idempotent). Run after migrations.

Usage: python -m app.seed

Materials are classified into ConSmat's page-3 business verticals (`segment`):
  S&F        Structure & Foundation (cement, steel, concrete, stone, sand, aggregate, formwork)
  B&B        Bricks & Blocks (bricks, blocks, pavers, curbstones, gutters, soak pits, parking tiles)
  S&S        Sheets & Shades (timber, plywood, roofing sheets, tiles, paints)
  P&P        Pipes & Plugs (pipes, plumbing, electrical, wires, transformers, panel boards)
  MixG&FixG  Mortars/Adhesives/Coatings (adhesives, plaster, jointing mortar, grouts, putty, textures, waterproofing)
  Interiors  Interiors & Home (doors/uPVC, glass, hardware, furniture, modular kitchen, elevations, lights, home automation)

Structural materials keep a `per_sqft` coefficient for the auto-plan; everything else is quantified
through the CE/architect product BOQ (per_sqft = 0) and dispatched on an explicit phase.
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import Material, Product

_0 = Decimal("0")


def _m(mid, name, segment, category, unit, per_sqft=_0, grade=""):
    return {"id": mid, "name": name, "segment": segment, "category": category, "unit": unit,
            "grade": grade, "per_sqft": Decimal(str(per_sqft))}


MATERIALS = [
    # ----- S&F: Structure & Foundation -----
    _m("cement", "Cement", "S&F", "binder", "bags", "0.40", "OPC 53-Grade"),
    _m("steel", "Structural Steel (TMT)", "S&F", "reinforcement", "tonnes", "0.004", "Fe 500D"),
    _m("rmc", "Concrete (Ready-Mix)", "S&F", "concrete", "cum"),
    _m("stone", "Stone", "S&F", "aggregate", "tonnes"),
    _m("sand", "Sand", "S&F", "aggregate", "tonnes", "0.0816", "Fine (plastering)"),
    _m("aggregate", "Aggregates", "S&F", "aggregate", "tonnes", "0.057", "20mm blue metal"),
    _m("formwork", "Aluminium Formwork", "S&F", "formwork", "sqft"),
    # ----- B&B: Bricks & Blocks -----
    _m("bricks", "Bricks", "B&B", "masonry", "pcs", "8.0", "Class-A red clay"),
    _m("blocks", "Concrete & AAC Blocks", "B&B", "masonry", "pcs"),
    _m("parking_tiles", "Parking Tiles", "B&B", "paving", "box"),
    _m("interlocking_pavers", "Interlocking Paving Blocks", "B&B", "paving", "pcs"),
    _m("curbstones", "Curbstones", "B&B", "paving", "pcs"),
    _m("gutters", "PCC / RCC Gutters", "B&B", "precast", "pcs"),
    _m("soak_pits", "Soak Pits", "B&B", "precast", "pcs"),
    # ----- S&S: Sheets & Shades -----
    _m("timber", "Timber", "S&S", "wood", "cft"),
    _m("plywood", "Plywood & Boards", "S&S", "wood", "sheet"),
    _m("roofing_sheets", "Roofing Sheets", "S&S", "roofing", "sheet"),
    _m("tiles", "Ceramic Tiles", "S&S", "finishing", "box"),
    _m("paints", "Paints & Coatings", "S&S", "finishing", "ltr"),
    # ----- P&P: Pipes & Plugs -----
    _m("pipes", "MS & GI Pipes", "P&P", "mep", "m"),
    _m("plumbing", "Plumbing & Sanitaryware", "P&P", "mep", "pcs"),
    _m("electrical", "Electrical Fittings", "P&P", "mep", "pcs"),
    _m("wires", "Wires & Cables", "P&P", "mep", "coil"),
    _m("transformers", "Distribution Transformers", "P&P", "power", "pcs"),
    _m("panel_boards", "Panel Boards", "P&P", "power", "pcs"),
    # ----- MixG & FixG: Mortars / Adhesives / Coatings -----
    _m("adhesives", "Tile Adhesives", "MixG&FixG", "chemicals", "bags"),
    _m("ready_mix_plaster", "Ready-Mix Plaster", "MixG&FixG", "chemicals", "bags"),
    _m("block_jointing_mortar", "Block Jointing Mortar", "MixG&FixG", "chemicals", "bags"),
    _m("grouts", "Grouts", "MixG&FixG", "chemicals", "pcs"),
    _m("skim_coats", "Skim Coats & Putty", "MixG&FixG", "chemicals", "bags"),
    _m("surface_coating", "Surface Coating (Textures)", "MixG&FixG", "chemicals", "ltr"),
    _m("waterproofing", "Waterproofing & Admixtures", "MixG&FixG", "chemicals", "kg"),
    # ----- Interiors & Home -----
    _m("doors", "uPVC Windows & Doors", "Interiors", "interior", "pcs"),
    _m("glass", "Glass & Facade", "Interiors", "interior", "sqft"),
    _m("hardware", "Hardware & Fasteners", "Interiors", "interior", "pcs"),
    _m("office_furniture", "Office Furniture", "Interiors", "furniture", "pcs"),
    _m("modular_kitchen", "Modular Kitchen", "Interiors", "furniture", "set"),
    _m("building_elevations", "Building Elevations", "Interiors", "facade", "sqft"),
    _m("lights", "Unique Lights", "Interiors", "electrical", "pcs"),
    _m("home_automation", "Home Automation", "Interiors", "automation", "pcs"),
]


def _p(pid, material, brand, name, grade, unit):
    return {"id": pid, "material_id": material, "brand": brand, "name": name, "grade": grade, "unit": unit}


PRODUCTS = [
    # ---- cement ----
    _p("cement-ultratech-opc53", "cement", "UltraTech", "UltraTech OPC 53 Grade Cement 50kg", "OPC 53", "bags"),
    _p("cement-acc-gold-ppc", "cement", "ACC", "ACC Gold Water Shield PPC Cement 50kg", "PPC", "bags"),
    _p("cement-ambuja-plus", "cement", "Ambuja", "Ambuja Plus Roof Special PPC Cement 50kg", "PPC", "bags"),
    _p("cement-dalmia-dsp", "cement", "Dalmia", "Dalmia DSP OPC 43 Grade Cement 50kg", "OPC 43", "bags"),
    _p("cement-bharathi-opc", "cement", "Bharathi", "Bharathi Cement OPC 53 Grade 50kg", "OPC 53", "bags"),
    _p("cement-ramco-supergrade", "cement", "Ramco", "Ramco Supergrade PPC Cement 50kg", "PPC", "bags"),
    _p("cement-birla-a1", "cement", "Birla A1", "Birla A1 Premium OPC 53 Cement 50kg", "OPC 53", "bags"),
    _p("cement-penna-ppc", "cement", "Penna", "Penna PPC Cement 50kg", "PPC", "bags"),
    _p("cement-jk-white", "cement", "JK", "JK White Cement 40kg", "White", "bags"),
    # ---- steel ----
    _p("steel-tata-tiscon", "steel", "TATA", "TATA Tiscon 500D TMT Bar", "Fe 500D", "tonnes"),
    _p("steel-jsw-neosteel", "steel", "JSW", "JSW Neosteel 550D TMT Bar", "Fe 550D", "tonnes"),
    _p("steel-sail-tmt", "steel", "SAIL", "SAIL TMT Fe 500 Bar", "Fe 500", "tonnes"),
    _p("steel-vizag-tmt", "steel", "Vizag", "Vizag Steel TMT Fe 500D Bar", "Fe 500D", "tonnes"),
    _p("steel-kamdhenu-nxt", "steel", "Kamdhenu", "Kamdhenu NXT 550D TMT Bar", "Fe 550D", "tonnes"),
    _p("steel-jindal-panther", "steel", "Jindal", "Jindal Panther Fe 500D TMT Bar", "Fe 500D", "tonnes"),
    # ---- rmc / concrete ----
    _p("rmc-m20", "rmc", "ACC", "ACC RMC M20 Grade", "M20", "cum"),
    _p("rmc-m25", "rmc", "UltraTech", "UltraTech Concrete RMC M25", "M25", "cum"),
    _p("rmc-m30-hsc", "rmc", "Godrej", "Godrej High-Strength Concrete M30", "High-Strength", "cum"),
    _p("rmc-hpc", "rmc", "RDC", "RDC High-Performance Concrete M40", "High-Performance", "cum"),
    _p("rmc-lightweight", "rmc", "UltraTech", "UltraTech Lightweight Concrete", "Lightweight", "cum"),
    # ---- stone ----
    _p("stone-granite-black", "stone", "", "Black Granite Slab (polished)", "Granite", "sqft"),
    _p("stone-marble", "stone", "", "Imported Marble Slab", "Marble", "sqft"),
    _p("stone-kadapa", "stone", "", "Kadapa Black Stone", "Kadapa", "sqft"),
    # ---- sand ----
    _p("sand-river-fine", "sand", "", "River Sand (Fine, plastering grade)", "Fine", "tonnes"),
    _p("sand-msand", "sand", "", "Manufactured Sand (M-Sand) for concrete", "M-Sand", "tonnes"),
    _p("sand-psand", "sand", "", "Plastering Sand (P-Sand)", "P-Sand", "tonnes"),
    # ---- aggregate ----
    _p("aggregate-20mm-blue", "aggregate", "", "20mm Blue Metal Aggregate", "20mm", "tonnes"),
    _p("aggregate-12mm", "aggregate", "", "12mm Crushed Stone Aggregate", "12mm", "tonnes"),
    _p("aggregate-40mm", "aggregate", "", "40mm Crushed Stone Aggregate", "40mm", "tonnes"),
    _p("aggregate-gsb", "aggregate", "", "GSB / Crusher Dust", "GSB", "tonnes"),
    # ---- formwork ----
    _p("formwork-alu-wall", "formwork", "MFE", "MFE Aluminium Wall Formwork Panel", "Wall", "sqft"),
    _p("formwork-alu-slab", "formwork", "PERI", "PERI Aluminium Slab Formwork", "Slab", "sqft"),
    _p("formwork-alu-column", "formwork", "Kumkang", "Kumkang Aluminium Column Formwork", "Column", "sqft"),
    _p("formwork-ply-shuttering", "formwork", "", "Film-faced Shuttering Plywood 12mm", "Shuttering", "sheet"),
    # ---- bricks ----
    _p("bricks-redclay-a", "bricks", "", "Class-A Red Clay Bricks", "Class-A", "pcs"),
    _p("bricks-wirecut", "bricks", "", "Wire-cut Red Bricks", "Wire-cut", "pcs"),
    _p("bricks-flyash", "bricks", "", "Fly Ash Bricks", "Fly Ash", "pcs"),
    # ---- blocks ----
    _p("blocks-aac-600", "blocks", "Magicrete", "Magicrete AAC Block 600x200x100", "AAC", "pcs"),
    _p("blocks-aac-biltech", "blocks", "Biltech", "Biltech Aerocon AAC Block 600x200x150", "AAC", "pcs"),
    _p("blocks-solid-4", "blocks", "", "Solid Concrete Block 4 inch", "Solid 4\"", "pcs"),
    _p("blocks-solid-6", "blocks", "", "Solid Concrete Block 6 inch", "Solid 6\"", "pcs"),
    _p("blocks-hollow-cc", "blocks", "", "Hollow Concrete Block 400x200x200", "Hollow", "pcs"),
    # ---- parking tiles ----
    _p("parking-tile-60mm", "parking_tiles", "", "Parking Tile 60mm (heavy duty)", "60mm", "box"),
    _p("parking-tile-cosmic", "parking_tiles", "", "Cosmic Parking Tile 300x300", "Cosmic", "box"),
    # ---- interlocking pavers ----
    _p("paver-rect-60", "interlocking_pavers", "", "Interlocking Rectangular Paver 60mm", "Rectangular", "pcs"),
    _p("paver-zigzag-80", "interlocking_pavers", "", "Interlocking Zigzag Paver 80mm", "Zigzag", "pcs"),
    # ---- curbstones ----
    _p("curbstone-chamfer", "curbstones", "", "Curbstone Chamfer (Long)", "Chamfer", "pcs"),
    _p("curbstone-round", "curbstones", "", "Curbstone Round (Short)", "Round", "pcs"),
    # ---- gutters ----
    _p("gutter-pcc", "gutters", "", "PCC Gutter", "PCC", "pcs"),
    _p("gutter-rcc-cover", "gutters", "", "RCC Gutter Cover", "RCC Cover", "pcs"),
    # ---- soak pits ----
    _p("soakpit-ring", "soak_pits", "", "Soak Pit Ring", "Ring", "pcs"),
    _p("soakpit-cover", "soak_pits", "", "Soak Pit Cover", "Cover", "pcs"),
    # ---- timber ----
    _p("timber-teak", "timber", "", "Teak Wood (seasoned)", "Teak", "cft"),
    _p("timber-sal", "timber", "", "Sal Wood", "Sal", "cft"),
    # ---- plywood ----
    _p("ply-century-mr", "plywood", "Century", "Century Club Prime MR Plywood 18mm", "MR", "sheet"),
    _p("ply-greenply-bwp", "plywood", "Greenply", "Greenply Green Club BWP Plywood 18mm", "BWP", "sheet"),
    _p("ply-actionteso-block", "plywood", "Action Tesa", "Action Tesa HDHMR Board 18mm", "HDHMR", "sheet"),
    _p("ply-mdf-greenpanel", "plywood", "Greenpanel", "Greenpanel Plain MDF Board 12mm", "MDF", "sheet"),
    # ---- roofing sheets ----
    _p("roof-cement-sheet", "roofing_sheets", "Everest", "Everest Fibre Cement Roofing Sheet", "Cement", "sheet"),
    _p("roof-polycarbonate", "roofing_sheets", "", "Polycarbonate Roofing Sheet (clear)", "Polycarbonate", "sheet"),
    _p("roof-color-coated", "roofing_sheets", "JSW", "JSW Colour-Coated Roofing Sheet", "Colour Coated", "sheet"),
    # ---- tiles ----
    _p("tiles-kajaria-vitrified", "tiles", "Kajaria", "Kajaria Vitrified Floor Tile 600x600", "Floor", "box"),
    _p("tiles-somany-gvt", "tiles", "Somany", "Somany GVT Floor Tile 800x800", "Floor", "box"),
    _p("tiles-johnson-wall", "tiles", "Johnson", "Johnson Ceramic Wall Tile 300x600", "Wall", "box"),
    _p("tiles-rak-porcelain", "tiles", "RAK", "RAK Porcelain Tile 600x600", "Floor", "box"),
    # ---- paints ----
    _p("paints-asian-apex", "paints", "Asian Paints", "Asian Paints Apex Ultima Exterior 20L", "Exterior", "ltr"),
    _p("paints-asian-royale", "paints", "Asian Paints", "Asian Paints Royale Luxury Emulsion 20L", "Interior", "ltr"),
    _p("paints-berger-weathercoat", "paints", "Berger", "Berger WeatherCoat Anti-Dust 20L", "Exterior", "ltr"),
    _p("paints-dulux-velvet", "paints", "Dulux", "Dulux Velvet Touch Interior 20L", "Interior", "ltr"),
    # ---- pipes (MS & GI) ----
    _p("pipes-gi-tata", "pipes", "TATA", "TATA GI Pipe 2 inch (medium)", "GI", "m"),
    _p("pipes-gi-jindal", "pipes", "Jindal", "Jindal GI Pipe 1 inch", "GI", "m"),
    _p("pipes-ms-square", "pipes", "APL Apollo", "APL Apollo MS Square Pipe 50x50", "MS", "m"),
    _p("pipes-ms-round", "pipes", "Surya", "Surya MS Round Pipe 25mm", "MS", "m"),
    # ---- plumbing ----
    _p("plumbing-upvc-supreme", "plumbing", "Supreme", "Supreme UPVC Pipe 4 inch (drainage)", "UPVC", "m"),
    _p("plumbing-cpvc-ashirvad", "plumbing", "Ashirvad", "Ashirvad Flowguard CPVC Pipe 1 inch", "CPVC", "m"),
    _p("plumbing-jaquar-faucet", "plumbing", "Jaquar", "Jaquar Continental Pillar Cock (Tap)", "Tap", "pcs"),
    _p("plumbing-hindware-wc", "plumbing", "Hindware", "Hindware Wall-Hung Water Closet", "WC", "pcs"),
    _p("plumbing-cera-basin", "plumbing", "Cera", "Cera Wash Basin (Table Top)", "Basin", "pcs"),
    _p("plumbing-watertank-sintex", "plumbing", "Sintex", "Sintex Water Tank 1000L", "Tank", "pcs"),
    # ---- electrical ----
    _p("electrical-switch-anchor", "electrical", "Anchor", "Anchor Roma Modular Switch 6A", "Switch", "pcs"),
    _p("electrical-switch-legrand", "electrical", "Legrand", "Legrand Myrius Modular Switch", "Switch", "pcs"),
    _p("electrical-mcb-havells", "electrical", "Havells", "Havells MCB 32A SP", "MCB", "pcs"),
    _p("electrical-socket-gm", "electrical", "GM", "GM 16A Modular Socket", "Socket", "pcs"),
    # ---- wires ----
    _p("wires-finolex-15", "wires", "Finolex", "Finolex FR Wire 1.5 sqmm (90m)", "1.5sqmm", "coil"),
    _p("wires-polycab-25", "wires", "Polycab", "Polycab FR Wire 2.5 sqmm (90m)", "2.5sqmm", "coil"),
    _p("wires-havells-40", "wires", "Havells", "Havells Life Line Wire 4.0 sqmm", "4.0sqmm", "coil"),
    _p("wires-rr-6", "wires", "RR Kabel", "RR Kabel Wire 6.0 sqmm", "6.0sqmm", "coil"),
    # ---- transformers ----
    _p("transformer-100kva", "transformers", "Kirloskar", "Kirloskar 100 kVA Distribution Transformer", "100kVA", "pcs"),
    _p("transformer-250kva", "transformers", "Crompton", "Crompton 250 kVA Distribution Transformer", "250kVA", "pcs"),
    # ---- panel boards ----
    _p("panel-schneider-8way", "panel_boards", "Schneider", "Schneider 8-Way Distribution Board", "8-Way", "pcs"),
    _p("panel-lt-mcc", "panel_boards", "L&T", "L&T LT Panel / MCC Board", "LT Panel", "pcs"),
    # ---- adhesives ----
    _p("adh-fixg-gold", "adhesives", "FixG", "FixG Gold Tile Adhesive 20kg", "Type-1 (Gold)", "bags"),
    _p("adh-fixg-platinum", "adhesives", "FixG", "FixG Platinum Tile Adhesive 20kg", "Type-3 (Platinum)", "bags"),
    _p("adh-myk-tileadh", "adhesives", "MYK Laticrete", "MYK Laticrete Tile Adhesive Type-1 20kg", "Type-1", "bags"),
    # ---- ready-mix plaster ----
    _p("plaster-mixg", "ready_mix_plaster", "MixG", "MixG Ready-Mix Plaster 40kg", "Plaster", "bags"),
    _p("plaster-mixg-plus", "ready_mix_plaster", "MixG", "MixG Plaster Plus 40kg", "Plaster Plus", "bags"),
    # ---- block jointing mortar ----
    _p("mortar-fixg-jointer", "block_jointing_mortar", "FixG", "FixG Jointer Block Jointing Mortar 40kg", "Jointer", "bags"),
    # ---- grouts ----
    _p("grout-fixg-3x", "grouts", "FixG", "FixG 3X Tile Grout 1kg", "3X", "pcs"),
    _p("grout-fixg-2x", "grouts", "FixG", "FixG 2X Tile Grout 1kg", "2X", "pcs"),
    _p("grout-fixg-unsand", "grouts", "FixG", "FixG Unsanded Grout 1kg", "Unsanded", "pcs"),
    _p("grout-fixg-premium", "grouts", "FixG", "FixG Premium Epoxy Grout 1kg", "Premium", "pcs"),
    # ---- skim coats / putty ----
    _p("putty-fixg-wallcare", "skim_coats", "FixG", "FixG Wall Care Putty 40kg", "Putty", "bags"),
    _p("primer-fixg-interior", "skim_coats", "FixG", "FixG Interior Primer 20L", "Interior Primer", "bags"),
    _p("primer-fixg-exterior", "skim_coats", "FixG", "FixG Exterior Primer 20L", "Exterior Primer", "bags"),
    _p("putty-birla", "skim_coats", "Birla", "Birla White Wall Care Putty 40kg", "Putty", "bags"),
    # ---- surface coating ----
    _p("coat-mixg-designer", "surface_coating", "MixG", "MixG Designer Texture 20L", "Designer Texture", "ltr"),
    _p("coat-mixg-natural", "surface_coating", "MixG", "MixG Natural Texture 20L", "Natural Texture", "ltr"),
    # ---- waterproofing ----
    _p("wp-drfixit-lw", "waterproofing", "Dr. Fixit", "Dr. Fixit LW+ Integral Waterproofing 1L", "Admixture", "kg"),
    _p("wp-fosroc-brushbond", "waterproofing", "Fosroc", "Fosroc Brushbond Crystalline 30kg", "Coating", "kg"),
    _p("wp-fosroc-conplast", "waterproofing", "Fosroc", "Fosroc Conplast SP430 Superplasticiser 5L", "Admixture", "kg"),
    _p("wp-bitumen-coat", "waterproofing", "", "Bituminous Waterproof Coating 20L", "Bitumen", "kg"),
    # ---- doors / uPVC ----
    _p("doors-flush-century", "doors", "Century", "Century Flush Door 32mm", "Flush", "pcs"),
    _p("doors-upvc-window", "doors", "Fenesta", "Fenesta uPVC Sliding Window", "uPVC", "pcs"),
    _p("doors-upvc-hardware", "doors", "", "uPVC Window Hardware Set", "uPVC Hardware", "pcs"),
    _p("doors-main-teak", "doors", "", "Teak Wood Main Door (solid)", "Teak", "pcs"),
    # ---- glass ----
    _p("glass-sg-clear", "glass", "Saint-Gobain", "Saint-Gobain Clear Float Glass 8mm", "Float", "sqft"),
    _p("glass-toughened", "glass", "Saint-Gobain", "Saint-Gobain Toughened Glass 10mm", "Toughened", "sqft"),
    _p("glass-upvc", "glass", "AIS", "AIS Glass for uPVC (DGU)", "DGU", "sqft"),
    # ---- hardware ----
    _p("hw-hinges-hettich", "hardware", "Hettich", "Hettich Soft-Close Hinges (pair)", "Hinge", "pcs"),
    _p("hw-lock-godrej", "hardware", "Godrej", "Godrej Mortise Door Lock Set", "Lock", "pcs"),
    _p("hw-binding-wire", "hardware", "", "GI Binding Wire 18 SWG (1kg)", "Binding", "pcs"),
    # ---- office furniture ----
    _p("furniture-office-desk", "office_furniture", "Godrej", "Godrej Office Desk", "Desk", "pcs"),
    _p("furniture-office-chair", "office_furniture", "Featherlite", "Featherlite Ergonomic Office Chair", "Chair", "pcs"),
    # ---- modular kitchen ----
    _p("kitchen-l-shaped", "modular_kitchen", "Sleek", "Sleek Modular Kitchen (L-Shaped)", "L-Shaped", "set"),
    _p("kitchen-island", "modular_kitchen", "Hafele", "Hafele Modular Kitchen (Island)", "Island", "set"),
    # ---- building elevations ----
    _p("elevation-acp", "building_elevations", "Alstrong", "Alstrong ACP Elevation Cladding 4mm", "ACP", "sqft"),
    _p("elevation-hpl", "building_elevations", "Merino", "Merino HPL Exterior Cladding", "HPL", "sqft"),
    # ---- unique lights ----
    _p("light-led-panel", "lights", "Philips", "Philips LED Panel Light 18W", "LED Panel", "pcs"),
    _p("light-facade", "lights", "", "Architectural Facade Light (IP65)", "Facade", "pcs"),
    # ---- home automation ----
    _p("auto-smart-switch", "home_automation", "Wipro", "Wipro Smart Switch Board", "Switch Board", "pcs"),
    _p("auto-door-lock", "home_automation", "Yale", "Yale Smart Door Lock", "Door Lock", "pcs"),
    _p("auto-security-sensor", "home_automation", "Godrej", "Godrej Home Safety Sensor", "Sensor", "pcs"),
    _p("auto-wifi-gateway", "home_automation", "", "Home Automation Gateway + WiFi Router", "Gateway", "pcs"),
]


def seed() -> int:
    db = SessionLocal()
    added = prod_added = updated = 0
    try:
        for m in MATERIALS:
            existing = db.get(Material, m["id"])
            if existing is None:
                db.add(Material(**m))
                added += 1
            else:
                # Normalize display fields to the page-3 wording (leave per_sqft as configured so the
                # structural auto-plan coefficients are never disturbed).
                changed = False
                for f in ("name", "category", "segment", "unit"):
                    if getattr(existing, f) != m[f]:
                        setattr(existing, f, m[f])
                        changed = True
                if changed:
                    updated += 1
        for p in PRODUCTS:
            if db.get(Product, p["id"]) is None:
                db.add(Product(**p))
                prod_added += 1
        db.commit()
    finally:
        db.close()
    print(f"[seed] catalog ensured; {added} new materials, {updated} normalized, "
          f"{prod_added} new products ({len(MATERIALS)} categories, {len(PRODUCTS)} product lines total)")
    return added


if __name__ == "__main__":
    seed()
