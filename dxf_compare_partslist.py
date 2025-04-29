#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from collections import Counter

def normalize_label(label):
    """ラベルを正規化する（空白を削除し、大文字に変換）"""
    if label is None:
        return ""
    return label.strip().upper()

def load_labels_from_file(file_path):
    """ファイルからラベルを読み込み、正規化する"""
    labels = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                label = line.strip()
                if label:  # 空行を無視
                    # ラベルを正規化（大文字変換・トリム）
                    label = normalize_label(label)
                    labels.append(label)
        return labels
    except Exception as e:
        # エラーメッセージは標準エラー出力へ
        print(f"エラー: ファイル '{file_path}' の読み込みに失敗しました: {str(e)}", file=sys.stderr)
        sys.exit(1) # エラー終了

def compare_label_files(dxf_labels_file, circuit_symbols_file, output_file, verbose=False):
    """2つのラベルファイルを比較し、結果をマークダウン形式で出力する"""
    try:
        # verbose 出力は標準エラー出力へ
        if verbose:
            print(f"図面ラベルファイル: {dxf_labels_file}", file=sys.stderr)
            print(f"回路記号ファイル: {circuit_symbols_file}", file=sys.stderr)
            print(f"出力ファイル: {output_file}", file=sys.stderr)
            print("処理を開始します...", file=sys.stderr)

        dxf_labels = load_labels_from_file(dxf_labels_file)
        circuit_symbols = load_labels_from_file(circuit_symbols_file)

        if verbose:
            print(f"図面ラベル数: {len(dxf_labels)}", file=sys.stderr)
            print(f"回路記号数: {len(circuit_symbols)}", file=sys.stderr)

        # カウンターで集計
        dxf_counter = Counter(dxf_labels)
        circuit_counter = Counter(circuit_symbols)

        # 図面に不足しているラベル（回路記号にはあるが図面にない）
        missing_in_dxf = circuit_counter - dxf_counter

        # 回路記号に不足しているラベル（図面にあるが回路記号にない）
        missing_in_circuit = dxf_counter - circuit_counter

        # 不足しているラベルの総数を計算
        missing_in_dxf_total_count = sum(missing_in_dxf.values())
        missing_in_circuit_total_count = sum(missing_in_circuit.values())

        # 共通するユニークラベル数
        common_unique_labels_count = len(set(dxf_counter.keys()) & set(circuit_counter.keys()))

        if verbose:
            print(f"共通ユニークラベル数: {common_unique_labels_count}", file=sys.stderr)
            print(f"図面不足総数: {missing_in_dxf_total_count}", file=sys.stderr)
            print(f"回路記号不足総数: {missing_in_circuit_total_count}", file=sys.stderr)

        # マークダウン形式で出力を生成
        output = []
        output.append("# 図面ラベルと回路記号の差分比較結果\n")

        output.append("## 処理概要")
        output.append(f"- 図面ラベル数: {len(dxf_labels)} (ユニーク: {len(dxf_counter)})")
        output.append(f"- 回路記号数: {len(circuit_symbols)} (ユニーク: {len(circuit_counter)})")
        output.append(f"- 共通ユニークラベル数: {common_unique_labels_count}")
        output.append(f"- 図面に不足しているラベル総数: {missing_in_dxf_total_count}") # 総数を表示
        output.append(f"- 回路記号に不足しているラベル総数: {missing_in_circuit_total_count}") # 総数を表示
        output.append("")

        output.append("## 図面に不足しているラベル（回路記号リストには存在する）")
        if missing_in_dxf:
            # ★修正点: elements() でラベルを個数分展開し、ソートして出力
            missing_labels_expanded = sorted(list(missing_in_dxf.elements()))
            for symbol in missing_labels_expanded:
                output.append(f"- {symbol}") # 個数表示を削除し、個数分出力
        else:
            output.append("- なし")
        output.append("") # セクション間の見やすさのために空行を追加

        output.append("## 回路記号リストに不足しているラベル（図面には存在する）")
        if missing_in_circuit:
            # ★修正点: elements() でラベルを個数分展開し、ソートして出力
            missing_labels_expanded = sorted(list(missing_in_circuit.elements()))
            for label in missing_labels_expanded:
                output.append(f"- {label}") # 個数表示を削除し、個数分出力
        else:
            output.append("- なし")
        output.append("") # 末尾にも空行を追加

        # 結果をファイルに書き込み
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(output))
            if verbose:
                 print(f"比較結果を '{output_file}' に出力しました", file=sys.stderr)
        except Exception as e:
            print(f"エラー: 出力ファイル '{output_file}' への書き込みに失敗しました: {str(e)}", file=sys.stderr)
            return False # 書き込み失敗時はFalseを返す

        return True # 正常終了
    except Exception as e:
        print(f"エラー: 比較処理中に予期せぬエラーが発生しました: {str(e)}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        return False # 異常終了

def ensure_file_extension(filename, default_ext):
    """ファイル名に拡張子がない場合、デフォルトの拡張子を追加する"""
    base, ext = os.path.splitext(filename)
    if not ext:
        return f"{filename}{default_ext}"
    return filename

def get_default_output_filename(dxf_labels_file, circuit_symbols_file):
    """
    デフォルトの出力ファイル名を生成する
    入力ファイル名をベースにして、比較結果を示す名前を生成
    """
    base_dxf = os.path.basename(dxf_labels_file)
    base_circuit = os.path.basename(circuit_symbols_file)
    name_dxf, _ = os.path.splitext(base_dxf)
    name_circuit, _ = os.path.splitext(base_circuit)
    return f"{name_dxf}_vs_{name_circuit}.md"

def main():
    parser = argparse.ArgumentParser(
        description='2つの部品リストファイル（テキスト形式）を比較し、差分をマークダウン形式で出力します。',
        formatter_class=argparse.RawTextHelpFormatter
    )
    # 引数のヘルプメッセージを少し具体的に修正
    parser.add_argument('dxf_labels_file', help='図面上の部品ラベルが1行1ラベルで記述されたファイル (.txt)')
    parser.add_argument('circuit_symbols_file', help='回路図シンボル（部品表など）が1行1ラベルで記述されたファイル (.txt)')
    parser.add_argument('output_file', nargs='?', help='比較結果の出力ファイル (.md)。指定しない場合は自動生成')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細な処理情報を標準エラー出力に表示する')

    args = parser.parse_args()

    # 入力ファイルに拡張子を追加
    dxf_labels_file = ensure_file_extension(args.dxf_labels_file, '.txt')
    circuit_symbols_file = ensure_file_extension(args.circuit_symbols_file, '.txt')

    # 入力ファイルの存在確認
    if not os.path.exists(dxf_labels_file):
        print(f"エラー: 図面ラベルファイル '{dxf_labels_file}' が見つかりません", file=sys.stderr)
        return 1
    if not os.path.exists(circuit_symbols_file):
        print(f"エラー: 回路記号ファイル '{circuit_symbols_file}' が見つかりません", file=sys.stderr)
        return 1

    # 出力ファイル名の処理
    if args.output_file is None:
        # 出力ファイル名が指定されていない場合、デフォルト名を生成
        output_file = get_default_output_filename(dxf_labels_file, circuit_symbols_file)
        print(f"出力ファイル名が指定されていないため、デフォルト名を使用します: {output_file}", file=sys.stderr)
    else:
        # 出力ファイル名が指定されている場合、拡張子を確認・追加
        output_file = ensure_file_extension(args.output_file, '.md')

    # 出力ファイル拡張子の確認とディレクトリ作成 (エラー出力先をstderrに修正)
    if not output_file.lower().endswith('.md'):
        # 警告のみとし、ファイル名は変更しない方針も検討可
        print(f"警告: 出力ファイル '{output_file}' の拡張子は .md を推奨します。", file=sys.stderr)
        # args.output_file += '.md' # 自動変更する場合はコメント解除
        # print(f"出力ファイル名を '{args.output_file}' に変更しました", file=sys.stderr)

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"情報: 出力ディレクトリ '{output_dir}' を作成しました。", file=sys.stderr)
        except Exception as e:
            print(f"エラー: 出力ディレクトリ '{output_dir}' を作成できません: {str(e)}", file=sys.stderr)
            return 1

    # 比較を実行
    success = compare_label_files(
        dxf_labels_file,
        circuit_symbols_file,
        output_file,
        verbose=args.verbose
    )

    # 終了メッセージを標準エラー出力へ
    if success:
        print(f"\n比較処理が正常に完了しました。", file=sys.stderr)
        print(f"結果は '{os.path.abspath(output_file)}' を確認してください。", file=sys.stderr) # 絶対パス表示
        return 0 # 正常終了コード
    else:
        print(f"\n比較処理中にエラーが発生しました。", file=sys.stderr)
        return 1 # 異常終了コード

if __name__ == "__main__":
    sys.exit(main())