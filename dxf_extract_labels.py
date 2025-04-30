#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import ezdxf
import argparse
import re

# --- ヘルパー関数 (変更なし) ---
def normalize_label(label):
    """ラベルを正規化（大文字化、トリム、全角スペース置換）"""
    if label is None:
        return ""
    return label.replace('　', ' ').strip().upper()

def remove_all_brackets(label):
    """ラベル内の括弧とその内容を削除"""
    if label is None:
        return "", False
    original_label = label
    modified_label = label
    pattern = re.compile(r'\([^)]*\)')
    prev_label = None
    while pattern.search(modified_label):
        if prev_label == modified_label:
            print(f"警告: 括弧削除で予期せぬパターン。処理を中断します: '{original_label}'", file=sys.stderr)
            break
        prev_label = modified_label
        modified_label = pattern.sub('', modified_label)
    modified_label = modified_label.strip()
    bracket_found = modified_label != original_label
    return modified_label, bracket_found

# --- is_filtered_label (デバッグ出力削除) ---
def is_filtered_label(label):
    """ラベルがフィルター条件に合致するか判断 (デバッグ出力なし)"""
    original_label = label
    normalized = normalize_label(label)
    modified_label = normalized
    current_label = normalized
    final_reason = None
    bracket_found = False
    trailing_removed = False

    # --- フィルター条件 (括弧削除前にチェック) ---
    if not normalized: return True, "空文字列", None
    if normalized.startswith('('): return True, "( で始まる", None
    if normalized[0].isdigit(): return True, "数字で始まる", None
    if 'GND' in normalized: return True, "GND を含む", None
    if normalized.startswith('AWG'): return True, "AWG で始まる", None
    stripped_original = original_label.strip() if original_label else ""
    if stripped_original and stripped_original[0].islower(): return True, "英小文字で始まる", None
    if normalized.startswith('☆'): return True, "☆ で始まる", None
    if normalized.startswith('注'): return True, "注 で始まる", None

    # --- 括弧削除処理 ---
    modified_label, bracket_found = remove_all_brackets(normalized)
    current_label = modified_label
    if bracket_found and modified_label != normalized:
        final_reason = "括弧削除"

    if not current_label:
        reason = "空文字列" if not normalized else "括弧削除後に空文字列"
        return True, reason, None

    # --- 括弧削除後のフィルター条件 ---
    reason_prefix = "括弧削除後、" if bracket_found and modified_label != normalized else ""
    single_letter_number_pattern = r'^[A-Z][0-9]+$'
    single_letter_dot_pattern_strict = r'^[A-Z][0-9]+\.[0-9]+$'
    alpha_plusminus_pattern = r'^[A-Z]+[\+\-]$'

    if current_label.isalpha() and current_label.isupper() and len(current_label) <= 2:
        return True, reason_prefix + "英大文字だけで2文字以下", None
    if re.match(single_letter_number_pattern, current_label):
        return True, reason_prefix + "英大文字1文字+数字", None
    if re.match(single_letter_dot_pattern_strict, current_label):
        return True, reason_prefix + "英大文字1文字+数字+ドット+数字", None
    if re.match(alpha_plusminus_pattern, current_label):
        return True, reason_prefix + "英字+[+/-]", None
    if ' ' in current_label and len(current_label.split()) > 1:
        return True, reason_prefix + "英文字列と空白を複数含む", None

    # --- 後続文字削除処理 ---
    match = re.match(r'^[A-Z0-9]+', current_label)
    if match:
        extracted_part = match.group(0)
        if extracted_part != current_label:
            trailing_removed = True
            current_label = extracted_part
            # 再度フィルターチェック
            reason_prefix_trail = reason_prefix + "後続文字削除後、" if reason_prefix else "後続文字削除後、"
            if not current_label: return True, reason_prefix_trail + "空文字列", None
            if current_label.isalpha() and current_label.isupper() and len(current_label) <= 2:
                 return True, reason_prefix_trail + "英大文字だけで2文字以下", None
            if re.match(single_letter_number_pattern, current_label):
                 return True, reason_prefix_trail + "英大文字1文字+数字", None

    # --- 最終判断 ---
    if trailing_removed:
        final_reason = "括弧削除+後続文字削除" if final_reason == "括弧削除" else "後続文字削除"
    elif bracket_found and final_reason is None:
         final_reason = "括弧あり(変化なし)" # または None

    # 最終的なラベルを返す (除外されなかった場合)
    return False, final_reason, current_label

