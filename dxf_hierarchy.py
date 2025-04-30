#!/usr/bin/env python
import sys
import ezdxf
import argparse
from io import StringIO
import os

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

def ensure_file_extension(filename, default_ext):
    """ファイル名に拡張子がない場合、デフォルトの拡張子を追加する"""
    base, ext = os.path.splitext(filename)
    if not ext:
        return f"{filename}{default_ext}"
    return filename

def get_default_output_filename(input_dxf):
    """
    デフォルトの出力ファイル名を生成する
    入力ファイルの名前をベースにして、階層構造を示す接尾辞を追加
    """
    base = os.path.basename(input_dxf)
    name, _ = os.path.splitext(base)
    return f"{name}_hierarchy.md"

def main():
    parser = argparse.ArgumentParser(description='DXF階層構造をMarkdownで出力')
    parser.add_argument('input_dxf', help='入力DXFファイル')
    parser.add_argument('output_file', nargs='?', help='出力ファイル（.md）。指定しない場合は自動生成')
    args = parser.parse_args()

    # 入力ファイル名に拡張子を追加
    input_dxf = ensure_file_extension(args.input_dxf, '.dxf')

    # 入力ファイルの存在確認
    if not os.path.exists(input_dxf):
        print(f"エラー: 入力ファイル '{input_dxf}' が見つかりません")
        sys.exit(1)

    # 出力ファイル名の処理
    if args.output_file is None:
        # 出力ファイル名が指定されていない場合、デフォルト名を生成
        output_file = get_default_output_filename(input_dxf)
        print(f"出力ファイル名が指定されていないため、デフォルト名を使用します: {output_file}")
    else:
        # 出力ファイル名が指定されている場合、拡張子を確認・追加
        output_file = ensure_file_extension(args.output_file, '.md')

    # 出力ファイル拡張子の確認
    if not output_file.endswith('.md') and not output_file.endswith('.txt'):
        print("⚠️  警告: 出力ファイルの拡張子は '.txt' か '.md' を推奨します。")
        if not "." in output_file:
            output_file += '.md'
            print(f"出力ファイル名を '{output_file}' に変更しました")

    # 出力先ディレクトリの存在確認と作成
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"出力ディレクトリ '{output_dir}' を作成しました")
        except Exception as e:
            print(f"エラー: 出力ディレクトリ '{output_dir}' を作成できません: {str(e)}")
            sys.exit(1)

    try:
        doc = ezdxf.readfile(input_dxf)
        hierarchy = extract_hierarchy(doc)

        with open(output_file, 'w', encoding='utf-8') as f:
            for line in hierarchy:
                f.write(line + "\n")

        print(f"Markdown出力完了: {output_file}")
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()