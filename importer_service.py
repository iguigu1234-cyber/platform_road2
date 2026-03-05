# =================================================================
# importer_service.py - CSVインポート時の空行除外強化
# =================================================================
import json
import pandas as pd
import re
import io
import constants
import streamlit as st

class DataImporter:
    @staticmethod
    def process_file(uploaded_file):
        filename = uploaded_file.name
        try:
            if filename.endswith(('.geojson', '.json')):
                return DataImporter._process_geojson(uploaded_file)
            elif filename.endswith('.csv'):
                return DataImporter._process_csv(uploaded_file)
        except Exception as e:
            st.error(f"ファイル解析エラー: {e}")
        return []

    @staticmethod
    def _process_geojson(file):
        try:
            data = json.load(file)
        except:
            return []
        features = data.get("features", [data] if data.get("type") == "Feature" else [])
        results = []
        for f in features:
            props = f.get("properties", {})
            geom = f.get("geometry", {})
            g_type = geom.get("type")
            coords = geom.get("coordinates", [])
            rec = {col: "" for col in constants.PF2_COLUMNS}

            if g_type == "MultiLineString":
                rec["タイプ"] = "複線"
                flat = []
                for line in coords:
                    for p in line: flat.append([p[1], p[0]])
                rec["RM位置座標"] = json.dumps(flat)
            elif g_type == "LineString":
                rec["タイプ"] = "線"
                rec["RM位置座標"] = json.dumps([[p[1], p[0]] for p in coords])
            elif g_type == "Point":
                rec["タイプ"] = "点"
                if len(coords) >= 2: rec["始点緯度経度"] = f"{coords[1]}, {coords[0]}"

            if "規制内容（規制種別）" in props:
                rec.update({
                    "路線名": props.get("規制区間（路線名）", ""),
                    "道路種別": props.get("規制区間（道路種別）", ""),
                    "規制種別": props.get("規制内容（規制種別）", ""),
                    "規制理由": props.get("規制理由（事象種別）", ""),
                    "始点住所": props.get("箇所（住所等）", ""),
                    "タイトル": f"和歌山_{props.get('通し番号（規制ID）', '')}",
                    "線・面の色": "#000000", "不透明度(%)": "100", "サイズ": "5"
                })
            else:
                rec["タイトル"] = props.get("name", props.get("タイトル", ""))
                if "_color" in props: rec["線・面の色"] = props["_color"]
                if "_opacity" in props: rec["不透明度(%)"] = str(int(float(props["_opacity"]) * 100))
                if "_weight" in props: rec["サイズ"] = str(props["_weight"])
                if g_type == "Point" and "_iconUrl" in props:
                    m = re.search(r'(\d+)\.png$', str(props["_iconUrl"]))
                    if m: rec["アイコン番号"] = m.group(1)

            results.append(rec)
        return results

    @staticmethod
    def _process_csv(file):
        try:
            content = file.getvalue().decode('utf-8-sig')
            lines = content.splitlines()
        except: return []

        header_idx = -1
        for i, line in enumerate(lines):
            if any(k in line for k in ["整理番号", "整理\n番号", "報番号"]):
                header_idx = i
                break
        if header_idx == -1: header_idx = 0

        CSV_COL_DEF = {
            0: "報番号", 1: "地整番号", 2: "整備局名", 3: "県番号", 4: "県名",
            5: "市町村名", 6: "道路種別", 7: "路線名", 8: "始点住所", 9: "終点住所",
            10: "規制種別", 11: "規制理由",
            12: "tmp_s_date", 13: "tmp_s_time", 14: "規制開始_内容",
            15: "延長_Km",
            16: "tmp_c_date", 17: "tmp_c_time", 18: "規制変更_内容",
            19: "迂回路_有無", 20: "迂回路内容", 21: "孤立集落_有無", 22: "孤立集落戸数・人口",
            23: "人身_有無", 24: "人身内容", 25: "物損_有無", 26: "物損内容",
            27: "停電_有無", 28: "停電世帯数", 29: "始点緯度経度", 
            30: "マスコミ", 31: "終点緯度経度" 
        }

        try:
            df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])), header=None, encoding='utf-8')
        except: return []

        results = []
        for idx, row in df.iloc[1:].iterrows():
            if len(row) < 8: continue

            # --- [強化] 空行および無効行の判定 ---
            v_a = str(row[0]).strip().lower() # 報番号
            v_e = str(row[4]).strip().lower() # 県名
            v_h = str(row[7]).strip().lower() # 路線名

            # いずれも中身がない、または見出し行の場合はスキップ
            if v_e in ["nan", "", "none", "自動", "県名", "県　名"]: continue
            if v_h in ["nan", "", "none", "#ref!", "路線名"]: continue
            if all(v in ["nan", "", "none", "#ref!"] for v in [v_a, v_e, v_h]): continue

            rec = {col: "" for col in constants.PF2_COLUMNS}
            temp = {}
            for col_idx, pf2_key in CSV_COL_DEF.items():
                if col_idx < len(row):
                    val_raw = str(row[col_idx]).strip()
                    if val_raw.lower() not in ["nan", "none", "#ref!"] and val_raw != "":
                        if pf2_key.startswith("tmp_"): temp[pf2_key] = val_raw
                        else: rec[pf2_key] = val_raw
            
            if temp.get("tmp_s_date") or temp.get("tmp_s_time"):
                rec["規制開始_日時"] = f"{temp.get('tmp_s_date','')} {temp.get('tmp_s_time','')}".strip()
            if temp.get("tmp_c_date") or temp.get("tmp_c_time"):
                rec["規制変更_日時"] = f"{temp.get('tmp_c_date','')} {temp.get('tmp_c_time','')}".strip()
            
            if rec.get("始点緯度経度"):
                rec["タイプ"] = "点"
                rec["始点緯度経度"] = rec["始点緯度経度"].replace("　", " ").replace("，", ",")
            if rec.get("終点緯度経度"):
                rec["終点緯度経度"] = rec["終点緯度経度"].replace("　", " ").replace("，", ",")

            if not rec.get("タイトル"): rec["タイトル"] = f"{rec.get('路線名','名称未設定')}規制"
            if not rec.get("線・面の色"): rec["線・面の色"] = "#FF0000"
            if not rec.get("不透明度(%)"): rec["不透明度(%)"] = "100"
            if not rec.get("サイズ"): rec["サイズ"] = "10"
            if not rec.get("タイプ"): rec["タイプ"] = "点"
            results.append(rec)
        return results