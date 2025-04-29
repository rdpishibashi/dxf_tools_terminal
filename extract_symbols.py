#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import argparse
import os
import re

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

def extract_circuit_symbols(input_excel, output_txt):
    """
    Excelファイルから回路記号リストを抽出し、テキストファイルに出力する。
    
    Args:
        input_excel (str): 入力Excelファイルのパス（ファイル名は抽出する指番）
        output_txt (str): 出力テキストファイルのパス
    """
    try:
        # アセンブリ番号を入力ファイル名から抽出
        filename = os.path.basename(input_excel)
        assembly_number = os.path.splitext(filename)[0]  # 拡張子を除いた部分
        
        print(f"アセンブリ番号: {assembly_number}")
        
        # Excelファイルを読み込む（1行目をヘッダーとして）
        df = pd.read_excel(input_excel)
        
        # ファイルが存在し、必要な列があるか確認
        required_columns = ["符号", "構成コメント", "構成数", "図面番号"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"'{col}'列がExcelファイルに見つかりません")
        
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
            
            # 回路記号リストに追加
            circuit_symbols.extend(final_symbols)
        
        # テキストファイルに書き込み
        with open(output_txt, 'w', encoding='utf-8') as f:
            for symbol in circuit_symbols:
                if symbol:  # 空文字列でない場合に出力
                    f.write(f"{symbol}\n")
        
        print(f"回路記号リスト抽出完了。{len(circuit_symbols)}個の回路記号を抽出しました。")
        print(f"出力ファイル: {output_txt}")
        return True
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        return False

def main():
    # コマンドライン引数を解析
    parser = argparse.ArgumentParser(description='Excelファイルから回路記号リストを抽出します')
    parser.add_argument('input_excel', help='入力Excelファイルのパス')
    parser.add_argument('output_txt', help='出力テキストファイルのパス')
    
    args = parser.parse_args()
    
    # 入力ファイルの存在確認
    if not os.path.exists(args.input_excel):
        print(f"エラー: 入力ファイル '{args.input_excel}' が見つかりません")
        return 1
    
    # 入力ファイル拡張子の確認
    if not args.input_excel.lower().endswith('.xlsx'):
        print(f"エラー: 入力ファイル '{args.input_excel}' はExcelファイル(.xlsx)である必要があります")
        return 1
    
    # 出力先ディレクトリの存在確認
    output_dir = os.path.dirname(args.output_txt)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print(f"エラー: 出力ディレクトリ '{output_dir}' を作成できません: {str(e)}")
            return 1
    
    # 回路記号抽出処理を実行
    success = extract_circuit_symbols(args.input_excel, args.output_txt)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())