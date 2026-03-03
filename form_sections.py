# =================================================================
# form_sections.py - UI定義（個別の位置選択ボタン削除版）
# =================================================================
import streamlit as st
import folium
import json
import re
from streamlit_folium import st_folium
import constants
from datetime import datetime

def clean_latlon(input_str):
    """入力文字列を解析して(lat, lon)を返す。全角・スペース等に対応"""
    if not input_str: return None
    s = str(input_str).replace("　", " ").replace("，", ",").replace("\n", "").strip()
    match = re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", s)
    if len(match) >= 2:
        try: return float(match[0]), float(match[1])
        except: return None
    return None

def parse_rm_coords(rm_str):
    """RM位置座標の文字列をリストに変換"""
    if not rm_str or "[[" not in rm_str: return []
    try:
        json_str = rm_str.replace(" ", "")
        return json.loads(json_str)
    except:
        return []

def render_preview_map():
    """RM位置座標に基づいた経路可視化"""
    s_coords = clean_latlon(st.session_state.get("始点緯度経度"))
    e_coords = clean_latlon(st.session_state.get("終点緯度経度"))
    rm_path = parse_rm_coords(st.session_state.get("RM位置座標", ""))

    if not s_coords and not e_coords and not rm_path:
        st.info("座標が入力されると、ここにプレビューが表示されます。")
        return

    # 中心点の決定
    center = s_coords if s_coords else (e_coords if e_coords else (35.6812, 139.7671))
    m = folium.Map(location=center, zoom_start=14)
    folium.TileLayer(tiles='https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', attr='国土地理院').add_to(m)

    # 経路の描画
    if rm_path and len(rm_path) > 1:
        folium.PolyLine(rm_path, color="blue", weight=6, opacity=0.7).add_to(m)
        m.fit_bounds(rm_path)

    # 始点・終点マーカー
    if s_coords: folium.Marker(s_coords, tooltip="始点", icon=folium.Icon(color='blue')).add_to(m)
    if e_coords: folium.Marker(e_coords, tooltip="終点", icon=folium.Icon(color='red')).add_to(m)

    st_folium(m, width=800, height=350, key="preview_map")