# --- extract_labels_from_dxf (セミコロン区切りで4つ目の要素を抽出するように変更) ---
def extract_labels_from_dxf(input_dxf, filter_labels=True, sort_order='asc'):
    """DXFからMTEXTエンティティの4番目のセグメント（3つ目のセミコロンの後）を抽出・フィルタリング"""
    info = {
        "total_extracted": 0, "filtered_count": 0, "skipped_count": 0,
        "final_count": 0, "skipped_labels": [], "filtered_labels_info": []
    }

    try:
        doc = ezdxf.readfile(input_dxf)
        msp = doc.modelspace()
        raw_labels = []

        for entity in msp:
            try:
                if entity.dxftype() == 'MTEXT':
                    text = entity.text
                    # セミコロンで分割し、4つ目の要素（インデックス3）を取得
                    segments = text.split(';')
                    if len(segments) >= 4:  # 少なくとも4つのセグメントがあることを確認
                        label = segments[3].strip()
                        if label:
                            raw_labels.append(label)
                    else:
                        info["skipped_count"] += 1
                        info["skipped_labels"].append((entity.dxftype(), "セミコロン区切りの4番目の要素が存在しない"))
            except AttributeError:
                 info["skipped_count"] += 1
                 info["skipped_labels"].append((entity.dxftype(), "AttributeError"))
            except Exception as e:
                info["skipped_count"] += 1
                info["skipped_labels"].append((entity.dxftype(), str(e)))
                print(f"警告: エンティティ処理スキップ: {entity.dxftype()} - {str(e)}", file=sys.stderr)

        info["total_extracted"] = len(raw_labels)
        processed_labels = [] # 最終的に出力するラベルリスト

        if filter_labels:
            for label in raw_labels:
                try:
                    exclude, reason, result_label = is_filtered_label(label)
                    if not exclude:
                        if result_label:
                            processed_labels.append(result_label)
                    elif reason:
                         info["filtered_labels_info"].append((label, reason))
                except Exception as e:
                    info["skipped_count"] += 1
                    info["skipped_labels"].append((label, f"Filtering error: {str(e)}"))
                    print(f"警告: ラベルフィルタリング中にエラー: '{label}' - {str(e)}", file=sys.stderr)
            info["filtered_count"] = len(raw_labels) - len(processed_labels)
        else:
            # フィルターしない場合でも正規化は行う
            print("情報: --no-filter が指定されたためフィルターは行いませんが、抽出ラベルの正規化（大文字化・トリム）は行います。", file=sys.stderr)
            for label in raw_labels:
                normalized_lbl = normalize_label(label)
                if normalized_lbl:
                    processed_labels.append(normalized_lbl)
            info["filtered_count"] = 0 # フィルターによる除外はない

        # ソート処理
        labels = processed_labels # 最終リストを labels に代入
        if sort_order == 'asc':
            labels.sort()
        elif sort_order == 'desc':
            labels.sort(reverse=True)

        info["final_count"] = len(labels)
        return labels, info

    except ezdxf.DXFStructureError as e:
        print(f"エラー: DXFファイルの読み込みに失敗: {str(e)}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"エラー: 予期せぬエラー: {str(e)}", file=sys.stderr)
        raise

# --- 拡張子を確保する補助関数 ---
def ensure_file_extension(filename, default_ext):
    """ファイル名に拡張子がない場合、デフォルトの拡張子を追加する"""
    base, ext = os.path.splitext(filename)
    if not ext:
        return f"{filename}{default_ext}"
    return filename

# --- main (拡張子処理改善) ---
def main():
    parser = argparse.ArgumentParser(
        description='DXFファイルからMTEXT要素のラベルを抽出・フィルタリングし、テキストファイルに出力します。',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input_dxf', help='入力DXFファイル (拡張子がない場合は .dxf が自動追加)')
    parser.add_argument('output_file', help='出力テキストファイル (拡張子がない場合は .txt が自動追加)')
    # フィルター関連オプション
    parser.add_argument('--filter', action='store_true', default=True, # デフォルトON
                        help='フィルターを適用します（デフォルト）。除外条件はコード参照。')
    parser.add_argument('--no-filter', action='store_false', dest='filter',
                        help='フィルター処理を無効にします（正規化は行われます）。')
    # ソート関連オプション
    parser.add_argument('--sort', dest='sort_order', nargs='?',
                        choices=['asc', 'desc', 'none'],
                        const='asc', default='asc', # デフォルト昇順
                        help='ラベルのソート順を指定 (デフォルト: asc)。')
    # verbose オプション
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='フィルタリングで除外されたラベルとその理由を標準エラー出力に表示します。')

    args = parser.parse_args()

    # 拡張子を追加
    input_dxf = ensure_file_extension(args.input_dxf, '.dxf')
    output_file = ensure_file_extension(args.output_file, '.txt')

    # ファイルチェック
    if not os.path.exists(input_dxf):
        print(f"エラー: 入力ファイル '{input_dxf}' が見つかりません", file=sys.stderr)
        return 1

    # ディレクトリ作成
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"情報: 出力ディレクトリ '{output_dir}' を作成しました。", file=sys.stderr)
        except Exception as e:
            print(f"エラー: 出力ディレクトリ '{output_dir}' を作成できません: {str(e)}", file=sys.stderr)
            return 1

    try:
        # ラベル抽出処理の呼び出し
        labels, info = extract_labels_from_dxf(
            input_dxf,
            filter_labels=args.filter,
            sort_order=args.sort_order
        )

        # 処理結果のサマリー表示 (標準エラー出力へ)
        print(f"--- 処理結果 ---", file=sys.stderr)
        print(f"入力DXF: {input_dxf}", file=sys.stderr)
        print(f"抽出総数: {info['total_extracted']}", file=sys.stderr)
        if info["skipped_count"] > 0:
            print(f"スキップ数: {info['skipped_count']}", file=sys.stderr)
            # スキップ詳細は verbose 時のみ表示
            if args.verbose and info["skipped_labels"]:
                 print("スキップ詳細:", file=sys.stderr)
                 for item, reason in sorted(info["skipped_labels"]): # ソートして表示
                      print(f"  - スキップ: '{item}' ({reason})", file=sys.stderr)

        print(f"フィルター適用: {'はい' if args.filter else 'いいえ'}", file=sys.stderr)
        if args.filter:
            print(f"フィルター除外数: {info['filtered_count']}", file=sys.stderr)
        print(f"最終出力数: {info['final_count']}", file=sys.stderr)
        sort_map = {'asc': '昇順', 'desc': '降順', 'none': 'なし'}
        print(f"ソート: {sort_map.get(args.sort_order, '不明')}", file=sys.stderr)
        print(f"出力ファイル: {output_file}", file=sys.stderr)

        # ラベルをファイルに書き込み
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for label in labels:
                    f.write(label + "\n")
        except Exception as e:
             print(f"エラー: 出力ファイル '{output_file}' への書き込み失敗: {str(e)}", file=sys.stderr)
             return 1

        # verbose オプション処理
        if args.verbose and args.filter and info["filtered_labels_info"]:
            print("\n--- 除外されたラベル詳細 (-v) ---", file=sys.stderr)
            sorted_filtered = sorted(info["filtered_labels_info"], key=lambda x: x[0]) # ラベル名でソート
            for label, reason in sorted_filtered:
                print(f"  - 除外: '{label}' (理由: {reason})", file=sys.stderr)

        return 0 # 正常終了

    except Exception as e:
        print(f"\n処理中に予期せぬエラーが発生しました。", file=sys.stderr)
        # エラー発生時はトレースバックを表示すると原因究明に役立つ
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1 # 異常終了

if __name__ == "__main__":
    sys.exit(main())