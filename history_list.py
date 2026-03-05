# =================================================================
# history_list.py - 履歴表示・属性別出力（展開時再描画追加）
# =================================================================
import streamlit as st
import pandas as pd
import constants
from datetime import datetime
import json
from importer_service import DataImporter

def parse_rm_coords_for_geojson(rm_str):
    if not rm_str or "[[" not in rm_str: return None
    try:
        coords_list = json.loads(rm_str.replace(" ", ""))
        return [[c[1], c[0]] for c in coords_list if len(c) == 2]
    except: return None

def generate_custom_geojson(records_df):
    features = []
    for _, rec in records_df.iterrows():
        geometry = None
        rm_path = parse_rm_coords_for_geojson(rec.get("RM位置座標", ""))
        
        if rec["タイプ"] == "点":
            s_latlon = rec.get("始点緯度経度", "")
            if s_latlon:
                try:
                    parts = s_latlon.replace(" ", "").split(",")
                    geometry = {"type": "Point", "coordinates": [float(parts[1]), float(parts[0])]}
                except: pass
        elif rec["タイプ"] == "複線":
            if rm_path: geometry = {"type": "MultiLineString", "coordinates": [rm_path]}
        else:
            if rm_path: geometry = {"type": "LineString", "coordinates": rm_path}

        if not geometry: continue

        props = {"name": rec.get("タイトル", "")}
        exclude = ["タイプ", "アイコン番号", "サイズ", "線・面の色", "不透明度(%)", "タイトル", "RM位置座標"]
        for col in constants.PF2_COLUMNS:
            if col in rec and col not in exclude:
                props[col] = rec.get(col, "")

        if rec["タイプ"] == "点":
            icon_no = str(rec.get("アイコン番号", "056")).zfill(3)
            props["_iconUrl"] = f"https://maps.gsi.go.jp/portal/sys/v4/symbols/{icon_no}.png"
            try: size = int(rec.get("サイズ", 15))
            except: size = 15
            props["_iconSize"] = [size, size]
            props["_iconAnchor"] = [size // 2, size // 2]
        else:
            props["_color"] = rec.get("線・面の色", "#ff0000")
            try: opacity = float(rec.get("不透明度(%)", 90)) / 100.0
            except: opacity = 0.9
            props["_opacity"] = opacity
            try: weight = int(rec.get("サイズ", 5))
            except: weight = 5
            props["_weight"] = weight
            props["_dashArray"] = ""

        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return {"type": "FeatureCollection", "features": features}

def render_history():
    st.subheader("📋 規制案件一覧")
    
    with st.expander("📥 データのインポート (CSV / GeoJSON)"):
        uploaded_file = st.file_uploader("ファイルを選択してください", type=["geojson", "json", "csv"])
        if uploaded_file is not None:
            if st.button("インポートを実行", type="primary"):
                new_records = DataImporter.process_file(uploaded_file)
                if new_records:
                    st.session_state.records.extend(new_records)
                    st.success(f"{len(new_records)}件のデータを読み込みました。")
                    st.rerun()

    if not st.session_state.records:
        st.info("登録された案件はありません。")
        return

    full_df = pd.DataFrame(st.session_state.records)
    full_df.index = range(1, len(full_df) + 1)
    full_df.index.name = "No."

    st.write("### 🔍 絞り込み検索")
    search_q = st.text_input("キーワード入力", placeholder="検索ワード...")
    search_filtered_df = full_df[full_df.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)] if search_q else full_df

    display_cols = ["整備局名", "県名", "市町村名", "路線番号", "路線名", "始点住所", "記入日時"]
    available_cols = [c for c in display_cols if c in search_filtered_df.columns]
    st.dataframe(search_filtered_df[available_cols].iloc[::-1], use_container_width=True)

    st.divider()
    
    st.write("### 📥 データの保存")
    export_mode = st.radio("範囲選択", ["現在の検索結果", "整備局単位で抽出", "都道府県単位で抽出"], horizontal=True)
    target_df = search_filtered_df
    if "抽出" in export_mode:
        col_name = "整備局名" if "整備局" in export_mode else "県名"
        unique_vals = sorted([v for v in full_df[col_name].unique() if v])
        if unique_vals:
            selected = st.selectbox(f"出力する{col_name}を選択", unique_vals)
            target_df = full_df[full_df[col_name] == selected]

    if not target_df.empty:
        c1, c2 = st.columns(2)
        csv_data = target_df[constants.PF2_COLUMNS].to_csv(index=False).encode('utf-8-sig')
        c1.download_button("📄 CSV保存", data=csv_data, file_name=f"PF2_{datetime.now().strftime('%m%d_%H%M')}.csv", use_container_width=True)
        gj_data = generate_custom_geojson(target_df)
        c2.download_button("🌍 GeoJSON保存", data=json.dumps(gj_data, ensure_ascii=False, indent=2).encode('utf-8'), file_name=f"RoadPath_{datetime.now().strftime('%m%d_%H%M')}.geojson", use_container_width=True)

    # 管理操作
    with st.expander("📝 データ管理 (行指定操作)"):
        idx = st.number_input("操作したい No. を入力", min_value=1, max_value=len(st.session_state.records), step=1)
        m1, m2 = st.columns(2)
        if m1.button("個票（入力フォーム）に展開"):
            rec = st.session_state.records[idx-1]
            for k, v in rec.items(): 
                st.session_state[k] = v
            st.success(f"No.{idx} を展開しました。")
            st.rerun() # [修正] 確実に再描画してフォームに反映させる
            
        if m2.button("データを削除", type="secondary"):
            st.session_state.records.pop(idx-1)
            st.rerun()