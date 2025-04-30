#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import argparse
import os
import re
import sys

def extract_alphabetic_part(symbol):
    """
    回路記号からアルファベット部分を抽出する
    
    Args:
        symbol (str): 回路記号
        
    Returns:
        str: アルファベット部分
    """
    # アルファベット部分（先頭の連続したアルファベット）を抽出
    match = re.match(r'^([A-Za-z]+)', symbol)
    if match:
        return match.group(1)
    return ""

def extract_assembly_number_from_filename(filename):
    """
    ファイル名からアセンブリ番号を抽出する
    '_'以降がアセンブリ番号として扱われる
    
    Args:
        filename (str): ファイル名
        
    Returns:
        str: アセンブリ番号
    """
    # 拡張子を除いたファイル名を取得
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # '_'で分割し、'_'以降の部分をアセンブリ番号として返す
    parts = base_name.split('_', 1)
    if len(parts) > 1:
        return parts[1]
    
    # '_'がない場合はファイル名全体をアセンブリ番号として返す
    return base_name

def find_all_possible_assembly_numbers(df):
    """
    Excelファイル内の全ての可能なアセンブリ番号（図面番号）を抽出する
    図面番号の下に空白行がある図面番号のみを対象とする
    
    Args:
        df (pandas.DataFrame): Excelファイルから読み込んだデータフレーム
        
    Returns:
        list: 可能なアセンブリ番号のリスト
    """
    possible_assemblies = []
    
    for i in range(len(df) - 1):  # 最後の行は次の行がないので対象外
        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]
        
        # 現在の行に図面番号があり、次の行の図面番号が空白の場合
        if (pd.notna(current_row["図面番号"]) and 
            (pd.isna(next_row["図面番号"]) or str(next_row["図面番号"]).strip() == "")):
            possible_assemblies.append(str(current_row["図面番号"]))
    
    return possible_assemblies

