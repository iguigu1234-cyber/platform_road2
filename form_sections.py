# =================================================================
# form_sections.py - UI定義（Rerun処理追加版）
# =================================================================
import streamlit as st
import folium
import json
import re
from streamlit_folium import st_folium
import constants
from datetime import datetime

def clean_latlon(input_str):
    if not input_str: return None
    s = str(input_str).replace("　", " ").replace("，", ",").replace("\n", "").strip()
    match = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", s)
    if len(match) >= 2:
        try: return float(match[0]), float(match[1])
        except: return None
    return None

def render_preview_map():
    s_coords = clean_latlon(st.session_state.get("始点緯度経度"))
    e_coords = clean_latlon(st.session_state.get("終点緯度経度"))
    rm_str = st.session_state.get("RM位置座標", "")
    
    center = s_coords if s_coords else [35.68, 139.76]
    m = folium.Map(location=center, zoom_start=12)
    folium.TileLayer(tiles='https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', attr='国土地理院').add_to(m)

    if s_coords: folium.Marker(s_coords, tooltip="始点", icon=folium.Icon(color='blue')).add_to(m)
    if e_coords: folium.Marker(e_coords, tooltip="終点", icon=folium.Icon(color='red')).add_to(m)
    
    if "[[" in rm_str:
        try:
            path = json.loads(rm_str)
            if len(path) > 1: folium.PolyLine(path, color="blue", weight=5).add_to(m)
        except: pass
    
    st_folium(m, width=900, height=350, key="main_map_preview")