def render_form(api_service):
    # --- 1. 基本・管理情報 ---
    st.markdown('<div class="section-header">1. 基本・管理情報</div>', unsafe_allow_html=True)
    c1_1, c1_2, c1_3, c1_4 = st.columns(4)
    st.session_state["タイプ"] = c1_1.selectbox("タイプ", constants.MASTER_DATA["types"], index=constants.MASTER_DATA["types"].index(st.session_state.get("タイプ", "点")))
    st.session_state["アイコン番号"] = c1_2.text_input("アイコン番号", value=st.session_state.get("アイコン番号", ""))
    st.session_state["サイズ"] = c1_3.text_input("サイズ", value=st.session_state.get("サイズ", ""))
    st.session_state["線・面の色"] = c1_4.text_input("線・面の色", value=st.session_state.get("線・面の色", ""))

    c1_5, c1_6, c1_7, c1_8 = st.columns(4)
    st.session_state["不透明度(%)"] = c1_5.text_input("不透明度(%)", value=st.session_state.get("不透明度(%)", ""))
    st.session_state["タイトル"] = c1_6.text_input("タイトル(案件名)", value=st.session_state.get("タイトル", ""))
    st.session_state["記入日時"] = c1_7.text_input("記入日時", value=st.session_state.get("記入日時", datetime.now().strftime("%Y/%m/%d %H:%M")))
    st.session_state["報番号"] = c1_8.text_input("報番号", value=st.session_state.get("報番号", ""))
    
    st.session_state["RM位置座標"] = st.text_area("RM位置座標", value=st.session_state.get("RM位置座標", ""), height=80)

    # --- 2. 路線属性情報 ---
    st.markdown('<div class="section-header">2. 路線属性情報</div>', unsafe_allow_html=True)
    c2_1, c2_2, c2_3, c2_4 = st.columns(4)
    st.session_state["整備局名"] = c2_1.text_input("整備局名", value=st.session_state.get("整備局名", ""))
    st.session_state["県名"] = c2_2.text_input("県名", value=st.session_state.get("県名", ""))
    st.session_state["市町村名"] = c2_3.text_input("市町村名", value=st.session_state.get("市町村名", ""))
    st.session_state["24時間交通量_平日"] = c2_4.text_input("24H交通量(平日)", value=st.session_state.get("24時間交通量_平日", ""))
    
    c2_5, c2_6, c2_7, c2_8 = st.columns(4)
    st.session_state["道路管理者"] = c2_5.text_input("道路管理者", value=st.session_state.get("道路管理者", ""))
    st.session_state["道路種別"] = c2_6.text_input("道路種別", value=st.session_state.get("道路種別", ""))
    st.session_state["路線番号"] = c2_7.text_input("路線番号", value=st.session_state.get("路線番号", ""))
    st.session_state["路線名"] = c2_8.text_input("路線名", value=st.session_state.get("路線名", ""))

    # --- 3. 始点・終点・位置座標 ---
    st.markdown('<div class="section-header">3. 始点・終点・位置座標</div>', unsafe_allow_html=True)
    render_preview_map()

    # 操作ボタンの配置
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("🔍 道路属性一括取得（始点・終点）", use_container_width=True, type="primary"):
        s = clean_latlon(st.session_state.get("始点緯度経度"))
        e = clean_latlon(st.session_state.get("終点緯度経度"))
        if s: api_service.update_info_from_apis(s[0], s[1], "始点")
        if e: api_service.update_info_from_apis(e[0], e[1], "終点")
        st.toast("一括取得と延長算定を完了しました。")
        st.rerun()

    if btn_col2.button("🛣️ 経路座標取得 (DRM-API API9)", use_container_width=True, type="secondary"):
        s_coords = clean_latlon(st.session_state.get("始点緯度経度"))
        e_coords = clean_latlon(st.session_state.get("終点緯度経度"))
        token = st.session_state.get("drm_token")
        if token and s_coords and e_coords:
            with st.spinner("経路を取得中..."):
                r_types = st.session_state.get("道路種別", "1,2,3,4,5,6,7,8,9,18,19")
                path_str = api_service.fetch_route_coordinates(token, s_coords[0], s_coords[1], e_coords[0], e_coords[1], r_types)
                if path_str:
                    st.session_state["RM位置座標"] = path_str
                    api_service.calculate_extension()
                    st.rerun()

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state["始点緯度経度"] = st.text_input("始点座標", value=st.session_state.get("始点緯度経度", ""))
        st.session_state["始点住所"] = st.text_input("始点住所", value=st.session_state.get("始点住所", ""))
        st.session_state["始点キロポスト"] = st.text_input("始点KP", value=st.session_state.get("始点キロポスト", ""))

    with col_b:
        st.session_state["終点緯度経度"] = st.text_input("終点座標", value=st.session_state.get("終点緯度経度", ""))
        st.session_state["終点住所"] = st.text_input("終点住所", value=st.session_state.get("終点住所", ""))
        st.session_state["終点キロポスト"] = st.text_input("終点KP", value=st.session_state.get("終点キロポスト", ""))

    # --- 4. 規制内容 ---
    st.markdown('<div class="section-header">4. 規制内容</div>', unsafe_allow_html=True)
    c4_1, c4_2, c4_3, c4_4 = st.columns(4)
    st.session_state["規制種別"] = c4_1.selectbox("規制種別", constants.MASTER_DATA["reg_types"], index=constants.MASTER_DATA["reg_types"].index(st.session_state.get("規制種別", "")))
    st.session_state["規制理由"] = c4_2.text_input("規制理由", value=st.session_state.get("規制理由", ""))
    st.session_state["規制方向"] = c4_3.text_input("規制方向", value=st.session_state.get("規制方向", ""))
    st.session_state["延長_Km"] = c4_4.text_input("規制延長(km) [自動算定]", value=st.session_state.get("延長_Km", ""))

    c4_5, c4_6, c4_7, c4_8 = st.columns(4)
    st.session_state["規制開始_日時"] = c4_5.text_input("規制開始日時", value=st.session_state.get("規制開始_日時", ""))
    st.session_state["規制開始_内容"] = c4_6.text_input("規制開始内容", value=st.session_state.get("規制開始_内容", ""))
    st.session_state["規制変更_日時"] = c4_7.text_input("規制変更日時", value=st.session_state.get("規制変更_日時", ""))
    st.session_state["規制変更_内容"] = c4_8.text_input("規制変更内容", value=st.session_state.get("規制変更_内容", ""))

    # --- 5. 影響 ---
    st.markdown('<div class="section-header">5. 影響</div>', unsafe_allow_html=True)
    c5_1, c5_2, c5_3, c5_4, c5_5 = st.columns(5)
    st.session_state["迂回路_有無"] = c5_1.selectbox("迂回路", constants.MASTER_DATA["yes_no"], index=constants.MASTER_DATA["yes_no"].index(st.session_state.get("迂回路_有無", "無")))
    st.session_state["孤立集落_有無"] = c5_2.selectbox("孤立集落", constants.MASTER_DATA["yes_no"], index=constants.MASTER_DATA["yes_no"].index(st.session_state.get("孤立集落_有無", "無")))
    st.session_state["人身_有無"] = c5_3.selectbox("人身被害", constants.MASTER_DATA["yes_no"], index=constants.MASTER_DATA["yes_no"].index(st.session_state.get("人身_有無", "無")))
    st.session_state["物損_有無"] = c5_4.selectbox("物損被害", constants.MASTER_DATA["yes_no"], index=constants.MASTER_DATA["yes_no"].index(st.session_state.get("物損_有無", "無")))
    st.session_state["停電_有無"] = c5_5.selectbox("停電", constants.MASTER_DATA["yes_no"], index=constants.MASTER_DATA["yes_no"].index(st.session_state.get("停電_有無", "無")))

    c5_6, c5_7 = st.columns(2)
    st.session_state["迂回路内容"] = c5_6.text_input("迂回路内容", value=st.session_state.get("迂回路内容", ""))
    st.session_state["孤立集落戸数・人口"] = c5_7.text_input("孤立集落戸数・人口", value=st.session_state.get("孤立集落戸数・人口", ""))

    c5_8, c5_9 = st.columns(2)
    st.session_state["人身内容"] = c5_8.text_input("人身内容", value=st.session_state.get("人身内容", ""))
    st.session_state["物損内容"] = c5_9.text_input("物損内容", value=st.session_state.get("物損内容", ""))

    c5_10, c5_11 = st.columns(2)
    st.session_state["停電世帯数"] = c5_10.text_input("停電世帯数", value=st.session_state.get("停電世帯数", ""))
    st.session_state["マスコミ"] = c5_11.text_input("マスコミ", value=st.session_state.get("マスコミ", ""))

    st.session_state["備考_障害処理状況等"] = st.text_area("備考 (障害処理状況等)", value=st.session_state.get("備考_障害処理状況等", ""), height=80)