def extract_circuit_symbols(input_excel, output_txt, use_all_assemblies=False, include_maker_info=False):
    """
    Excelファイルから回路記号リストを抽出し、テキストファイルに出力する。
    
    Args:
        input_excel (str): 入力Excelファイルのパス
        output_txt (str): 出力テキストファイルのパス
        use_all_assemblies (bool): 全ての可能なアセンブリ番号を使用するかどうか
        include_maker_info (bool): メーカー名とメーカー型式を出力に含めるかどうか
        
    Returns:
        bool: 成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # アセンブリ番号をファイル名から抽出
        filename = os.path.basename(input_excel)
        suggested_assembly_number = extract_assembly_number_from_filename(filename)
        
        print(f"ファイル名から抽出されたアセンブリ番号: {suggested_assembly_number}")
        
        # Excelファイルを読み込む（1行目をヘッダーとして）
        df = pd.read_excel(input_excel)
        
        # ファイルが存在し、必要な列があるか確認
        required_columns = ["符号", "構成コメント", "構成数", "図面番号"]
        
        # メーカー情報を含める場合は追加の列が必要
        if include_maker_info:
            required_columns.extend(["メーカ名", "メーカ型式"])
        
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"'{col}'列がExcelファイルに見つかりません")
        
        # 使用するアセンブリ番号のリストを初期化
        assembly_numbers = []
        
        # 全てのアセンブリを使用するオプションが有効な場合
        if use_all_assemblies:
            possible_assemblies = find_all_possible_assembly_numbers(df)
            if possible_assemblies:
                assembly_numbers = possible_assemblies
                print(f"検出された可能なアセンブリ番号: {', '.join(assembly_numbers)}")
            else:
                print("警告: 可能なアセンブリ番号が見つかりませんでした。")
                # アセンブリ番号が見つからなかった場合でも、ファイル名から抽出したものを使用
                assembly_numbers = [suggested_assembly_number]
        else:
            # 抽出されたアセンブリ番号が図面番号に存在するか確認
            assembly_found = False
            for i, row in df.iterrows():
                if pd.notna(row["図面番号"]) and str(row["図面番号"]) == suggested_assembly_number:
                    assembly_numbers = [suggested_assembly_number]
                    assembly_found = True
                    break
            
            # アセンブリ番号が見つからなかった場合は、ファイル名全体を使用
            if not assembly_found:
                assembly_number = os.path.splitext(filename)[0]
                print(f"抽出されたアセンブリ番号が図面番号に見つからないため、ファイル名をアセンブリ番号として使用します: {assembly_number}")
                assembly_numbers = [assembly_number]
            else:
                print(f"アセンブリ番号として採用: {suggested_assembly_number}")
        
        # すべての回路記号を格納するリスト
        all_circuit_symbols = []
        
        # 各アセンブリ番号について処理を実行
        for assembly_number in assembly_numbers:
            print(f"===== アセンブリ番号 '{assembly_number}' の処理を開始 =====")
            
            # 処理対象の行を特定
            start_processing = False
            processing_rows = []
            
            for i, row in df.iterrows():
                # アセンブリ番号と一致する図面番号を探す
                if not start_processing and pd.notna(row["図面番号"]) and str(row["図面番号"]) == assembly_number:
                    start_processing = True
                    continue  # 一致した行は処理対象外
                
                # 処理開始後、図面番号が空白の行を処理対象とする
                if start_processing:
                    if pd.isna(row["図面番号"]) or str(row["図面番号"]).strip() == "":
                        processing_rows.append(i)
                    else:
                        # 図面番号が空白でなくなったら処理終了
                        break
            
            print(f"処理対象行数: {len(processing_rows)}")
            
            if not processing_rows:
                print(f"警告: 処理対象となる行が見つかりません。アセンブリ番号 '{assembly_number}' が図面番号列に存在するか確認してください。")
                continue  # 次のアセンブリ番号へ
            
            # 回路記号リストを格納するリスト
            circuit_symbols = []
            
            # 処理対象の行だけを処理
            for idx in processing_rows:
                row = df.iloc[idx]
                
                # 符号または構成コメントからシンボルを取得
                if pd.notna(row["構成コメント"]) and "_" in str(row["構成コメント"]):
                    # 構成コメントに"_"が含まれる場合はそちらを使用
                    base_symbols = str(row["構成コメント"]).split("_")
                else:
                    # そうでなければ符号を使用
                    symbol_str = str(row["符号"]) if pd.notna(row["符号"]) else ""
                    base_symbols = symbol_str.split("_") if "_" in symbol_str else [symbol_str]
                
                # 数値型の場合は整数に変換する
                qty = int(row["構成数"]) if pd.notna(row["構成数"]) else 0
                
                # 空文字列を除外
                base_symbols = [s for s in base_symbols if s.strip()]
                
                # 回路記号の個数を取得
                symbol_count = len(base_symbols)
                
                # 最終的なシンボルリスト
                final_symbols = base_symbols.copy()
                
                # 回路記号の個数と構成数を比較
                if symbol_count < qty:
                    # 最後の回路記号のアルファベット部分を取得
                    last_alpha = ""
                    if base_symbols:
                        last_alpha = extract_alphabetic_part(base_symbols[-1])
                    
                    # 不足分は"rrrrr-Xddd"で補完
                    # rrrrrはアルファベット部分、dddは行ごとに001からのシーケンス番号
                    for i in range(qty - symbol_count):
                        final_symbols.append(f"{last_alpha}-X{i+1:03d}")
                elif symbol_count > qty:
                    # 超過分は最後から?をつける
                    final_symbols = final_symbols[:qty]
                    for i in range(symbol_count - qty):
                        if i < len(final_symbols):
                            final_symbols[qty-i-1] = final_symbols[qty-i-1] + "?"
                
                # メーカー情報を含める場合
                if include_maker_info:
                    maker_name = str(row["メーカ名"]) if pd.notna(row["メーカ名"]) else ""
                    maker_model = str(row["メーカ型式"]) if pd.notna(row["メーカ型式"]) else ""
                    
                    # 各シンボルにメーカー情報を追加
                    symbols_with_info = []
                    for symbol in final_symbols:
                        if symbol:  # 空文字列でない場合
                            symbols_with_info.append(f"{symbol},{maker_name},{maker_model}")
                    
                    # 回路記号リストに追加
                    circuit_symbols.extend(symbols_with_info)
                else:
                    # メーカー情報を含めない場合は、シンボルのみを追加
                    circuit_symbols.extend([s for s in final_symbols if s])  # 空文字列を除外
            
            # 全てのシンボルリストに追加
            all_circuit_symbols.extend(circuit_symbols)
            
            print(f"アセンブリ '{assembly_number}' から {len(circuit_symbols)} 個の回路記号を抽出しました。")
        
        # テキストファイルに書き込み
        with open(output_txt, 'w', encoding='utf-8') as f:
            for symbol in all_circuit_symbols:
                f.write(f"{symbol}\n")
        
        print(f"回路記号リスト抽出完了。合計 {len(all_circuit_symbols)} 個の回路記号を抽出しました。")
        print(f"出力ファイル: {output_txt}")
        return True
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def ensure_file_extension(filename, default_ext):
    """ファイル名に拡張子がない場合、デフォルトの拡張子を追加する"""
    base, ext = os.path.splitext(filename)
    if not ext:
        return f"{filename}{default_ext}"
    return filename

def get_default_output_filename(input_excel):
    """
    デフォルトの出力ファイル名を生成する
    入力ファイルのパスをベースに、.txtの拡張子を付ける
    """
    base, ext = os.path.splitext(input_excel)
    return f"{base}.txt"

def main():
    # コマンドライン引数を解析
    parser = argparse.ArgumentParser(description='Excelファイルから回路記号リストを抽出します')
    parser.add_argument('input_excel', help='入力Excelファイルのパス')
    parser.add_argument('output_txt', nargs='?', help='出力テキストファイルのパス。指定しない場合は自動生成')
    parser.add_argument('--all-assemblies', '-a', action='store_true', 
                        help='図面番号にある全ての可能なアセンブリ番号を使用する')
    parser.add_argument('--include-maker', '-m', action='store_true',
                        help='メーカー名とメーカー型式を出力に含める')
    
    args = parser.parse_args()
    
    # 入力ファイル名に拡張子を追加
    input_excel = ensure_file_extension(args.input_excel, '.xlsx')
    
    # 入力ファイルの存在確認
    if not os.path.exists(input_excel):
        print(f"エラー: 入力ファイル '{input_excel}' が見つかりません")
        return 1
    
    # 入力ファイル拡張子の確認
    if not input_excel.lower().endswith('.xlsx'):
        print(f"エラー: 入力ファイル '{input_excel}' はExcelファイル(.xlsx)である必要があります")
        return 1
    
    # 出力ファイル名の処理
    if args.output_txt is None:
        # 出力ファイル名が指定されていない場合、入力ファイル名.txtを使用
        output_txt = get_default_output_filename(input_excel)
        print(f"出力ファイル名が指定されていないため、デフォルト名を使用します: {output_txt}")
    else:
        # 出力ファイル名が指定されている場合、拡張子を確認・追加
        output_txt = ensure_file_extension(args.output_txt, '.txt')
    
    # 出力拡張子の確認
    if not output_txt.endswith('.txt'):
        print(f"警告: 出力ファイルの拡張子は '.txt' を推奨します。")
        output_txt += '.txt'
        print(f"出力ファイル名を '{output_txt}' に変更しました。")
    
    # 出力先ディレクトリの存在確認
    output_dir = os.path.dirname(output_txt)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"出力ディレクトリ '{output_dir}' を作成しました。")
        except Exception as e:
            print(f"エラー: 出力ディレクトリ '{output_dir}' を作成できません: {str(e)}")
            return 1
    
    # 回路記号抽出処理を実行
    success = extract_circuit_symbols(
        input_excel, 
        output_txt,
        use_all_assemblies=args.all_assemblies,
        include_maker_info=args.include_maker
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())