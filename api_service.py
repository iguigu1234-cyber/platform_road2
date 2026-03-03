# =================================================================
# api_service.py - API連携ロジック（安定化修正版）
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
                if data.get("status") == 1: return data.get("key")
            return None
        except: return None

    def fetch_address_jartic_gsi(self, lat, lon):
        headers = {"Authorization": f"Basic {self.gsi_auth}"}
        params = {"lat": lat, "lon": lon}
        try:
            res = requests.get(self.jartic_gsi_url, params=params, headers=headers, timeout=5)
            return res.json() if res.status_code == 200 else None
        except: return None

    def fetch_drm_data_vba(self, token, lat, lon):
        url = f"{self.base_url}/API/Link/GetNearestLink.php"
        params = {"point_x": lat, "point_y": lon, "distance_marker_kind": 1, "response_geodata": "geojson/object"}
        headers = {"TOKEN-KEY": token}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=5)
            return res.json() if res.status_code == 200 else None
        except: return None

    def calculate_extension(self):
        """延長自動算定ロジックの安定化"""
        try:
            s_kp_str = str(st.session_state.get("始点キロポスト", "0"))
            e_kp_str = str(st.session_state.get("終点キロポスト", "0"))
            s_kp = float(re.sub(r'[^0-9.]', '', s_kp_str)) if s_kp_str else 0.0
            e_kp = float(re.sub(r'[^0-9.]', '', e_kp_str)) if e_kp_str else 0.0
            if s_kp != 0.0 and e_kp != 0.0:
                st.session_state["延長_Km"] = str(round(abs(e_kp - s_kp), 3))
        except: pass

    def update_info_from_apis(self, lat, lon, prefix="始点"):
        token = st.session_state.get("drm_token")
        gsi = self.fetch_address_jartic_gsi(lat, lon)
        
        if gsi:
            st.session_state[f"{prefix}住所"] = gsi.get("title", "")
            if prefix == "始点" and "feature" in gsi:
                props = gsi["feature"].get("properties", {})
                pref = props.get("pref", "")
                st.session_state["県名"] = pref
                st.session_state["市町村名"] = props.get("muni", "")
                st.session_state["整備局名"] = constants.PREF_TO_BUREAU.get(pref, "")

        if token:
            drm = self.fetch_drm_data_vba(token, lat, lon)
            if drm and "geo_data" in drm:
                feat = drm["geo_data"]["features"][0]["properties"]
                if prefix == "始点":
                    st.session_state["道路種別"] = str(feat.get("主路線・道路種別コード", ""))
                    st.session_state["道路管理者"] = feat.get("管理者名", "")
                    st.session_state["24時間交通量_平日"] = str(feat.get("平日24時間交通量", ""))
                    st.session_state["路線番号"] = str(feat.get("主路線・路線番号", ""))
                    st.session_state["路線名"] = feat.get("路線名.漢字名称", "")
                    st.session_state["始点キロポスト"] = str(round(float(drm.get("distance_from_starting_point", 0))/1000.0, 3))
                else:
                    st.session_state["終点キロポスト"] = str(round(float(drm.get("distance_from_starting_point", 0))/1000.0, 3))
        
        self.calculate_extension()

    def fetch_route_coordinates(self, token, s_lat, s_lon, e_lat, e_lon, r_types):
        url = f"{self.base_url}/API/Root/GetRootPointToPoint.php"
        params = {"road_classification": 2, "road_types": r_types, "point1_x": s_lat, "point1_y": s_lon, "point2_x": e_lat, "point2_y": e_lon, "response_geodata": "geojson/object"}
        headers = {"TOKEN-KEY": token}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                all_coords = []
                for feat in data.get("geo_data", {}).get("features", []):
                    for c in feat.get("geometry", {}).get("coordinates", []):
                        all_coords.append([c[1], c[0]])
                unique = []
                for c in all_coords:
                    if c not in unique: unique.append(c)
                return json.dumps(unique)
            return None
        except: return None