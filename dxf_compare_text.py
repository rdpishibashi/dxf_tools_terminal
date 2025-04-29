#!/usr/bin/env python
import sys
import ezdxf
import argparse
import re

def is_non_part_number(label):
    """
    ラベルが部品番号ではないと判断される条件をチェック
    
    Args:
        label (str): チェック対象のラベル
        
    Returns:
        bool: 部品番号ではないと思われる場合はTrue
    """
    if not label or len(label) == 0:
        return True
        
    # 最初の文字が「(」のラベル
    if label.startswith('('):
        return True
        
    # 最初の文字が数字のラベル
    if label[0].isdigit():
        return True
        
    # 最初の文字が英小文字のラベル
    if label[0].islower():
        return True
        
    # 「GND」を含むラベル
    if 'GND' in label:
        return True
        
    # 英字1文字のみのラベル（例：R, C）
    if len(label) == 1 and label.isalpha():
        return True
        
    # 英字1文字に続いて数字と「.」からなる文字列の組み合わせ（例：C1.1, R5.2）
    pattern1 = r'^[A-Za-z][0-9]+\.[0-9]+

def main():
    parser = argparse.ArgumentParser(description='ラベルを抽出してテキストファイルに出力（ENTITIESのMTEXT限定）')
    parser.add_argument('input_dxf', help='入力DXFファイル')
    parser.add_argument('output_file', help='出力ファイル（.txt）')
    parser.add_argument('--filter', action='store_true', 
                        help='除外条件に該当するラベルを出力しません。以下の条件に合致するラベルは部品番号でないと判断して除外します：\n'
                             '                - 最初の文字が「(」のラベル\n'
                             '                - 最初の文字が数字のラベル\n'
                             '                - 最初の文字が英小文字のラベル\n'
                             '                - 「GND」を含むラベル\n'
                             '                - 英字１文字のみのラベル（例：R, C）\n'
                             '                - 英字１文字に続いて数字（例：R1, C2, L3）\n'
                             '                - 英字１文字に続いて数字と「.」からなる文字列の組み合わせ（例：C1.1, R5.2, L1.1, N1.3）\n'
                             '                - 英字と「+」もしくは「-」の組み合わせ（例：A+, VCC-）')
    parser.add_argument('--sort', choices=['asc', 'desc', 'none'], default='none', 
                        help='ラベルのソート順を指定（asc=昇順, desc=降順, none=ソートなし）')
    
    args = parser.parse_args()

    if not args.output_file.endswith('.txt'):
        print("⚠️  警告: 拡張子が '.txt' 以外は指定できません。")
        sys.exit(1)

    try:
        # DXFフォーマットコード除去用の正規表現
        FORMAT_CODE_PATTERN = re.compile(r'(\\[A-Za-z0-9\.]+;)')

        doc = ezdxf.readfile(args.input_dxf)
        msp = doc.modelspace()

        labels = []

        # モデルスペース内のMTEXTのみ抽出
        for entity in msp:
            if entity.dxftype() == 'MTEXT':
                text = entity.dxf.text
                cleaned = FORMAT_CODE_PATTERN.sub('', text)
                cleaned = cleaned.replace('\\P', ' ').strip()  # 段落コードも除去
                
                if cleaned:
                    labels.append(cleaned)

        # フィルタリングオプションが有効な場合
        if args.filter:
            original_count = len(labels)
            labels = [label for label in labels if not is_non_part_number(label)]
            filtered_count = original_count - len(labels)
            print(f"フィルタリング: {filtered_count}個のラベルを除外しました")

        # ソートオプションに応じてソート
        if args.sort == 'asc':
            labels.sort()
            print("ラベルを昇順でソートしました")
        elif args.sort == 'desc':
            labels.sort(reverse=True)
            print("ラベルを降順でソートしました")

        # ファイルに書き込み
        with open(args.output_file, 'w', encoding='utf-8') as f:
            for label in labels:
                f.write(label + "\n")

        print(f"ラベル抽出完了: {len(labels)}個のラベルを出力しました")
        print(f"出力ファイル: {args.output_file}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

    if re.match(pattern1, label):
        return True
        
    # 英字と「+」もしくは「-」の組み合わせ（例：A+, VCC-）
    pattern2 = r'^[A-Za-z]+[\+\-]

def main():
    parser = argparse.ArgumentParser(description='ラベルを抽出してテキストファイルに出力（ENTITIESのMTEXT限定）')
    parser.add_argument('input_dxf', help='入力DXFファイル')
    parser.add_argument('output_file', help='出力ファイル（.txt）')
    parser.add_argument('--filter', action='store_true', help='部品番号ではないと思われるラベルを除外する')
    parser.add_argument('--sort', choices=['asc', 'desc', 'none'], default='none', 
                        help='ラベルのソート順を指定（asc=昇順, desc=降順, none=ソートなし）')
    
    args = parser.parse_args()

    if not args.output_file.endswith('.txt'):
        print("⚠️  警告: 拡張子が '.txt' 以外は指定できません。")
        sys.exit(1)

    try:
        # DXFフォーマットコード除去用の正規表現
        FORMAT_CODE_PATTERN = re.compile(r'(\\[A-Za-z0-9\.]+;)')

        doc = ezdxf.readfile(args.input_dxf)
        msp = doc.modelspace()

        labels = []

        # モデルスペース内のMTEXTのみ抽出
        for entity in msp:
            if entity.dxftype() == 'MTEXT':
                text = entity.dxf.text
                cleaned = FORMAT_CODE_PATTERN.sub('', text)
                cleaned = cleaned.replace('\\P', ' ').strip()  # 段落コードも除去
                
                if cleaned:
                    labels.append(cleaned)

        # フィルタリングオプションが有効な場合
        if args.filter:
            original_count = len(labels)
            labels = [label for label in labels if not is_non_part_number(label)]
            filtered_count = original_count - len(labels)
            print(f"フィルタリング: {filtered_count}個のラベルを除外しました")

        # ソートオプションに応じてソート
        if args.sort == 'asc':
            labels.sort()
            print("ラベルを昇順でソートしました")
        elif args.sort == 'desc':
            labels.sort(reverse=True)
            print("ラベルを降順でソートしました")

        # ファイルに書き込み
        with open(args.output_file, 'w', encoding='utf-8') as f:
            for label in labels:
                f.write(label + "\n")

        print(f"ラベル抽出完了: {len(labels)}個のラベルを出力しました")
        print(f"出力ファイル: {args.output_file}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

    if re.match(pattern2, label):
        return True
        
    return False

def main():
    parser = argparse.ArgumentParser(description='ラベルを抽出してテキストファイルに出力（ENTITIESのMTEXT限定）')
    parser.add_argument('input_dxf', help='入力DXFファイル')
    parser.add_argument('output_file', help='出力ファイル（.txt）')
    parser.add_argument('--filter', action='store_true', help='部品番号ではないと思われるラベルを除外する')
    parser.add_argument('--sort', choices=['asc', 'desc', 'none'], default='none', 
                        help='ラベルのソート順を指定（asc=昇順, desc=降順, none=ソートなし）')
    
    args = parser.parse_args()

    if not args.output_file.endswith('.txt'):
        print("⚠️  警告: 拡張子が '.txt' 以外は指定できません。")
        sys.exit(1)

    try:
        # DXFフォーマットコード除去用の正規表現
        FORMAT_CODE_PATTERN = re.compile(r'(\\[A-Za-z0-9\.]+;)')

        doc = ezdxf.readfile(args.input_dxf)
        msp = doc.modelspace()

        labels = []

        # モデルスペース内のMTEXTのみ抽出
        for entity in msp:
            if entity.dxftype() == 'MTEXT':
                text = entity.dxf.text
                cleaned = FORMAT_CODE_PATTERN.sub('', text)
                cleaned = cleaned.replace('\\P', ' ').strip()  # 段落コードも除去
                
                if cleaned:
                    labels.append(cleaned)

        # フィルタリングオプションが有効な場合
        if args.filter:
            original_count = len(labels)
            labels = [label for label in labels if not is_non_part_number(label)]
            filtered_count = original_count - len(labels)
            print(f"フィルタリング: {filtered_count}個のラベルを除外しました")

        # ソートオプションに応じてソート
        if args.sort == 'asc':
            labels.sort()
            print("ラベルを昇順でソートしました")
        elif args.sort == 'desc':
            labels.sort(reverse=True)
            print("ラベルを降順でソートしました")

        # ファイルに書き込み
        with open(args.output_file, 'w', encoding='utf-8') as f:
            for label in labels:
                f.write(label + "\n")

        print(f"ラベル抽出完了: {len(labels)}個のラベルを出力しました")
        print(f"出力ファイル: {args.output_file}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()