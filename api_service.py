# =================================================================
# api_service.py - DRM & 地理院API連携（機能FIX・安定化版）
# =================================================================
import requests
import streamlit as st
import base64
import re
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
        """VBA準拠ロジック (FIXED: GetNearestLink)"""
        url = f"{self.base_url}/API/Link/GetNearestLink.php"
        params = {
            "point_x": lat,
            "point_y": lon,
            "distance_marker_kind": 1,
            "response_geodata": "geojson/object"
        }
        headers = {"TOKEN-KEY": token}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=5)
            return res.json() if res.status_code == 200 else {"error": f"DRM Error: {res.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def translate_road_attributes(self, drm_res):
        """DRMレスポンス解析 (FIXED: 日本語プロパティ名)"""
        try:
            feat = drm_res.get("geo_data", {}).get("features", [{}])[0].get("properties", {})
            return {
                "道路種別コード": str(feat.get("主路線・道路種別コード", feat.get("R_CLASS", ""))),
                "道路管理者": feat.get("管理者名", feat.get("ADMIN_NAME", "")),
                "路線番号": str(feat.get("主路線・路線番号", feat.get("R_NO", ""))),
                "路線名": feat.get("路線名.漢字名称", feat.get("R_NAME", "")),
                "路線名かな": feat.get("路線名.カナ名称", feat.get("R_NAME_K", "")),
                "交通量": str(feat.get("平日24時間交通量", feat.get("TRAFFIC_W", ""))),
                "KP": str(round(float(drm_res.get("distance_from_starting_point", 0)) / 1000.0, 3))
            }
        except:
            return None

    def calculate_extension(self):
        """延長自動算定 (|終点KP - 始点KP|)"""
        try:
            s_kp_str = st.session_state.get("始点キロポスト", "0")
            e_kp_str = st.session_state.get("終点キロポスト", "0")
            s_kp = float(re.sub(r'[^0-9.]', '', str(s_kp_str))) if s_kp_str else 0.0
            e_kp = float(re.sub(r'[^0-9.]', '', str(e_kp_str))) if e_kp_str else 0.0
            if s_kp != 0.0 and e_kp != 0.0:
                extension = abs(e_kp - s_kp)
                st.session_state["延長_Km"] = str(round(extension, 3))
        except:
            pass

    def update_info_from_apis(self, lat, lon, prefix="始点"):
        """APIから取得したデータを反映"""
        token = st.session_state.get("drm_token")
        gsi = self.fetch_address_jartic_gsi(lat, lon)
        drm_data = None
        if token:
            drm_res = self.fetch_drm_data_vba(token, lat, lon)
            if "error" not in drm_res:
                drm_data = self.translate_road_attributes(drm_res)

        if "error" not in gsi:
            st.session_state[f"{prefix}住所"] = gsi.get("title", "")
            st.session_state[f"{prefix}住所かな"] = gsi.get("titleYomi", "")
            if prefix == "始点" and "feature" in gsi:
                props = gsi["feature"]["properties"]
                pref = props.get("pref", "")
                st.session_state["県名"] = pref
                st.session_state["市町村名"] = props.get("muni", "")
                st.session_state["整備局名"] = constants.PREF_TO_BUREAU.get(pref, "")

        if drm_data:
            if prefix == "始点":
                st.session_state["道路種別"] = drm_data["道路種別コード"]
                st.session_state["道路管理者"] = drm_data["道路管理者"]
                st.session_state["路線番号"] = drm_data["路線番号"]
                st.session_state["路線名"] = drm_data["路線名"]
                st.session_state["路線名かな"] = drm_data["路線名かな"]
                st.session_state["24時間交通量_平日"] = drm_data["交通量"]
                st.session_state["始点キロポスト"] = drm_data["KP"]
            else:
                st.session_state["終点キロポスト"] = drm_data["KP"]
        
        self.calculate_extension()

    def fetch_route_coordinates(self, token, start_lat, start_lon, end_lat, end_lon, road_types="1,2,3,4,5,6,7,8,9,18,19"):
        """DRM API9準拠ロジック (FIXED: GetRootPointToPoint.php)"""
        url = f"{self.base_url}/API/Root/GetRootPointToPoint.php"
        params = {
            "road_classification": 2,
            "road_types": road_types,
            "point1_x": start_lat,
            "point1_y": start_lon,
            "point2_x": end_lat,
            "point2_y": end_lon,
            "response_geodata": "geojson/object"
        }
        headers = {"TOKEN-KEY": token}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "geo_data" in data and data["geo_data"] and "features" in data["geo_data"]:
                    all_coords = []
                    for feature in data["geo_data"]["features"]:
                        coords = feature.get("geometry", {}).get("coordinates", [])
                        for c in coords:
                            all_coords.append(f"[{c[1]},{c[0]}]")
                    unique_coords = []
                    seen = set()
                    for c in all_coords:
                        if c not in seen:
                            unique_coords.append(c)
                            seen.add(c)
                    return "[" + ",".join(unique_coords) + "]"
            return None
        except Exception as e:
            st.error(f"経路取得エラー: {e}")
            return None