def render_form(api_service):
    # --- 1. 基本・管理情報 ---
    st.markdown('<div class="section-header">1. 基本・管理情報</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    st.session_state["タイプ"] = c1.selectbox("タイプ", constants.MASTER_DATA["types"], index=constants.MASTER_DATA["types"].index(st.session_state.get("タイプ", "点")))
    st.session_state["アイコン番号"] = c2.text_input("アイコン番号", value=st.session_state.get("アイコン番号", ""))
    st.session_state["サイズ"] = c3.text_input("サイズ", value=st.session_state.get("サイズ", ""))
    st.session_state["線・面の色"] = c4.text_input("線・面の色", value=st.session_state.get("線・面の色", ""))
    c5, c6, c7, c8 = st.columns(4)
    st.session_state["不透明度(%)"] = c5.text_input("不透明度(%)", value=st.session_state.get("不透明度(%)", ""))
    st.session_state["タイトル"] = c6.text_input("タイトル(案件名)", value=st.session_state.get("タイトル", ""))
    st.session_state["記入日時"] = c7.text_input("記入日時", value=st.session_state.get("記入日時", datetime.now().strftime("%Y/%m/%d %H:%M")))
    st.session_state["報番号"] = c8.text_input("報番号", value=st.session_state.get("報番号", ""))
    st.session_state["RM位置座標"] = st.text_area("RM位置座標", value=st.session_state.get("RM位置座標", ""), height=80)

    # --- 2. 路線属性情報 ---
    st.markdown('<div class="section-header">2. 路線属性情報</div>', unsafe_allow_html=True)
    c21, c22, c23, c24 = st.columns(4)
    st.session_state["整備局名"] = c21.text_input("整備局名", value=st.session_state.get("整備局名", ""))
    st.session_state["県名"] = c22.text_input("県名", value=st.session_state.get("県名", ""))
    st.session_state["市町村名"] = c23.text_input("市町村名", value=st.session_state.get("市町村名", ""))
    st.session_state["24時間交通量_平日"] = c24.text_input("24H交通量(平日)", value=st.session_state.get("24時間交通量_平日", ""))
    c25, c26, c27, c28 = st.columns(4)
    st.session_state["道路管理者"] = c25.text_input("道路管理者", value=st.session_state.get("道路管理者", ""))
    st.session_state["道路種別"] = c26.text_input("道路種別", value=st.session_state.get("道路種別", ""))
    st.session_state["路線番号"] = c27.text_input("路線番号", value=st.session_state.get("路線番号", ""))
    st.session_state["路線名"] = c28.text_input("路線名", value=st.session_state.get("路線名", ""))

    # --- 3. 始点・終点・位置座標 ---
    st.markdown('<div class="section-header">3. 始点・終点・位置座標</div>', unsafe_allow_html=True)
    render_preview_map()

    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("🔍 道路属性一括取得（始点・終点）", type="primary", use_container_width=True):
        s = clean_latlon(st.session_state.get("始点緯度経度"))
        e = clean_latlon(st.session_state.get("終点緯度経度"))
        if s: api_service.update_info_from_apis(s[0], s[1], "始点")
        if e: api_service.update_info_from_apis(e[0], e[1], "終点")
        st.rerun() # ← これが重要：画面を強制更新して最新Valueを表示

    if btn_col2.button("🛣️ 経路座標取得 (API9)", use_container_width=True):
        token = st.session_state.get("drm_token")
        s = clean_latlon(st.session_state.get("始点緯度経度"))
        e = clean_latlon(st.session_state.get("終点緯度経度"))
        if token and s and e:
            with st.spinner("経路取得中..."):
                r_types = st.session_state.get("道路種別") or "1,2,3,4,5,6,7,8,9,18,19"
                path = api_service.fetch_route_coordinates(token, s[0], s[1], e[0], e[1], r_types)
                if path:
                    st.session_state.RM位置座標 = path
                    st.rerun()

    c31, c32 = st.columns(2)
    with c31:
        st.session_state["始点緯度経度"] = st.text_input("始点座標", value=st.session_state.get("始点緯度経度", ""))
        st.session_state["始点住所"] = st.text_input("始点住所", value=st.session_state.get("始点住所", ""))
        st.session_state["始点キロポスト"] = st.text_input("始点KP", value=st.session_state.get("始点キロポスト", ""))
    with c32:
        st.session_state["終点緯度経度"] = st.text_input("終点座標", value=st.session_state.get("終点緯度経度", ""))
        st.session_state["終点住所"] = st.text_input("終点住所", value=st.session_state.get("終点住所", ""))
        st.session_state["終点キロポスト"] = st.text_input("終点KP", value=st.session_state.get("終点キロポスト", ""))

    # --- 4. 規制内容 ---
    st.markdown('<div class="section-header">4. 規制内容</div>', unsafe_allow_html=True)
    c41, c42, c43, c44 = st.columns(4)
    st.session_state["規制種別"] = c41.selectbox("規制種別", constants.MASTER_DATA["reg_types"], index=constants.MASTER_DATA["reg_types"].index(st.session_state.get("規制種別", "")))
    st.session_state["規制理由"] = c42.text_input("規制理由", value=st.session_state.get("規制理由", ""))
    st.session_state["規制方向"] = c43.text_input("規制方向", value=st.session_state.get("規制方向", ""))
    st.session_state["延長_Km"] = c44.text_input("規制延長(km)", value=st.session_state.get("延長_Km", ""))

    c45, c46, c47, c48 = st.columns(4)
    st.session_state["規制開始_日時"] = c45.text_input("規制開始日時", value=st.session_state.get("規制開始_日時", ""))
    st.session_state["規制開始_内容"] = c46.text_input("規制開始内容", value=st.session_state.get("規制開始_内容", ""))
    st.session_state["規制変更_日時"] = c47.text_input("規制変更日時", value=st.session_state.get("規制変更_日時", ""))
    st.session_state["規制変更_内容"] = c48.text_input("規制変更内容", value=st.session_state.get("規制変更_内容", ""))

    # --- 5. 影響 ---
    st.markdown('<div class="section-header">5. 影響</div>', unsafe_allow_html=True)
    c51, c52, c53, c54, c55 = st.columns(5)
    for i, col in enumerate(["迂回路_有無", "孤立集落_有無", "人身_有無", "物損_有無", "停電_有無"]):
        st.session_state[col] = [c51, c52, c53, c54, c55][i].selectbox(col.replace("_有無", ""), constants.MASTER_DATA["yes_no"], index=constants.MASTER_DATA["yes_no"].index(st.session_state.get(col, "無")))
    c56, c57 = st.columns(2)
    st.session_state["迂回路内容"] = c56.text_input("迂回路内容", value=st.session_state.get("迂回路内容", ""))
    st.session_state["孤立集落戸数・人口"] = c57.text_input("孤立集落戸数・人口", value=st.session_state.get("孤立集落戸数・人口", ""))
    c58, c59 = st.columns(2)
    st.session_state["人身内容"] = c58.text_input("人身内容", value=st.session_state.get("人身内容", ""))
    st.session_state["物損内容"] = c59.text_input("物損内容", value=st.session_state.get("物損内容", ""))
    c510, c511 = st.columns(2)
    st.session_state["停電世帯数"] = c510.text_input("停電世帯数", value=st.session_state.get("停電世帯数", ""))
    st.session_state["マスコミ"] = c511.text_input("マスコミ", value=st.session_state.get("マスコミ", ""))
    st.session_state["備考_障害処理状況等"] = st.text_area("備考", value=st.session_state.get("備考_障害処理状況等", ""), height=80)