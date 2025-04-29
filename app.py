import streamlit as st
import pandas as pd
import os
import re
import subprocess
import tempfile
import time
import glob
import shutil
from datetime import datetime
import sys
import io
import threading

# タイトルと概要の設定
st.title("電気設計支援ツール")
st.markdown("""
このツールは、電気設計業務をサポートするための各種機能を提供します。DXF図面の比較、部品リストの抽出と照合、DXF構造の分析などが可能です。
""")

# サイドバーでツール選択
tool_option = st.sidebar.selectbox(
    "機能を選択してください",
    [
        "DXF図面比較 (図形要素の変更点を可視化)", 
        "DXFラベル抽出", 
        "部品リスト比較", 
        "回路記号リスト抽出 (Excel部品表から)",
        "DXF構造分析",
        "DXF階層構造表示"
    ]
)

# アップロードされたファイルを一時ディレクトリに保存する関数
def save_uploaded_file(uploaded_file, directory=None):
    if directory is None:
        directory = tempfile.mkdtemp()
    
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    file_path = os.path.join(directory, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    return file_path, directory

# プロセス実行とリアルタイム出力表示用
def run_process_with_output(cmd, cwd=None):
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd
    )
    
    output = []
    output_area = st.empty()
    
    for line in iter(process.stdout.readline, ''):
        output.append(line)
        output_area.text("".join(output))
        
    process.stdout.close()
    return_code = process.wait()
    
    if return_code != 0:
        st.error(f"エラーが発生しました (終了コード: {return_code})")
        
    return "".join(output), return_code

# コマンド実行関数（リアルタイム出力のためのラッパー）
def execute_command(cmd, cwd=None):
    output_container = st.empty()
    output_text = ""
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        cwd=cwd
    )
    
    # リアルタイムでプロセスの出力を表示
    for line in iter(process.stdout.readline, ''):
        output_text += line
        output_container.text(output_text)
    
    process.wait()
    return process.returncode, output_text

# 処理完了後の結果表示
def show_result_file(file_path, file_type):
    if not os.path.exists(file_path):
        st.error(f"結果ファイルが見つかりません: {file_path}")
        return
    
    # ファイルタイプに応じた表示方法
    if file_type == "dxf":
        st.success(f"DXFファイルが生成されました: {os.path.basename(file_path)}")
        # DXFはダウンロード用リンクのみ提供
        with open(file_path, "rb") as file:
            st.download_button(
                label="DXFファイルをダウンロード",
                data=file,
                file_name=os.path.basename(file_path),
                mime="application/dxf"
            )
    elif file_type == "txt":
        st.success(f"テキストファイルが生成されました: {os.path.basename(file_path)}")
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            st.text_area("ファイル内容", content, height=400)
            st.download_button(
                label="テキストファイルをダウンロード",
                data=content,
                file_name=os.path.basename(file_path),
                mime="text/plain"
            )
    elif file_type == "md":
        st.success(f"Markdownファイルが生成されました: {os.path.basename(file_path)}")
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            st.markdown(content)
            st.download_button(
                label="Markdownファイルをダウンロード",
                data=content,
                file_name=os.path.basename(file_path),
                mime="text/markdown"
            )
    elif file_type in ["xlsx", "csv"]:
        st.success(f"データファイルが生成されました: {os.path.basename(file_path)}")
        if file_type == "xlsx":
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
        
        st.dataframe(df, height=400)
        
        # ダウンロード用のボタン
        with open(file_path, "rb") as file:
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file_type == "xlsx" else "text/csv"
            st.download_button(
                label=f"{file_type.upper()}ファイルをダウンロード",
                data=file,
                file_name=os.path.basename(file_path),
                mime=mime_type
            )

# ------ ツール別の機能実装 ------

