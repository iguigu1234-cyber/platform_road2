# =================================================================
# history_list.py - フィルタリング・項目整理・出力
# =================================================================
import streamlit as st
import pandas as pd
import constants
from datetime import datetime
import json

def generate_geojson(df):
    features = []
    for _, r in df.iterrows():
        try:
            coords = json.loads(r.get("RM位置座標", "[]"))
            if len(coords) > 1:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": [[c[1], c[0]] for c in coords]},
                    "properties": r.to_dict()
                })
        except: pass
    return json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False)

def render_history():
    st.subheader("📋 規制案件一覧")
    if not st.session_state.records:
        st.info("データがありません。")
        return

    df = pd.DataFrame(st.session_state.records)
    
    # --- フィルタリング機能 ---
    q = st.text_input("🔍 絞り込み (県, 市, 路線番号, 路線名など)", placeholder="例: 茨城県, 国道6号...")
    if q:
        df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)]

    # --- 代表項目の表示 ---
    display_cols = ["県名", "市町村名", "路線番号", "路線名", "始点住所", "記入日時"]
    st.dataframe(df[display_cols].iloc[::-1], use_container_width=True)
    st.write(f"表示中: {len(df)} 件")

    st.divider()
    c1, c2 = st.columns(2)
    # CSV出力
    csv = df[constants.PF2_COLUMNS].to_csv(index=False).encode('utf-8-sig')
    c1.download_button("📄 PF2形式CSVを保存", data=csv, file_name=f"TrafficPF2_{datetime.now().strftime('%m%d%H%M')}.csv", use_container_width=True)
    
    # GeoJSON出力
    gj = generate_geojson(df)
    c2.download_button("🌍 経路GeoJSONを保存", data=gj.encode('utf-8'), file_name=f"RoadPath_{datetime.now().strftime('%m%d%H%M')}.geojson", use_container_width=True)

    with st.expander("📝 データ管理"):
        idx = st.number_input("行番号", min_value=1, max_value=len(st.session_state.records), step=1)
        real_idx = len(st.session_state.records) - idx
        if st.button("フォームに戻す"):
            rec = st.session_state.records[real_idx]
            for k, v in rec.items(): st.session_state[k] = v
            st.success("展開完了。入力タブへ移動してください。")