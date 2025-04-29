#!/usr/bin/env python
import sys
import ezdxf
import argparse
import pandas as pd
import os
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

def save_by_section(df, base_filename):
    """Save data split by section to multiple Excel files"""
    sections = df['Section'].unique()
    base_name, ext = os.path.splitext(base_filename)
    
    # 拡張子がない場合はxlsxをデフォルトとして追加
    if not ext:
        ext = '.xlsx'
    
    for section in sections:
        # セクション名から括弧などを取り除いてファイル名に適した形式に変換
        section_safe = section.replace('(', '_').replace(')', '').replace(' ', '_')
        section_filename = f"{base_name}_{section_safe}{ext}"
        
        try:
            section_df = df[df['Section'] == section]
            # Excel行数制限チェック
            if ext.lower() == '.xlsx' and len(section_df) > 1000000:
                csv_filename = f"{base_name}_{section_safe}.csv"
                section_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                print(f"セクション '{section}' が大きすぎるため CSV として保存: {csv_filename} ({len(section_df)} 行)")
            else:
                section_df.to_excel(section_filename, index=False)
                print(f"保存完了: {section_filename} ({len(section_df)} 行)")
        except Exception as e:
            # エラーが発生した場合はCSVにフォールバック
            csv_filename = f"{base_name}_{section_safe}.csv"
            section_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"エラー発生: {e}")
            print(f"代わりにCSVとして保存: {csv_filename}")

def ensure_extension(filename, default_ext='.xlsx'):
    """ファイル名に拡張子がない場合、デフォルトの拡張子を追加する"""
    base, ext = os.path.splitext(filename)
    if not ext:
        return f"{filename}{default_ext}"
    return filename

def ensure_dxf_extension(filename):
    """入力DXFファイル名に.dxf拡張子を追加（存在しない場合）"""
    base, ext = os.path.splitext(filename)
    if not ext:
        return f"{filename}.dxf"
    elif ext.lower() != '.dxf':
        print(f"⚠️  警告: 入力ファイルの拡張子が '.dxf' ではありません: {ext}")
    return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DXF構造をExcelまたはCSVに出力')
    parser.add_argument('input_dxf', help='入力DXFファイル（拡張子がない場合は .dxf が自動追加）')
    parser.add_argument('output_file', help='出力ファイル（拡張子がない場合は .xlsx が自動追加）')
    parser.add_argument('--csv', action='store_true', help='強制的にCSV形式で出力')
    parser.add_argument('--split', action='store_true', help='セクションごとに別ファイルに分割')
    args = parser.parse_args()

    # 入力ファイルに .dxf 拡張子を追加（必要な場合）
    input_dxf = ensure_dxf_extension(args.input_dxf)
    
    # 出力ファイルに拡張子を追加（必要な場合）
    output_file = args.output_file
    if args.csv:
        output_file = ensure_extension(output_file, '.csv')
    else:
        output_file = ensure_extension(output_file, '.xlsx')
    
    # 入力ファイルが存在するか確認
    if not os.path.exists(input_dxf):
        print(f"❌ エラー: 入力ファイルが見つかりません: {input_dxf}")
        sys.exit(1)
    
    try:
        # DXF構造データを抽出
        print(f"DXFファイル分析中: {input_dxf}")
        data = analyze_dxf_structure(input_dxf)
        df = pd.DataFrame(data, columns=['Section', 'Entity', 'GroupCode', 'GroupCode Definition', 'Value'])
        
        row_count = len(df)
        print(f"抽出されたデータ: {row_count} 行")
        
        # Excelの行数制限をチェック
        EXCEL_ROW_LIMIT = 1000000  # 実際の制限より少し小さい値を設定
        
        if args.split:
            # セクションごとに分割して保存
            save_by_section(df, output_file)
        elif args.csv or row_count > EXCEL_ROW_LIMIT or output_file.endswith('.csv'):
            # CSV形式で保存
            csv_file = output_file if output_file.endswith('.csv') else os.path.splitext(output_file)[0] + '.csv'
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"CSV形式出力完了 出力ファイル: {csv_file}")
            if output_file.endswith('.xlsx') and row_count > EXCEL_ROW_LIMIT:
                print(f"⚠️  注意: データが大きすぎるため ({row_count} 行 > {EXCEL_ROW_LIMIT} 行制限)、Excel形式ではなくCSV形式で保存しました。")
        else:
            # Excel形式で保存
            try:
                df.to_excel(output_file, index=False)
                print(f"Excel形式出力完了 出力ファイル: {output_file}")
            except Exception as e:
                # エラーが発生した場合はCSVにフォールバック
                csv_file = os.path.splitext(output_file)[0] + '.csv'
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"Excel形式で保存中にエラーが発生しました: {e}")
                print(f"代わりにCSV形式で保存しました: {csv_file}")
    
    except Exception as e:
        print(f"❌ エラー: 処理中に例外が発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)