# DXF図面比較ツール
if tool_option == "DXF図面比較 (図形要素の変更点を可視化)":
    st.header("DXF図面比較")
    st.markdown("""
    2つのDXFファイルを比較し、図形要素の差分をDXF形式で可視化します。
    
    - 緑色（ADDED）：追加された要素
    - 赤色（REMOVED）：削除された要素
    - 青色（MODIFIED）：変更された要素
    - 白色（UNCHANGED）：変更なしの要素
    """)
    
    # ファイルアップロード
    file_a = st.file_uploader("基準となるDXFファイル (A)", type=["dxf"])
    file_b = st.file_uploader("比較対象のDXFファイル (B)", type=["dxf"])
    
    # 許容誤差の設定
    tolerance = st.slider("浮動小数点比較の許容誤差", min_value=1e-10, max_value=1e-2, value=1e-6, format="%.0e")
    
    if st.button("比較実行", disabled=(file_a is None or file_b is None)):
        with st.spinner("DXFファイルを比較中..."):
            # 一時ディレクトリの作成
            temp_dir = tempfile.mkdtemp()
            
            # ファイルを一時ディレクトリに保存
            file_a_path, _ = save_uploaded_file(file_a, temp_dir)
            file_b_path, _ = save_uploaded_file(file_b, temp_dir)
            
            # 出力ファイル名を設定
            output_file = os.path.join(temp_dir, f"{os.path.splitext(file_a.name)[0]}_compared_with_{os.path.splitext(file_b.name)[0]}.dxf")
            
            # コマンド実行
            cmd = [
                "python", "dxf_compare_dxf.py",
                file_a_path,
                file_b_path,
                output_file,
                "--tolerance", str(tolerance)
            ]
            
            # プロセス実行と出力表示
            st.text("処理中...")
            returncode, output = execute_command(cmd)
            
            if returncode == 0:
                # 結果表示
                show_result_file(output_file, "dxf")
            else:
                st.error("DXF比較処理中にエラーが発生しました。")

# DXF部品ラベル抽出ツール
elif tool_option == "DXFラベル抽出":
    st.header("DXFラベル抽出")
    st.markdown("""
    DXFファイルからMTEXT要素のラベルを抽出し、テキストファイルに出力します。
    部品記号だけを出力するフィルタリング機能があります。
    """)
    
    # ファイルアップロード
    dxf_file = st.file_uploader("DXFファイル", type=["dxf"])
    
    # 抽出オプション
    col1, col2 = st.columns(2)
    with col1:
        filter_option = st.checkbox("部品記号だけを出力", value=True)
    with col2:
        sort_option = st.selectbox(
            "ソート順", 
            [("昇順", "asc"), ("降順", "desc"), ("ソートなし", "none")],
            format_func=lambda x: x[0]
        )
    
    verbose_option = st.checkbox("詳細情報を表示", value=False)
    
    if st.button("抽出実行", disabled=(dxf_file is None)):
        with st.spinner("DXFファイルからラベルを抽出中..."):
            # 一時ディレクトリの作成
            temp_dir = tempfile.mkdtemp()
            
            # ファイルを一時ディレクトリに保存
            dxf_file_path, _ = save_uploaded_file(dxf_file, temp_dir)
            
            # 出力ファイル名を設定
            output_file = os.path.join(temp_dir, f"{os.path.splitext(dxf_file.name)[0]}_labels.txt")
            
            # コマンド実行
            cmd = [
                "python", "dxf_extract_labels.py",
                dxf_file_path,
                output_file
            ]
            
            if filter_option:
                cmd.append("--filter")
            else:
                cmd.append("--no-filter")
                
            if sort_option[1] != "none":
                cmd.extend(["--sort", sort_option[1]])
                
            if verbose_option:
                cmd.append("--verbose")
            
            # プロセス実行と出力表示
            st.text("処理中...")
            returncode, output = execute_command(cmd)
            
            if returncode == 0:
                # 結果表示
                st.text(output)
                show_result_file(output_file, "txt")
            else:
                st.error("ラベル抽出処理中にエラーが発生しました。")

