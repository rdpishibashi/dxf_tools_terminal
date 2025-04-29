#!/usr/bin/env python
import sys
import ezdxf
import argparse
import pandas as pd
from io import StringIO

# バージョンに応じた TagWriter のインポート
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

def extract_entity_data(section_name, entity):
    rows = []
    entity_type = entity.dxftype()

    buffer = StringIO()
    tagwriter = TagWriter(buffer)
    entity.export_dxf(tagwriter)
    buffer.seek(0)
    lines = buffer.readlines()

    for i in range(0, len(lines)-1, 2):
        code_line = lines[i].strip()
        value_line = lines[i+1].strip()
        if code_line.isdigit():
            code = int(code_line)
            meaning = get_group_code_meaning(code)
            rows.append([section_name, entity_type, code, meaning, value_line])

    return rows

def extract_table_data(section_name, table_entry):
    rows = []
    entry_type = table_entry.dxftype()
    for key, value in table_entry.dxf.all_existing_dxf_attribs().items():
        rows.append([section_name, entry_type, "-", "TABLE Entry", f"{key} = {value}"])
    return rows

def analyze_dxf_structure(dxf_file):
    doc = ezdxf.readfile(dxf_file)
    all_rows = []

    # HEADER
    for varname in doc.header.varnames():
        value = doc.header.get(varname)
        all_rows.append(['HEADER', 'HEADER_VAR', 9, "Variable Name", f"{varname} = {value}"])

    # TABLES
    for table_name, table in {
        'LAYERS': doc.layers,
        'LTYPE': doc.linetypes,
        'STYLES': doc.styles,
        'DIMSTYLES': doc.dimstyles,
        'UCS': doc.ucs
    }.items():
        for entry in table:
            all_rows.extend(extract_table_data(f"TABLES({table_name})", entry))

    # BLOCKS
    for block in doc.blocks:
        for entity in block:
            all_rows.extend(extract_entity_data('BLOCKS', entity))

    # ENTITIES
    msp = doc.modelspace()
    for entity in msp:
        all_rows.extend(extract_entity_data('ENTITIES', entity))

    # OBJECTS
    for obj in doc.objects:
        all_rows.extend(extract_entity_data('OBJECTS', obj))

    # CLASSES コメント行
    all_rows.append(['CLASSES', 'INFO', '', '', 'CLASSES セクションは存在すればファイル内に含まれます'])

    return all_rows

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DXF構造をCSVまたはExcelに出力')
    parser.add_argument('input_dxf', help='入力DXFファイル')
    parser.add_argument('output_file', help='出力ファイル（.csv または .xlsx）')
    parser.add_argument('--excel', action='store_true', help='強制的にExcel形式で出力')
    args = parser.parse_args()

    # 拡張子チェック
    if not args.output_file.endswith('.xlsx'):
        print("⚠️  警告: 出力ファイルの拡張子は '.xlsx' です。")
        sys.exit(1)

    data = analyze_dxf_structure(args.input_dxf)
    df = pd.DataFrame(data, columns=['Section', 'Entity', 'GroupCode', 'GroupCode Definition', 'Value'])

    if args.output_file.endswith('.xlsx') or args.excel:
        df.to_excel(args.output_file, index=False)
        print(f"Excel形式出力完了 出力ファイル: {args.output_file}")
    else:
        df.to_csv(args.output_file, index=False, encoding='utf-8-sig')
        print(f"CSV形式出力完了 出力ファイル: {args.output_file}")
