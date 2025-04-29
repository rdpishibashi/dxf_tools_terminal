# 電気設計支援ツール

電気設計業務をサポートするための統合ツールです。DXF図面の比較、部品リストの抽出と照合、構造分析などの機能を提供します。

## 概要

このアプリケーションは、電気設計の現場における効率化を目的としたDX支援ツールです。コマンドライン版のスクリプト群とWebインターフェース（Streamlit）を組み合わせて提供します。

## 機能

### 1. DXF図面比較

2つのDXFファイルを比較し、図形要素の差分をDXF形式で出力（図形差分を可視化）します。

- 緑色（ADDED）：追加された要素
- 赤色（REMOVED）：削除された要素  
- 青色（MODIFIED）：変更された要素
- 白色（UNCHANGED）：変更なしの要素

```
python dxf_compare_dxf.py file_a.dxf file_b.dxf output.dxf [--tolerance 1e-6]
```

### 2. DXF部品ラベル抽出

DXFファイルからMTEXT要素のラベルを抽出し、テキストファイルに出力します。部品記号と考えられるラベルだけを出力フィルタリング機能もあります。

```
python dxf_extract_labels.py input.dxf output.txt [--filter] [--no-filter] [--sort {asc,desc,none}] [--verbose]
```

### 3. 部品リスト比較

2つの部品リストファイル（テキスト形式）を比較し、差分をマークダウン形式で出力します。DXF図面から抽出した部品ラベルと回路記号（部品表など）のリストを照合するのに役立ちます。

```
python dxf_compare_partslist.py dxf_labels.txt circuit_symbols.txt output.md [--verbose]
```

### 4. 回路記号リスト抽出

Excel形式の部品表（構成表）から回路記号リストを抽出します。

```
python extract_symbols.py input.xlsx output.txt
```

### 5. DXF構造分析

DXFファイルの構造を詳細に分析し、ExcelまたはCSV形式で出力します。

```
python dxf_analyze_structure.py input.dxf output.xlsx [--csv] [--split]
```

### 6. DXF階層構造表示

DXFファイルの階層構造をMarkdownフォーマットで出力します。

```
python dxf_hierarchy.py input.dxf output.md
```

## Webインターフェース (Streamlit)

すべての機能を直感的に使用できるWebインターフェースも提供しています。以下のコマンドで起動します。

```
streamlit run app.py
```

## インストール方法

### 前提条件

- Python 3.8以上
- 必要なライブラリ：ezdxf, pandas, streamlit



## 利用方法

### コマンドライン版

各スクリプトは単体で実行できます。`--help` オプションを付けて実行すると、使用方法が表示されます。

例：
```
python dxf_compare_dxf.py --help
```

### Webインターフェース版

```
streamlit run app.py
```

実行後、Webブラウザで http://localhost:8501 にアクセスすることで使用できます。

## 注意事項

- DXFファイルのバージョンは R2010 で出力されます
- 大規模なDXFファイルを処理する場合、メモリ使用量にご注意ください
- 出力ファイル名に拡張子がない場合は適切な拡張子が自動的に追加されます
- 出力ファイル名が指定されていない場合は入力ファイル名をベースにしたデフォルト名を使用
- ファイル名に拡張子がない場合は適切な拡張子を自動追加
- 出力ディレクトリが存在しない場合は自動作成

