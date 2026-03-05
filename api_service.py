# =================================================================
# api_service.py - DRM API 経路取得・属性変換安定化版
# =================================================================
import requests
import streamlit as st
import base64
import re
import json
import constants

class RoadAPIService:
    def __init__(self):
        self.base_url = "https://pf.drm.jp"
        self.jartic_gsi_url = "https://www.jartic-ri2maps.org/api/get-address-gsi/get-address-gsi.php"
        self.gsi_auth = base64.b64encode(b"ri2maps-api:Agf58IjA").decode("utf-8")

    def drm_login(self, user_name, password):
        url = f"{self.base_url}/API/State/Authentication"
        payload = {"user_name": user_name, "password": password}
        try:
            res = requests.post(url, data=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == 1:
                    return data.get("key")
            return None
        except:
            return None

    def fetch_address_jartic_gsi(self, lat, lon):
        headers = {"Authorization": f"Basic {self.gsi_auth}"}
        params = {"lat": lat, "lon": lon}
        try:
            res = requests.get(self.jartic_gsi_url, params=params, headers=headers, timeout=5)
            return res.json() if res.status_code == 200 else {"error": "GSI API Error"}
        except Exception as e:
            return {"error": str(e)}

    def fetch_drm_data_vba(self, token, lat, lon):
        if lat is None or lon is None: return {"error": "Invalid Coords"}
        url = f"{self.base_url}/API/Link/GetNearestLink.php"
        params = {"point_x": lat, "point_y": lon, "distance_marker_kind": 1, "response_geodata": "geojson/object"}
        headers = {"TOKEN-KEY": token}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=5)
            return res.json() if res.status_code == 200 else {"error": f"DRM Error: {res.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def translate_road_attributes(self, drm_res):
        try:
            feat_list = drm_res.get("geo_data", {}).get("features", [])
            if not feat_list: return None
            props = feat_list[0].get("properties", {})
            
            kp_val = ""
            try:
                raw_dist = drm_res.get("distance_from_starting_point")
                if raw_dist is not None: kp_val = str(round(float(raw_dist) / 1000.0, 3))
            except: kp_val = ""

            m_code = int(props.get("主路線・管理者コード", 0))
            t_code = int(props.get("主路線・道路種別コード", 0))
            rt, rm = "その他", "その他"

            if t_code == 1:
                rt = "高速道路"; rm = "NEXCO" if m_code == 1 else "国" if m_code == 4 else "その他"
            elif t_code == 2:
                rt = "都市高速道路"; rm = "都市高速" if m_code == 2 else "道路公社" if m_code == 3 else "その他"
            elif t_code == 3:
                if m_code == 4: rt, rm = "直轄国道", "国"
                elif m_code == 1: rt, rm = "有料道路", "NEXCO"
                else: rt, rm = "補助国道", "各都道府県" if m_code == 5 else "政令市"
            elif t_code in [4, 5, 6]:
                rt = "都道府県道"; rm = "道路公社" if m_code == 3 else "各都道府県" if m_code == 5 else "政令市"
            elif t_code == 7:
                rt = "市町村道"; rm = "政令市" if m_code == 6 else "市町村"
            if (m_code in [6, 7]) and (7 <= t_code <= 11): rt = "市町村道"
            
            return {
                "道路種別": rt, "道路管理者": rm, "路線番号": str(props.get("主路線・路線番号", "")),
                "路線名": props.get("路線名.漢字名称", ""), "路線名かな": props.get("路線名.カナ名称", ""),
                "交通量": str(props.get("平日24時間交通量", "")), "KP": kp_val
            }
        except: return None

    def calculate_extension(self):
        try:
            s_kp_str = st.session_state.get("始点キロポスト", "0")
            e_kp_str = st.session_state.get("終点キロポスト", "0")
            s_kp = float(re.sub(r'[^0-9.]', '', str(s_kp_str))) if s_kp_str else 0.0
            e_kp = float(re.sub(r'[^0-9.]', '', str(e_kp_str))) if e_kp_str else 0.0
            if s_kp != 0.0 and e_kp != 0.0:
                st.session_state["延長_Km"] = str(round(abs(e_kp - s_kp), 3))
        except: pass

    def update_info_from_apis(self, lat, lon, prefix="始点"):
        token = st.session_state.get("drm_token")
        gsi = self.fetch_address_jartic_gsi(lat, lon)
        drm_data = None
        if token:
            drm_res = self.fetch_drm_data_vba(token, lat, lon)
            if "error" not in drm_res: drm_data = self.translate_road_attributes(drm_res)

        if "error" not in gsi:
            st.session_state[f"{prefix}住所"] = gsi.get("title", "")
            if prefix == "始点" and "feature" in gsi:
                props = gsi["feature"].get("properties", {})
                pref = props.get("pref", "")
                st.session_state["県名"] = pref
                st.session_state["市町村名"] = props.get("muni", "")
                st.session_state["整備局名"] = constants.PREF_TO_BUREAU.get(pref, "")

        if drm_data:
            if prefix == "始点":
                for k, v in drm_data.items(): st.session_state[k] = v
                st.session_state["始点キロポスト"] = drm_data["KP"]
            else:
                st.session_state["終点キロポスト"] = drm_data["KP"]
        self.calculate_extension()

    def fetch_route_coordinates(self, token, start_lat, start_lon, end_lat, end_lon, road_types_input):
        """日本語道路種別をDRMコードに変換して経路取得"""
        # 逆マッピング
        ROAD_TYPE_MAP = {
            "高速道路": "1", "都市高速道路": "2", "直轄国道": "3", 
            "補助国道": "3", "有料道路": "3", "都道府県道": "4,5,6", 
            "市町村道": "7,8,9,10,11"
        }
        # 入力が日本語名称ならコードに変換、そうでなければデフォルト
        rt_code = ROAD_TYPE_MAP.get(road_types_input, "1,2,3,4,5,6,7,8,9,18,19")
        
        url = f"{self.base_url}/API/Root/GetRootPointToPoint.php"
        params = {
            "road_classification": 2, "road_types": rt_code,
            "point1_x": start_lat, "point1_y": start_lon,
            "point2_x": end_lat, "point2_y": end_lon,
            "response_geodata": "geojson/object"
        }
        headers = {"TOKEN-KEY": token}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "geo_data" in data and data["geo_data"] and "features" in data["geo_data"]:
                    coords = []
                    for feat in data["geo_data"]["features"]:
                        for c in feat.get("geometry", {}).get("coordinates", []):
                            coords.append([c[1], c[0]])
                    # 重複削除
                    unique = []
                    for c in coords:
                        if not unique or c != unique[-1]: unique.append(c)
                    return json.dumps(unique)
            return None
        except Exception as e:
            st.error(f"API実行エラー: {e}")
            return None