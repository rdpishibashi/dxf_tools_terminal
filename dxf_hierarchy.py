#!/usr/bin/env python
import sys
import ezdxf
import argparse
from io import StringIO

try:
    from ezdxf.lldxf.writer import TagWriter  # ezdxf >= 0.19
except ImportError:
    from ezdxf.lldxf.tagwriter import TagWriter  # ezdxf < 0.19

def get_group_code_meaning(code):
    code_meanings = {
        0: "Entity Type", 1: "Primary Text String", 2: "Name", 3: "Additional Text",
        5: "Handle", 6: "Linetype", 7: "Text Style Name", 8: "Layer Name", 9: "Variable Name",
        10: "X Coordinate (Main)", 20: "Y Coordinate (Main)", 30: "Z Coordinate (Main)",
        40: "Double Precision Value", 50: "Angle", 62: "Color Number", 70: "Integer Value",
        210: "X Direction Vector", 220: "Y Direction Vector", 230: "Z Direction Vector", 999: "Comment"
    }
    return code_meanings.get(code, "Other")

def extract_hierarchy(doc):
    hierarchy = []

    # HEADER
    hierarchy.append("# SECTION: HEADER")

    # TABLES
    hierarchy.append("# SECTION: TABLES")
    for table_name, table in {
        'LAYERS': doc.layers,
        'LTYPE': doc.linetypes,
        'STYLES': doc.styles,
        'DIMSTYLES': doc.dimstyles,
        'UCS': doc.ucs
    }.items():
        hierarchy.append(f"## TABLE: {table_name}")
        for entry in table:
            hierarchy.append(f"### ENTRY: {entry.dxf.name}")
            for key, value in entry.dxf.all_existing_dxf_attribs().items():
                hierarchy.append(f"- {key}: {value}")

    # BLOCKS
    hierarchy.append("# SECTION: BLOCKS")
    for block in doc.blocks:
        hierarchy.append(f"## BLOCK: {block.name}")
        for entity in block:
            hierarchy.append(f"### ENTITY: {entity.dxftype()}")
            hierarchy.extend(get_sorted_entity_tags(entity))

    # ENTITIES
    hierarchy.append("# SECTION: ENTITIES")
    msp = doc.modelspace()
    for entity in msp:
        hierarchy.append(f"## ENTITY: {entity.dxftype()}")
        hierarchy.extend(get_sorted_entity_tags(entity))

    # OBJECTS
    hierarchy.append("# SECTION: OBJECTS")
    for obj in doc.objects:
        hierarchy.append(f"## OBJECT: {obj.dxftype()}")
        hierarchy.extend(get_sorted_entity_tags(obj))

    # CLASSES
    hierarchy.append("# SECTION: CLASSES (if present)")

    return hierarchy

def get_sorted_entity_tags(entity):
    buffer = StringIO()
    tagwriter = TagWriter(buffer)
    entity.export_dxf(tagwriter)
    buffer.seek(0)
    lines = buffer.readlines()

    tags = []
    for i in range(0, len(lines)-1, 2):
        code = lines[i].strip()
        value = lines[i+1].strip()
        if code.isdigit():
            code_int = int(code)
            meaning = get_group_code_meaning(code_int)
            tags.append((code_int, meaning, value))

    tags.sort(key=lambda x: x[0])

    return [f"- {code} ({meaning}): {value}" for code, meaning, value in tags]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DXF階層構造をMarkdownで出力')
    parser.add_argument('input_dxf', help='入力DXFファイル')
    parser.add_argument('output_file', help='出力ファイル（.md）')
    args = parser.parse_args()

    if not args.output_file.endswith('.md') or not args.output_file.endswith('.txt'):
        print("⚠️  警告: 出力ファイルの拡張子は '.txt' か '.md' です。")
        sys.exit(1)

    doc = ezdxf.readfile(args.input_dxf)
    hierarchy = extract_hierarchy(doc)

    with open(args.output_file, 'w', encoding='utf-8') as f:
        for line in hierarchy:
            f.write(line + "\n")

    print(f"Markdown出力完了: {args.output_file}")
