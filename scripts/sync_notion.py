#!/usr/bin/env python3
"""
Sync KiCad project to Notion.

1. Create/update the project page in Projekte database with structured content:
   - BOM table, hardware info, firmware info, links
2. Sync unique components to Bauteil-Bibliothek database.

Required env var:  NOTION_TOKEN
Optional env vars: NOTION_PROJEKTE_DB_ID, NOTION_BAUTEIL_DB_ID
"""

import os
import re
import sys
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
    def _request(method, url, headers, data=None):
        r = requests.request(method, url, headers=headers, json=data, timeout=30)
        return r.json()
except ImportError:
    import urllib.request, urllib.error
    def _request(method, url, headers, data=None):
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

NOTION_TOKEN     = os.environ.get("NOTION_TOKEN", "")
PROJEKTE_DB_ID   = os.environ.get("NOTION_PROJEKTE_DB_ID", "359d2e49b98481fb83c2e2e3f1a9edbb")
BAUTEIL_DB_ID    = os.environ.get("NOTION_DB_ID",          "359d2e49b98481cab9d9dbb713c3c048")
NOTION_VERSION   = "2022-06-28"

TYPE_MAP = {
    "Device:R": "Widerstand", "Device:C": "Kondensator", "Device:L": "Induktivität",
    "Device:D": "Diode",      "Device:LED": "LED",        "Transistor": "Transistor",
    "Pico": "Mikrocontroller","DRV": "IC / Treiber",      "PC817": "Optokoppler",
    "L7805": "Spannungsregler","IRF": "MOSFET",           "BTS": "High-Side Switch",
    "TB6612": "Motortreiber", "1.5KE": "TVS-Diode",       "1190": "Steckverbinder",
}

# ── Notion API ────────────────────────────────────────────────────────────────

def notion(method, path, data=None):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    result = _request(method, f"https://api.notion.com/v1{path}", headers, data)
    time.sleep(0.35)  # stay within 3 req/s rate limit
    return result

# ── Git info ──────────────────────────────────────────────────────────────────

def git(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def get_project_info():
    remote = git(["git", "remote", "get-url", "origin"])
    # https://github.com/User/Repo.git  or  git@github.com:User/Repo.git
    m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", remote)
    slug = m.group(1) if m else ""
    name = slug.split("/")[-1].replace("_", " ").replace("-", " ") if slug else Path.cwd().name
    github_url = f"https://github.com/{slug}" if slug else ""
    return name, github_url

# ── KiCad schematic parser ───────────────────────────────────────────────────

def parse_property(block, name):
    m = re.search(rf'\(property\s+"{re.escape(name)}"\s+"([^"]*)"', block)
    return m.group(1) if m else ""

def parse_schematic(sch_path):
    content = Path(sch_path).read_text(encoding="utf-8")
    # skip lib_symbols section
    ls_start = content.find("(lib_symbols")
    depth, pos = 0, ls_start
    for i, ch in enumerate(content[ls_start:], ls_start):
        if ch == "(": depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0: pos = i + 1; break
    placed = content[pos:]

    components = []
    for sm in re.finditer(r"\n\t\(symbol\b", "\n" + placed):
        start = sm.start() + 1
        depth, end = 0, start
        for i, ch in enumerate(placed[start:], start):
            if ch == "(": depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0: end = i + 1; break
        block = placed[start:end]
        if "(dnp yes)" in block or "(in_bom no)" in block: continue
        lib_id_m = re.search(r'\(lib_id\s+"([^"]+)"', block)
        if not lib_id_m: continue
        lib_id = lib_id_m.group(1)
        if lib_id.startswith("power:") or lib_id.startswith("PWR_FLAG"): continue
        reference = parse_property(block, "Reference")
        if reference.startswith("#"): continue
        components.append({
            "lib_id": lib_id,
            "reference": reference,
            "value": parse_property(block, "Value"),
            "footprint": parse_property(block, "Footprint"),
            "description": parse_property(block, "Description"),
            "manufacturer": parse_property(block, "MF"),
        })
    return components

def group_bom(components):
    groups = {}
    for c in components:
        key = f"{c['value']}|{c['footprint']}"
        if key not in groups:
            groups[key] = {**c, "references": []}
        groups[key]["references"].append(c["reference"])
    bom = list(groups.values())
    return [c for c in bom if c["value"] not in ("R_Small","C_Small","L_Small","")]

def guess_type(lib_id, value):
    combined = lib_id + " " + value
    for key, t in TYPE_MAP.items():
        if key.lower() in combined.lower():
            return t
    if lib_id.startswith("Device:R"): return "Widerstand"
    if lib_id.startswith("Device:C"): return "Kondensator"
    if lib_id.startswith("Device:D") or "diode" in lib_id.lower(): return "Diode"
    return "Sonstiges"

# ── Notion page content builder ───────────────────────────────────────────────

def txt(content, **kwargs):
    return {"type": "text", "text": {"content": content, **kwargs}}

def link_txt(content, url):
    return {"type": "text", "text": {"content": content, "link": {"url": url}}}

def h2(content):
    return {"type": "heading_2", "heading_2": {"rich_text": [txt(content)], "color": "default"}}

def h3(content):
    return {"type": "heading_3", "heading_3": {"rich_text": [txt(content)], "color": "default"}}

def paragraph(content, url=None):
    rt = link_txt(content, url) if url else txt(content)
    return {"type": "paragraph", "paragraph": {"rich_text": [rt]}}

def bullet(content, url=None):
    rt = link_txt(content, url) if url else txt(content)
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [rt]}}

