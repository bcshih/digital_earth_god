"""
Extract 台南市中西區 village boundaries from NLSC shapefile
and update the spatialBoundary in dijizu_agent_new/*.json files.

Usage: python scripts/update_boundaries.py
"""

import json
import struct
from pathlib import Path

SHP_DIR   = Path(r"C:\Users\User\Downloads\OFiles_1fddfa2b-1ef5-4d1e-9116-cff8b4d9b8e6")
SHP_FILE  = SHP_DIR / "VILLAGE_NLSC_1150511.shp"
DBF_FILE  = SHP_DIR / "VILLAGE_NLSC_1150511.dbf"
SHX_FILE  = SHP_DIR / "VILLAGE_NLSC_1150511.shx"
AGENT_DIR = Path(__file__).resolve().parents[1] / "dijizu_agent_new"

# UTF-8 bytes for 中西 (partial match covers 中西區 in any county)
ZHONGXI_BYTES = b"\xe4\xb8\xad\xe8\xa5\xbf"


# ── 1. Read DBF ───────────────────────────────────────────────────────────────

def read_dbf_fields(f):
    fields = []
    while True:
        b = f.read(32)
        if b[0] == 0x0D:
            break
        name   = b[:11].replace(b"\x00", b"").decode("ascii", "ignore").strip()
        length = b[16]
        fields.append((name, length))
    return fields


def find_zhongxi_records():
    """Returns {village_name: dbf_index} for all 中西區 villages."""
    with open(DBF_FILE, "rb") as f:
        f.read(4)
        num_records = struct.unpack("<I", f.read(4))[0]
        header_size = struct.unpack("<H", f.read(2))[0]
        record_size = struct.unpack("<H", f.read(2))[0]
        f.read(20)
        fields = read_dbf_fields(f)

        f.seek(header_size)
        result = {}
        for i in range(num_records):
            raw = f.read(record_size)
            if not raw:
                break
            if raw[0:1] == b"*":  # deleted
                continue
            offset = 1
            row = {}
            for name, length in fields:
                row[name] = raw[offset : offset + length]
                offset += length

            if ZHONGXI_BYTES in row["TOWNNAME"]:
                vill = row["VILLNAME"].rstrip(b"\x00 ").decode("utf-8")
                result[vill] = i

    return result


# ── 2. Read SHX ──────────────────────────────────────────────────────────────

def read_shx():
    offsets = []
    with open(SHX_FILE, "rb") as f:
        f.seek(100)
        while True:
            raw = f.read(8)
            if len(raw) < 8:
                break
            offset  = struct.unpack(">I", raw[0:4])[0] * 2
            content = struct.unpack(">I", raw[4:8])[0] * 2
            offsets.append((offset, content))
    return offsets


# ── 3. Read polygon from SHP ──────────────────────────────────────────────────

def read_polygon(shp_file, byte_offset):
    with open(shp_file, "rb") as f:
        f.seek(byte_offset + 8)          # skip 8-byte record header
        shape_type = struct.unpack("<i", f.read(4))[0]

        if shape_type not in (5, 15, 25):  # Polygon types
            return None

        f.read(32)                        # bounding box

        num_parts  = struct.unpack("<i", f.read(4))[0]
        num_points = struct.unpack("<i", f.read(4))[0]
        parts      = [struct.unpack("<i", f.read(4))[0] for _ in range(num_parts)]

        points = []
        for _ in range(num_points):
            x, y = struct.unpack("<dd", f.read(16))
            points.append([round(x, 6), round(y, 6)])

        rings = []
        for idx, start in enumerate(parts):
            end = parts[idx + 1] if idx + 1 < num_parts else num_points
            rings.append(points[start:end])

        return rings


# ── 4. Update agent JSON files ────────────────────────────────────────────────

def update_agents(name_to_rings):
    agent_files = sorted(AGENT_DIR.glob("*.json"))
    print(f"\nUpdating agent files in {AGENT_DIR}/")

    updated   = []
    not_found = []

    for path in agent_files:
        village_name = path.stem

        if village_name not in name_to_rings:
            not_found.append(village_name)
            continue

        rings = name_to_rings[village_name]

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        changed = False
        for node in data.get("@graph", []):
            if node.get("type") == "VillageAgent":
                node["spatialBoundary"] = {
                    "type": "GeoProperty",
                    "value": {
                        "type": "Polygon",
                        "coordinates": rings,
                    },
                }
                changed = True
                break

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            updated.append(village_name)
        else:
            print(f"  WARNING: no VillageAgent node found in {path.name}")

    print(f"\nUpdated ({len(updated)}): {updated}")
    if not_found:
        print(f"No NLSC match ({len(not_found)}): {not_found}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Step 1: Scanning DBF for Zhongxi villages...")
    village_to_idx = find_zhongxi_records()
    print(f"  Found {len(village_to_idx)} villages: {sorted(village_to_idx)}")

    print("\nStep 2: Reading SHX offsets...")
    offsets = read_shx()
    print(f"  {len(offsets)} records in SHX")

    print("\nStep 3: Extracting polygons from SHP...")
    name_to_rings = {}
    for vill, idx in village_to_idx.items():
        byte_off, _ = offsets[idx]
        rings = read_polygon(SHP_FILE, byte_off)
        if rings:
            total_pts = sum(len(r) for r in rings)
            print(f"  {vill}: {len(rings)} ring(s), {total_pts} points")
            name_to_rings[vill] = rings
        else:
            print(f"  WARNING: no polygon for {vill}")

    print("\nStep 4: Updating agent JSON files...")
    update_agents(name_to_rings)
    print("\nDone.")