# 部品リスト比較ツール
elif tool_option == "部品リスト比較":
    st.header("部品リスト比較")
    st.markdown("""
    2つの部品リストファイル（テキスト形式）を比較し、差分をマークダウン形式で出力します。
    DXF図面から抽出した部品ラベルと回路記号（部品表など）のリストを照合するのに役立ちます。
    """)
    
    # ファイルアップロード
    file_a = st.file_uploader("図面上の部品ラベルリスト", type=["txt"], help="DXFラベル抽出ツールで抽出したテキストファイル")
    file_b = st.file_uploader("回路図シンボルリスト", type=["txt"], help="回路記号リスト抽出ツールで抽出したテキストファイル")
    
    verbose_option = st.checkbox("詳細情報を表示", value=False)
    
    if st.button("比較実行", disabled=(file_a is None or file_b is None)):
        with st.spinner("部品リストを比較中..."):
            # 一時ディレクトリの作成
            temp_dir = tempfile.mkdtemp()
            
            # ファイルを一時ディレクトリに保存
            file_a_path, _ = save_uploaded_file(file_a, temp_dir)
            file_b_path, _ = save_uploaded_file(file_b, temp_dir)
            
            # 出力ファイル名を設定
            output_file = os.path.join(temp_dir, f"{os.path.splitext(file_a.name)[0]}_vs_{os.path.splitext(file_b.name)[0]}.md")
            
            # コマンド実行
            cmd = [
                "python", "dxf_compare_partslist.py",
                file_a_path,
                file_b_path,
                output_file
            ]
            
            if verbose_option:
                cmd.append("--verbose")
            
            # プロセス実行と出力表示
            st.text("処理中...")
            returncode, output = execute_command(cmd)
            
            if returncode == 0:
                # 結果表示
                st.text(output)
                show_result_file(output_file, "md")
            else:
                st.error("部品リスト比較処理中にエラーが発生しました。")

# 回路記号リスト抽出ツール
elif tool_option == "回路記号リスト抽出 (Excel部品表から)":
    st.header("回路記号リスト抽出")
    st.markdown("""
    Excel形式の部品表（構成表）から回路記号リストを抽出します。
    Excelファイル名は、抽出対象となるアセンブリ番号と一致させてください。
    """)
    
    # ファイルアップロード
    excel_file = st.file_uploader("Excelファイル（部品表）", type=["xlsx"])
    
    if st.button("抽出実行", disabled=(excel_file is None)):
        with st.spinner("Excelファイルから回路記号を抽出中..."):
            # 一時ディレクトリの作成
            temp_dir = tempfile.mkdtemp()
            
            # ファイルを一時ディレクトリに保存
            excel_file_path, _ = save_uploaded_file(excel_file, temp_dir)
            
            # 出力ファイル名を設定
            output_file = os.path.join(temp_dir, f"{os.path.splitext(excel_file.name)[0]}_circuit_symbols.txt")
            
            # コマンド実行
            cmd = [
                "python", "extract_symbols.py",
                excel_file_path,
                output_file
            ]
            
            # プロセス実行と出力表示
            st.text("処理中...")
            returncode, output = execute_command(cmd)
            
            if returncode == 0:
                # 結果表示
                st.text(output)
                show_result_file(output_file, "txt")
            else:
                st.error("回路記号リスト抽出処理中にエラーが発生しました。")