def divider():
    return {"type": "divider", "divider": {}}

def callout(content, emoji="ℹ️"):
    return {
        "type": "callout",
        "callout": {
            "rich_text": [txt(content)],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": "gray_background",
        }
    }

def bom_table(bom):
    header = ["Wert", "Referenz(en)", "Anzahl", "Package", "Hersteller", "Typ"]
    rows = [header]
    for c in sorted(bom, key=lambda x: (guess_type(x["lib_id"], x["value"]), x["value"])):
        refs = ", ".join(sorted(c["references"]))
        pkg  = c["footprint"].split(":")[-1] if ":" in c["footprint"] else c["footprint"]
        rows.append([
            c["value"], refs, str(len(c["references"])),
            pkg[:60], c["manufacturer"], guess_type(c["lib_id"], c["value"]),
        ])
    return {
        "type": "table",
        "table": {
            "table_width": len(header),
            "has_column_header": True,
            "has_row_header": False,
            "children": [
                {"type": "table_row", "table_row": {
                    "cells": [[txt(cell)] for cell in row]
                }}
                for row in rows
            ],
        }
    }

def build_page_blocks(bom, github_url, project_name):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    blocks = []

    # Hardware section
    blocks.append(h2("Hardware"))
    if github_url:
        blocks.append(bullet(f"GitHub: {github_url}", url=github_url))
    blocks.append(bullet("Schaltplan: hardware/"))
    blocks.append(bullet("Gerbers: hardware/gerbers/"))
    blocks.append(divider())

    # BOM
    if bom:
        blocks.append(h3(f"Stückliste – {len(bom)} Bauteile"))
        blocks.append(bom_table(bom))
        blocks.append(divider())

    # Firmware section
    blocks.append(h2("Firmware"))
    blocks.append(bullet("Sprache: MicroPython"))
    blocks.append(bullet("Einstiegspunkt: firmware/main.py"))
    blocks.append(bullet("Deployment: MicroPico → \"Upload Project to Pico\""))
    blocks.append(divider())

    # Footer
    blocks.append(callout(f"Zuletzt synchronisiert: {now}", emoji="🤖"))

    return blocks

# ── Notion project page ───────────────────────────────────────────────────────

def find_project_page(name):
    result = notion("POST", f"/databases/{PROJEKTE_DB_ID}/query", {
        "filter": {"property": "Name", "title": {"equals": name}},
        "page_size": 1,
    })
    results = result.get("results", [])
    return results[0]["id"] if results else None

