# =================================================================
# history_list.py - 履歴表示・PF2形式CSV出力・経路GeoJSON出力
# =================================================================
import streamlit as st
import pandas as pd
import constants
from datetime import datetime
import json
import re

def parse_rm_coords_for_geojson(rm_str):
    """RM位置座標の文字列 [[lat,lon],...] をGeoJSON用の [lon,lat] リストに変換"""
    if not rm_str or "[[" not in rm_str:
        return None
    try:
        # スペースを詰め、JSONとしてパース
        coords_list = json.loads(rm_str.replace(" ", ""))
        if isinstance(coords_list, list) and len(coords_list) > 0:
            # [lat, lon] -> [lon, lat] に変換
            return [[c[1], c[0]] for c in coords_list if len(c) == 2]
    except:
        return None
    return None

def generate_geojson(records):
    """保存された全レコードからGeoJSON FeatureCollectionを作成"""
    features = []
    for rec in records:
        geometry = None
        rm_path = parse_rm_coords_for_geojson(rec.get("RM位置座標", ""))
        
        if rm_path:
            if len(rm_path) > 1:
                # 複数点あれば LineString (線)
                geometry = {
                    "type": "LineString",
                    "coordinates": rm_path
                }
            else:
                # 1点のみなら Point (点)
                geometry = {
                    "type": "Point",
                    "coordinates": rm_path[0]
                }
        else:
            # RM位置座標がない場合のフォールバック: 始点緯度経度を使用
            s_latlon = rec.get("始点緯度経度", "")
            if s_latlon:
                try:
                    parts = s_latlon.replace(" ", "").split(",")
                    geometry = {
                        "type": "Point",
                        "coordinates": [float(parts[1]), float(parts[0])]
                    }
                except:
                    pass
        
        if geometry:
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": rec  # 全50項目を属性として保持
            })
            
    return {
        "type": "FeatureCollection",
        "features": features
    }

def render_history():
    st.subheader("📋 規制案件一覧")
    
    if not st.session_state.records:
        st.info("登録された案件はありません。")
        return

    # DataFrame表示
    df = pd.DataFrame(st.session_state.records)
    
    # メイン画面には主要な項目のみ表示
    display_cols = ["タイトル", "路線名", "規制種別", "規制理由", "始点住所", "記入日時"]
    # 登録順の逆順（新しい順）で表示
    st.dataframe(df[display_cols].iloc[::-1], use_container_width=True)

    st.divider()
    st.write("### 📥 データのダウンロード")
    c_csv, c_geojson = st.columns(2)

    # 1. PF2形式CSV出力 (原本適合50列)
    csv_df = df[constants.PF2_COLUMNS]
    csv_data = csv_df.to_csv(index=False).encode('utf-8-sig')
    
    c_csv.download_button(
        "📄 PF2形式CSVを保存",
        data=csv_data,
        file_name=f"TrafficPF2_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )

    # 2. 経路GeoJSON出力 (新機能)
    geojson_data = generate_geojson(st.session_state.records)
    geojson_str = json.dumps(geojson_data, ensure_ascii=False, indent=2)
    
    c_geojson.download_button(
        "🌍 経路GeoJSONを保存",
        data=geojson_str.encode('utf-8'),
        file_name=f"RoadPath_{datetime.now().strftime('%Y%m%d_%H%M')}.geojson",
        mime="application/geo+json",
        use_container_width=True
    )

    # 管理操作
    with st.expander("📝 データの管理"):
        target_idx = st.number_input("操作する行番号 (1から表示順)", min_value=1, max_value=len(st.session_state.records), step=1)
        # DataFrameのインデックスに合わせる
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

    if st.button("🗑️ すべてのデータを消去する"):
        if st.checkbox("本当に消去しますか？"):
            st.session_state.records = []
            st.rerun()