# DXF構造分析ツール
elif tool_option == "DXF構造分析":
    st.header("DXF構造分析")
    st.markdown("""
    DXFファイルの構造を詳細に分析し、ExcelまたはCSV形式で出力します。
    大量のデータがある場合はCSVで出力されます。
    """)
    
    # ファイルアップロード
    dxf_file = st.file_uploader("DXFファイル", type=["dxf"])
    
    # 出力フォーマット
    output_format = st.radio(
        "出力フォーマット",
        [("Excel", "xlsx"), ("CSV", "csv")],
        format_func=lambda x: x[0]
    )
    
    split_option = st.checkbox("セクションごとに別ファイルに分割", value=False)
    
    if st.button("分析実行", disabled=(dxf_file is None)):
        with st.spinner("DXFファイルを分析中..."):
            # 一時ディレクトリの作成
            temp_dir = tempfile.mkdtemp()
            
            # ファイルを一時ディレクトリに保存
            dxf_file_path, _ = save_uploaded_file(dxf_file, temp_dir)
            
            # 出力ファイル名を設定
            output_file = os.path.join(temp_dir, f"{os.path.splitext(dxf_file.name)[0]}_structure.{output_format[1]}")
            
            # コマンド実行
            cmd = [
                "python", "dxf_structure_record.py",
                dxf_file_path,
                output_file
            ]
            
            if output_format[1] == "csv":
                cmd.append("--csv")
                
            if split_option:
                cmd.append("--split")
            
            # プロセス実行と出力表示
            st.text("処理中...")
            returncode, output = execute_command(cmd)
            
            if returncode == 0:
                # 結果表示
                st.text(output)
                
                # 分割ファイルか単一ファイルかでの表示切り替え
                if split_option:
                    # 分割ファイルの場合、すべてのファイルを検索して表示
                    result_files = glob.glob(os.path.join(temp_dir, f"{os.path.splitext(dxf_file.name)[0]}_structure_*.{output_format[1]}"))
                    
                    if result_files:
                        st.success(f"{len(result_files)}個のファイルが生成されました")
                        
                        for file_path in result_files:
                            with st.expander(f"ファイル: {os.path.basename(file_path)}"):
                                show_result_file(file_path, output_format[1])
                    else:
                        st.error("生成されたファイルが見つかりません")
                else:
                    # 単一ファイルの場合
                    show_result_file(output_file, output_format[1])
            else:
                st.error("DXF構造分析処理中にエラーが発生しました。")

# DXF階層構造表示ツール
elif tool_option == "DXF階層構造表示":
    st.header("DXF階層構造表示")
    st.markdown("""
    DXFファイルの階層構造をMarkdownフォーマットで表示します。
    DXFファイルのセクション、テーブル、ブロック、エンティティ、オブジェクトなどの構造を確認できます。
    """)
    
    # ファイルアップロード
    dxf_file = st.file_uploader("DXFファイル", type=["dxf"])
    
    if st.button("階層構造表示", disabled=(dxf_file is None)):
        with st.spinner("DXFファイルの階層構造を解析中..."):
            # 一時ディレクトリの作成
            temp_dir = tempfile.mkdtemp()
            
            # ファイルを一時ディレクトリに保存
            dxf_file_path, _ = save_uploaded_file(dxf_file, temp_dir)
            
            # 出力ファイル名を設定
            output_file = os.path.join(temp_dir, f"{os.path.splitext(dxf_file.name)[0]}_hierarchy.md")
            
            # コマンド実行
            cmd = [
                "python", "dxf_hierarchy.py",
                dxf_file_path,
                output_file
            ]
            
            # プロセス実行と出力表示
            st.text("処理中...")
            returncode, output = execute_command(cmd)
            
            if returncode == 0:
                # 結果表示
                show_result_file(output_file, "md")
            else:
                st.error("DXF階層構造表示処理中にエラーが発生しました。")

# フッター情報
st.sidebar.markdown("---")
st.sidebar.markdown("### 電気設計支援ツール")
st.sidebar.markdown("バージョン: 1.0.0")
st.sidebar.markdown(f"最終更新日: {datetime.now().strftime('%Y-%m-%d')}")
st.sidebar.markdown("開発者: DX設計チーム")
st.sidebar.markdown("---")
st.sidebar.markdown("© 2025 製品開発支援ソリューション")