def create_project_page(name, github_url):
    props = {
        "Name": {"title": [{"text": {"content": name}}]},
        "Status": {"select": {"name": "In Arbeit"}},
    }
    if github_url:
        props["GitHub URL"] = {"url": github_url}
    result = notion("POST", "/pages", {
        "parent": {"database_id": PROJEKTE_DB_ID},
        "properties": props,
    })
    return result.get("id")

def clear_page_blocks(page_id):
    result = notion("GET", f"/blocks/{page_id}/children?page_size=100")
    for block in result.get("results", []):
        notion("DELETE", f"/blocks/{block['id']}")

def append_blocks(page_id, blocks):
    # Notion allows max 100 blocks per request
    for i in range(0, len(blocks), 100):
        notion("PATCH", f"/blocks/{page_id}/children", {"children": blocks[i:i+100]})

def sync_project_page(name, github_url, bom):
    print(f"  Syncing Notion project page for \"{name}\"...")
    page_id = find_project_page(name)
    if page_id:
        print(f"  Found existing page, updating content...")
        clear_page_blocks(page_id)
    else:
        print(f"  Creating new project page...")
        page_id = create_project_page(name, github_url)

    blocks = build_page_blocks(bom, github_url, name)
    append_blocks(page_id, blocks)
    print(f"  Project page updated with {len(bom)} BOM entries.")
    return page_id

# ── Bauteil-Bibliothek sync ───────────────────────────────────────────────────

def query_existing_bauteil(name):
    result = notion("POST", f"/databases/{BAUTEIL_DB_ID}/query", {
        "filter": {"property": "Name", "title": {"equals": name}},
        "page_size": 1,
    })
    results = result.get("results", [])
    return results[0]["id"] if results else None

def sync_bauteil(comp):
    name = comp["value"]
    pkg  = comp["footprint"].split(":")[-1] if ":" in comp["footprint"] else comp["footprint"]
    props = {
        "Name":     {"title":     [{"text": {"content": name}}]},
        "Typ":      {"select":    {"name": guess_type(comp["lib_id"], name)}},
        "Funktion": {"rich_text": [{"text": {"content": (comp["description"] or name)[:2000]}}]},
    }
    if pkg:
        props["Package"] = {"select": {"name": pkg[:100]}}
    if comp["manufacturer"]:
        props["Hersteller"] = {"rich_text": [{"text": {"content": comp["manufacturer"]}}]}

    existing_id = query_existing_bauteil(name)
    if existing_id:
        notion("PATCH", f"/pages/{existing_id}", {"properties": props})
        return "updated"
    else:
        notion("POST", "/pages", {"parent": {"database_id": BAUTEIL_DB_ID}, "properties": props})
        return "created"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not NOTION_TOKEN:
        print("ERROR: NOTION_TOKEN not set"); sys.exit(1)

    sch_files = list(Path(".").glob("hardware/*.kicad_sch"))
    if not sch_files:
        sch_files = list(Path(".").glob("**/*.kicad_sch"))

    project_name, github_url = get_project_info()
    print(f"Project: {project_name}")
    print(f"GitHub:  {github_url or '(no remote)'}")

    bom = []
    if sch_files:
        for sch in sch_files:
            print(f"Parsing {sch}...")
            bom.extend(parse_schematic(sch))
        bom = group_bom(bom)
        print(f"Found {len(bom)} unique components.")
    else:
        print("No .kicad_sch files found – creating project page without BOM.")

    # 1. Update project page
    print("\nUpdating Notion project page...")
    sync_project_page(project_name, github_url, bom)

    # 2. Sync to Bauteil-Bibliothek
    if bom:
        print("\nSyncing to Bauteil-Bibliothek...")
        counts = {"created": 0, "updated": 0}
        for comp in bom:
            counts[sync_bauteil(comp)] += 1
        print(f"  {counts['created']} created, {counts['updated']} updated.")

    print("\nDone.")

if __name__ == "__main__":
    main()
