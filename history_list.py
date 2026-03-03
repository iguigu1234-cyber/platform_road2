# =================================================================
# history_list.py - フィルタリング・項目整理・各種出力
# =================================================================
import streamlit as st
import pandas as pd
import constants
from datetime import datetime
import json

def parse_rm_coords_for_geojson(rm_str):
    if not rm_str or "[[" not in rm_str: return None
    try:
        coords_list = json.loads(rm_str.replace(" ", ""))
        if isinstance(coords_list, list) and len(coords_list) > 0:
            return [[c[1], c[0]] for c in coords_list if len(c) == 2]
    except: return None
    return None

def generate_geojson(records_df):
    features = []
    for _, rec in records_df.iterrows():
        geometry = None
        rm_path = parse_rm_coords_for_geojson(rec.get("RM位置座標", ""))
        
        if rm_path:
            geometry = {"type": "LineString", "coordinates": rm_path} if len(rm_path) > 1 else {"type": "Point", "coordinates": rm_path[0]}
        else:
            s_latlon = rec.get("始点緯度経度", "")
            if s_latlon:
                try:
                    parts = s_latlon.replace(" ", "").split(",")
                    geometry = {"type": "Point", "coordinates": [float(parts[1]), float(parts[0])]}
                except: pass
        
        if geometry:
            features.append({"type": "Feature", "geometry": geometry, "properties": rec.to_dict()})
            
    return {"type": "FeatureCollection", "features": features}

def render_history():
    st.subheader("📋 規制案件一覧")
    
    if not st.session_state.records:
        st.info("登録された案件はありません。")
        return

    # 全データをDataFrame化
    df = pd.DataFrame(st.session_state.records)

    # --- ① フィルタリング機能 ---
    search_query = st.text_input("🔍 県、市、路線名などで絞り込み", placeholder="例: 茨城県, 国道6号...")
    
    if search_query:
        mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        filtered_df = df[mask]
    else:
        filtered_df = df

    # --- ② 代表項目の表示設定 ---
    # カラムが存在しない場合のエラー防止
    display_cols = ["県名", "市町村名", "路線番号", "路線名", "始点住所", "記入日時"]
    available_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(filtered_df[available_cols].iloc[::-1], use_container_width=True)
    st.write(f"表示中: {len(filtered_df)} 件 / 全 {len(df)} 件")

    st.divider()
    st.write("### 📥 データのダウンロード")
    c_csv, c_geojson = st.columns(2)

    # CSV出力 (原本適合50列、フィルタ結果を反映)
    csv_data = filtered_df[constants.PF2_COLUMNS].to_csv(index=False).encode('utf-8-sig')
    c_csv.download_button(
        "📄 PF2形式CSVを保存",
        data=csv_data,
        file_name=f"TrafficPF2_{datetime.now().strftime('%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )

    # GeoJSON出力 (フィルタ結果を反映)
    geojson_data = generate_geojson(filtered_df)
    geojson_str = json.dumps(geojson_data, ensure_ascii=False, indent=2)
    c_geojson.download_button(
        "🌍 経路GeoJSONを保存",
        data=geojson_str.encode('utf-8'),
        file_name=f"RoadPath_{datetime.now().strftime('%m%d_%H%M')}.geojson",
        mime="application/geo+json",
        use_container_width=True
    )

    # 管理操作
    with st.expander("📝 データの管理"):
        target_idx = st.number_input("操作する行番号 (1から表示順)", min_value=1, max_value=len(st.session_state.records), step=1)
        real_idx = len(st.session_state.records) - target_idx 
        
        c1, c2 = st.columns(2)
        if c1.button("選択した内容を入力フォームに戻す"):
            rec = st.session_state.records[real_idx]
            for col in constants.PF2_COLUMNS:
                st.session_state[col] = rec.get(col, "")
            st.success("フォームに展開しました。入力画面に戻って修正してください。")
            
        if c2.button("選択した内容を削除する", type="secondary"):
            st.session_state.records.pop(real_idx)
            st.rerun()