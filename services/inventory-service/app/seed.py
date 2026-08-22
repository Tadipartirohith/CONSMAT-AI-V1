"""Seed the materials reference data (idempotent). Run after migrations.

Usage: python -m app.seed

The catalog mirrors consmat.in's breadth: structural materials (cement/steel/sand/aggregate/bricks)
carry a `per_sqft` BOM coefficient so the legacy auto-plan can quantify them; finishing / MEP / interior
categories use `per_sqft = 0` and are quantified through the CE/architect product BOM with an explicit
phase (they dispatch on the phase they are assigned to, independent of the weight matrix).
"""
from __future__ import annotations

from decimal import Decimal

from .db import SessionLocal
from .models import Material, Product

_0 = Decimal("0")

# Structural materials keep their per_sqft coefficient; every new category is quantified via the BOM.
MATERIALS = [
    # --- structural (auto-plan uses per_sqft) ---
    {"id": "cement", "name": "Cement", "category": "binder", "unit": "bags",
     "grade": "OPC 53-Grade", "per_sqft": Decimal("0.40")},
    {"id": "steel", "name": "TMT Steel", "category": "reinforcement", "unit": "tonnes",
     "grade": "Fe 500D", "per_sqft": Decimal("0.004")},
    {"id": "sand", "name": "River Sand", "category": "aggregate", "unit": "tonnes",
     "grade": "Fine (plastering)", "per_sqft": Decimal("0.0816")},
    {"id": "aggregate", "name": "Aggregate 20mm", "category": "aggregate", "unit": "tonnes",
     "grade": "20mm blue metal", "per_sqft": Decimal("0.057")},
    {"id": "bricks", "name": "Bricks", "category": "masonry", "unit": "pcs",
     "grade": "Class-A red clay", "per_sqft": Decimal("8.0")},
    # --- concrete / masonry ---
    {"id": "rmc", "name": "Ready-Mix Concrete", "category": "concrete", "unit": "cum", "grade": "M-grade", "per_sqft": _0},
    {"id": "blocks", "name": "Concrete & AAC Blocks", "category": "masonry", "unit": "pcs", "grade": "", "per_sqft": _0},
    # --- structural systems ---
    {"id": "formwork", "name": "Aluminium Formwork", "category": "formwork", "unit": "sqft", "grade": "", "per_sqft": _0},
    # --- MEP ---
    {"id": "pipes", "name": "MS & GI Pipes", "category": "mep", "unit": "m", "grade": "", "per_sqft": _0},
    {"id": "plumbing", "name": "Plumbing & Sanitaryware", "category": "mep", "unit": "pcs", "grade": "", "per_sqft": _0},
    {"id": "electrical", "name": "Electrical Fittings", "category": "mep", "unit": "pcs", "grade": "", "per_sqft": _0},
    {"id": "wires", "name": "Wires & Cables", "category": "mep", "unit": "coil", "grade": "", "per_sqft": _0},
    # --- finishing / interiors ---
    {"id": "tiles", "name": "Flooring & Wall Tiles", "category": "finishing", "unit": "box", "grade": "", "per_sqft": _0},
    {"id": "paints", "name": "Paints & Coatings", "category": "finishing", "unit": "ltr", "grade": "", "per_sqft": _0},
    {"id": "waterproofing", "name": "Waterproofing & Admixtures", "category": "finishing", "unit": "kg", "grade": "", "per_sqft": _0},
    {"id": "adhesives", "name": "Tile Adhesives & Grouts", "category": "finishing", "unit": "bags", "grade": "", "per_sqft": _0},
    {"id": "plywood", "name": "Plywood & Boards", "category": "interior", "unit": "sheet", "grade": "", "per_sqft": _0},
    {"id": "doors", "name": "Doors & Windows", "category": "interior", "unit": "pcs", "grade": "", "per_sqft": _0},
    {"id": "glass", "name": "Glass & Facade", "category": "interior", "unit": "sqft", "grade": "", "per_sqft": _0},
    {"id": "hardware", "name": "Hardware & Fasteners", "category": "interior", "unit": "pcs", "grade": "", "per_sqft": _0},
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
    # ---- steel (TMT) ----
    _p("steel-tata-tiscon", "steel", "TATA", "TATA Tiscon 500D TMT Bar", "Fe 500D", "tonnes"),
    _p("steel-jsw-neosteel", "steel", "JSW", "JSW Neosteel 550D TMT Bar", "Fe 550D", "tonnes"),
    _p("steel-sail-tmt", "steel", "SAIL", "SAIL TMT Fe 500 Bar", "Fe 500", "tonnes"),
    _p("steel-vizag-tmt", "steel", "Vizag", "Vizag Steel TMT Fe 500D Bar", "Fe 500D", "tonnes"),
    _p("steel-kamdhenu-nxt", "steel", "Kamdhenu", "Kamdhenu NXT 550D TMT Bar", "Fe 550D", "tonnes"),
    _p("steel-jindal-panther", "steel", "Jindal", "Jindal Panther Fe 500D TMT Bar", "Fe 500D", "tonnes"),
    # ---- sand ----
    _p("sand-river-fine", "sand", "", "River Sand (Fine, plastering grade)", "Fine", "tonnes"),
    _p("sand-msand", "sand", "", "Manufactured Sand (M-Sand) for concrete", "M-Sand", "tonnes"),
    _p("sand-psand", "sand", "", "Plastering Sand (P-Sand)", "P-Sand", "tonnes"),
    # ---- aggregate ----
    _p("aggregate-20mm-blue", "aggregate", "", "20mm Blue Metal Aggregate", "20mm", "tonnes"),
    _p("aggregate-12mm", "aggregate", "", "12mm Crushed Stone Aggregate", "12mm", "tonnes"),
    _p("aggregate-40mm", "aggregate", "", "40mm Crushed Stone Aggregate", "40mm", "tonnes"),
    _p("aggregate-gsb", "aggregate", "", "GSB / Crusher Dust", "GSB", "tonnes"),
    # ---- bricks ----
    _p("bricks-redclay-a", "bricks", "", "Class-A Red Clay Bricks", "Class-A", "pcs"),
    _p("bricks-wirecut", "bricks", "", "Wire-cut Red Bricks", "Wire-cut", "pcs"),
    _p("bricks-flyash", "bricks", "", "Fly Ash Bricks", "Fly Ash", "pcs"),
    # ---- ready-mix concrete ----
    _p("rmc-m20", "rmc", "ACC", "ACC RMC M20 Grade", "M20", "cum"),
    _p("rmc-m25", "rmc", "UltraTech", "UltraTech Concrete RMC M25", "M25", "cum"),
    _p("rmc-m30", "rmc", "Godrej", "Godrej RMC M30 Grade", "M30", "cum"),
    _p("rmc-m35", "rmc", "RDC", "RDC RMC M35 Grade", "M35", "cum"),
    _p("rmc-selfcompact", "rmc", "UltraTech", "UltraTech Self-Compacting Concrete", "SCC", "cum"),
    # ---- concrete & AAC blocks ----
    _p("blocks-aac-600", "blocks", "Magicrete", "Magicrete AAC Block 600x200x100", "AAC", "pcs"),
    _p("blocks-aac-biltech", "blocks", "Biltech", "Biltech Aerocon AAC Block 600x200x150", "AAC", "pcs"),
    _p("blocks-solid-cc", "blocks", "", "Solid Concrete Block 400x200x200", "Solid CC", "pcs"),
    _p("blocks-hollow-cc", "blocks", "", "Hollow Concrete Block 400x200x200", "Hollow", "pcs"),
    _p("blocks-flyash-block", "blocks", "", "Fly Ash Solid Block", "Fly Ash", "pcs"),
    # ---- aluminium formwork ----
    _p("formwork-alu-wall", "formwork", "MFE", "MFE Aluminium Wall Formwork Panel", "Wall", "sqft"),
    _p("formwork-alu-slab", "formwork", "PERI", "PERI Aluminium Slab Formwork", "Slab", "sqft"),
    _p("formwork-alu-column", "formwork", "Kumkang", "Kumkang Aluminium Column Formwork", "Column", "sqft"),
    _p("formwork-ply-shuttering", "formwork", "", "Film-faced Shuttering Plywood 12mm", "Shuttering", "sheet"),
    # ---- MS & GI pipes ----
    _p("pipes-gi-tata", "pipes", "TATA", "TATA GI Pipe 2 inch (medium)", "GI", "m"),
    _p("pipes-gi-jindal", "pipes", "Jindal", "Jindal GI Pipe 1 inch", "GI", "m"),
    _p("pipes-ms-square", "pipes", "APL Apollo", "APL Apollo MS Square Pipe 50x50", "MS", "m"),
    _p("pipes-ms-round", "pipes", "Surya", "Surya MS Round Pipe 25mm", "MS", "m"),
    _p("pipes-gi-conduit", "pipes", "BEC", "BEC GI Conduit Pipe 25mm", "Conduit", "m"),
    _p("pipes-cpvc-astral", "pipes", "Astral", "Astral CPVC Pipe 3/4 inch", "CPVC", "m"),
    # ---- plumbing & sanitaryware ----
    _p("plumbing-upvc-supreme", "plumbing", "Supreme", "Supreme UPVC Pipe 4 inch (drainage)", "UPVC", "m"),
    _p("plumbing-cpvc-ashirvad", "plumbing", "Ashirvad", "Ashirvad Flowguard CPVC Pipe 1 inch", "CPVC", "m"),
    _p("plumbing-finolex-pvc", "plumbing", "Finolex", "Finolex PVC Pipe 2 inch", "PVC", "m"),
    _p("plumbing-jaquar-faucet", "plumbing", "Jaquar", "Jaquar Continental Pillar Cock", "Faucet", "pcs"),
    _p("plumbing-hindware-wc", "plumbing", "Hindware", "Hindware Wall-Hung Water Closet", "WC", "pcs"),
    _p("plumbing-cera-basin", "plumbing", "Cera", "Cera Wash Basin (Table Top)", "Basin", "pcs"),
    _p("plumbing-parryware-sink", "plumbing", "Parryware", "Parryware Kitchen Sink SS", "Sink", "pcs"),
    _p("plumbing-kohler-mixer", "plumbing", "Kohler", "Kohler Single-Lever Basin Mixer", "Mixer", "pcs"),
    _p("plumbing-watertank-sintex", "plumbing", "Sintex", "Sintex Water Tank 1000L", "Tank", "pcs"),
    _p("plumbing-gate-valve", "plumbing", "Zoloto", "Zoloto Brass Gate Valve 1 inch", "Valve", "pcs"),
    # ---- electrical fittings ----
    _p("electrical-switch-anchor", "electrical", "Anchor", "Anchor Roma Modular Switch 6A", "Switch", "pcs"),
    _p("electrical-switch-legrand", "electrical", "Legrand", "Legrand Myrius Modular Switch", "Switch", "pcs"),
    _p("electrical-mcb-havells", "electrical", "Havells", "Havells MCB 32A SP", "MCB", "pcs"),
    _p("electrical-db-schneider", "electrical", "Schneider", "Schneider 8-Way Distribution Board", "DB", "pcs"),
    _p("electrical-socket-ge", "electrical", "GM", "GM 16A Modular Socket", "Socket", "pcs"),
    _p("electrical-fan-crompton", "electrical", "Crompton", "Crompton Ceiling Fan 1200mm", "Fan", "pcs"),
    _p("electrical-led-philips", "electrical", "Philips", "Philips LED Panel Light 18W", "LED", "pcs"),
    _p("electrical-conduit-precision", "electrical", "Precision", "Precision PVC Conduit 25mm", "Conduit", "m"),
    # ---- wires & cables ----
    _p("wires-finolex-15", "wires", "Finolex", "Finolex FR Wire 1.5 sqmm (90m)", "1.5sqmm", "coil"),
    _p("wires-polycab-25", "wires", "Polycab", "Polycab FR Wire 2.5 sqmm (90m)", "2.5sqmm", "coil"),
    _p("wires-havells-40", "wires", "Havells", "Havells Life Line Wire 4.0 sqmm", "4.0sqmm", "coil"),
    _p("wires-rr-6", "wires", "RR Kabel", "RR Kabel Wire 6.0 sqmm", "6.0sqmm", "coil"),
    _p("wires-kei-multicore", "wires", "KEI", "KEI 3-Core Flexible Cable 4sqmm", "3-core", "coil"),
    _p("wires-anchor-1", "wires", "Anchor", "Anchor Advance FR Wire 1.0 sqmm", "1.0sqmm", "coil"),
    # ---- flooring & wall tiles ----
    _p("tiles-kajaria-vitrified", "tiles", "Kajaria", "Kajaria Vitrified Tile 600x600 Glossy", "Vitrified", "box"),
    _p("tiles-somany-gvt", "tiles", "Somany", "Somany GVT Tile 800x800", "GVT", "box"),
    _p("tiles-johnson-ceramic", "tiles", "Johnson", "Johnson Ceramic Wall Tile 300x600", "Ceramic", "box"),
    _p("tiles-nitco-marble", "tiles", "Nitco", "Nitco Marble-Finish Tile 600x1200", "Vitrified", "box"),
    _p("tiles-rak-porcelain", "tiles", "RAK", "RAK Porcelain Tile 600x600", "Porcelain", "box"),
    _p("tiles-orient-double", "tiles", "Orient Bell", "Orient Bell Double-Charge Tile 600x600", "Vitrified", "box"),
    _p("tiles-granite-slab", "tiles", "", "Granite Slab (Jet Black) polished", "Granite", "sqft"),
    _p("tiles-marble-slab", "tiles", "", "Imported Marble Slab", "Marble", "sqft"),
    # ---- paints & coatings ----
    _p("paints-asian-apex", "paints", "Asian Paints", "Asian Paints Apex Ultima Exterior 20L", "Exterior", "ltr"),
    _p("paints-asian-royale", "paints", "Asian Paints", "Asian Paints Royale Luxury Emulsion 20L", "Interior", "ltr"),
    _p("paints-berger-weathercoat", "paints", "Berger", "Berger WeatherCoat Anti-Dust 20L", "Exterior", "ltr"),
    _p("paints-nerolac-excel", "paints", "Nerolac", "Nerolac Excel Total Exterior 20L", "Exterior", "ltr"),
    _p("paints-dulux-velvet", "paints", "Dulux", "Dulux Velvet Touch Interior 20L", "Interior", "ltr"),
    _p("paints-putty-jk", "paints", "JK", "JK Wall Putty 40kg", "Putty", "bags"),
    _p("paints-primer-asian", "paints", "Asian Paints", "Asian Paints Wall Primer 20L", "Primer", "ltr"),
    _p("paints-enamel-berger", "paints", "Berger", "Berger Luxol Synthetic Enamel 4L", "Enamel", "ltr"),
    _p("paints-birla-putty", "paints", "Birla", "Birla White Wall Care Putty 40kg", "Putty", "bags"),
    # ---- waterproofing & admixtures ----
    _p("wp-drfixit-lw", "waterproofing", "Dr. Fixit", "Dr. Fixit LW+ Integral Waterproofing 1L", "Admixture", "ltr"),
    _p("wp-drfixit-pidiproof", "waterproofing", "Dr. Fixit", "Dr. Fixit Pidiproof LW+ 20kg", "Coating", "kg"),
    _p("wp-fosroc-brushbond", "waterproofing", "Fosroc", "Fosroc Brushbond Crystalline 30kg", "Coating", "kg"),
    _p("wp-sika-latex", "waterproofing", "Sika", "Sika Latex Power Bonding Agent 5kg", "Bonding", "kg"),
    _p("wp-fevicol-sh", "waterproofing", "Pidilite", "Fevicol SR Synthetic Rubber 5kg", "Adhesive", "kg"),
    _p("wp-mycem-plast", "waterproofing", "MYK Laticrete", "MYK Laticrete Waterproof Membrane 20kg", "Membrane", "kg"),
    _p("wp-fosroc-conplast", "waterproofing", "Fosroc", "Fosroc Conplast SP430 Superplasticiser 5L", "Admixture", "ltr"),
    _p("wp-bitumen-coat", "waterproofing", "", "Bituminous Waterproof Coating 20L", "Bitumen", "ltr"),
    # ---- tile adhesives & grouts ----
    _p("adh-myk-tileadh", "adhesives", "MYK Laticrete", "MYK Laticrete Tile Adhesive Type-1 20kg", "Type-1", "bags"),
    _p("adh-roff-tileguard", "adhesives", "Roff", "Roff Tile Adhesive Type-3 20kg", "Type-3", "bags"),
    _p("adh-weber-set", "adhesives", "Weber", "Weberset Tile Adhesive 20kg", "Type-2", "bags"),
    _p("adh-roff-grout", "adhesives", "Roff", "Roff Epoxy Grout 1kg", "Grout", "pcs"),
    _p("adh-myk-grout", "adhesives", "MYK Laticrete", "MYK Laticrete Cementitious Grout 1kg", "Grout", "pcs"),
    _p("adh-drfixit-tileadh", "adhesives", "Dr. Fixit", "Dr. Fixit Roff Tile Adhesive 20kg", "Type-1", "bags"),
    # ---- plywood & boards ----
    _p("ply-century-mr", "plywood", "Century", "Century Club Prime MR Plywood 18mm", "MR", "sheet"),
    _p("ply-greenply-bwp", "plywood", "Greenply", "Greenply Green Club BWP Plywood 18mm", "BWP", "sheet"),
    _p("ply-kitply-mr", "plywood", "Kitply", "Kitply MR Grade Plywood 12mm", "MR", "sheet"),
    _p("ply-actionteso-block", "plywood", "Action Tesa", "Action Tesa HDHMR Board 18mm", "HDHMR", "sheet"),
    _p("ply-mdf-greenpanel", "plywood", "Greenpanel", "Greenpanel Plain MDF Board 12mm", "MDF", "sheet"),
    _p("ply-laminate-merino", "plywood", "Merino", "Merino Laminate Sheet 1mm", "Laminate", "sheet"),
    _p("ply-particle-board", "plywood", "", "Pre-laminated Particle Board 18mm", "PLB", "sheet"),
    # ---- doors & windows ----
    _p("doors-flush-century", "doors", "Century", "Century Flush Door 32mm", "Flush", "pcs"),
    _p("doors-wpc-frame", "doors", "", "WPC Door Frame", "WPC", "pcs"),
    _p("doors-upvc-window", "doors", "Fenesta", "Fenesta UPVC Sliding Window", "UPVC", "pcs"),
    _p("doors-alu-window", "doors", "Jindal", "Jindal Aluminium Window (2-track)", "Aluminium", "pcs"),
    _p("doors-main-teak", "doors", "", "Teak Wood Main Door (solid)", "Teak", "pcs"),
    # ---- glass & facade ----
    _p("glass-sg-clear", "glass", "Saint-Gobain", "Saint-Gobain Clear Float Glass 8mm", "Float", "sqft"),
    _p("glass-toughened", "glass", "Saint-Gobain", "Saint-Gobain Toughened Glass 10mm", "Toughened", "sqft"),
    _p("glass-acp-alstrong", "glass", "Alstrong", "Alstrong ACP Cladding Sheet 4mm", "ACP", "sqft"),
    _p("glass-dgu", "glass", "AIS", "AIS Double-Glazed Unit (DGU)", "DGU", "sqft"),
    _p("glass-mirror", "glass", "Modiguard", "Modiguard Mirror 5mm", "Mirror", "sqft"),
    # ---- hardware & fasteners ----
    _p("hw-hinges-hettich", "hardware", "Hettich", "Hettich Soft-Close Hinges (pair)", "Hinge", "pcs"),
    _p("hw-lock-godrej", "hardware", "Godrej", "Godrej Mortise Door Lock Set", "Lock", "pcs"),
    _p("hw-lock-europa", "hardware", "Europa", "Europa Cylindrical Lock", "Lock", "pcs"),
    _p("hw-channel-ebco", "hardware", "Ebco", "Ebco Telescopic Drawer Channel", "Channel", "pcs"),
    _p("hw-nails-1kg", "hardware", "", "Construction Nails (assorted) 1kg", "Nails", "pcs"),
    _p("hw-binding-wire", "hardware", "", "GI Binding Wire 18 SWG (1kg)", "Binding", "pcs"),
    _p("hw-anchor-fastener", "hardware", "Hilti", "Hilti Anchor Fastener M10", "Anchor", "pcs"),
    _p("hw-screws-box", "hardware", "", "Self-Tapping Screws (box of 200)", "Screws", "pcs"),
]


def seed() -> int:
    db = SessionLocal()
    added = 0
    prod_added = 0
    try:
        for m in MATERIALS:
            if db.get(Material, m["id"]) is None:
                db.add(Material(**m))
                added += 1
        for p in PRODUCTS:
            if db.get(Product, p["id"]) is None:
                db.add(Product(**p))
                prod_added += 1
        db.commit()
    finally:
        db.close()
    print(f"[seed] catalog ensured; {added} new materials, {prod_added} new products "
          f"({len(MATERIALS)} categories, {len(PRODUCTS)} product lines total)")
    return added


if __name__ == "__main__":
    seed()
