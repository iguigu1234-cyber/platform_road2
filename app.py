# =================================================================
# app.py - 通行規制PF2管理システム
# =================================================================
import streamlit as st
import constants, view, history_list
import api_service as api
import form_sections as fs

def run_app():
    st.set_page_config(page_title="通行規制管理 PF2", layout="wide")
    view.apply_custom_style(constants.STYLE_CONFIG)
    
    if 'records' not in st.session_state: st.session_state.records = []
    if 'drm_token' not in st.session_state: st.session_state.drm_token = None
    
    # 台帳に基づき初期値をセット
    for k, v in constants.INITIAL_VALUES.items():
        if k not in st.session_state: st.session_state[k] = v

    api_service = api.RoadAPIService()

    with st.sidebar:
        st.title("⚙️ 認証・メニュー")
        with st.expander("🔑 DRM API ログイン", expanded=(st.session_state.drm_token is None)):
            u = st.text_input("ユーザー名")
            p = st.text_input("パスワード", type="password")
            if st.button("ログイン"):
                token = api_service.drm_login(u, p)
                if token:
                    st.session_state.drm_token = token
                    st.success("DRM認証成功")
                    st.rerun()
                else: st.error("認証失敗")
        
        if st.session_state.drm_token:
            st.success("✅ DRM認証済み")
            if st.button("ログアウト"):
                st.session_state.drm_token = None
                st.rerun()

        st.divider()
        menu = st.radio("メニュー選択", ["規制入力", "一覧・出力"])

    st.title("🚧 通行規制プラットフォーム (PF2)")

    if menu == "規制入力":
        fs.render_form(api_service)
        st.divider()
        if st.button("📥 この内容で記録する", type="primary", use_container_width=True):
            # 台帳(PF2_COLUMNS)の順序でレコードを作成
            rec = {col: st.session_state.get(col, "") for col in constants.PF2_COLUMNS}
            st.session_state.records.append(rec)
            st.success("登録完了。一覧タブで確認できます。")
            
    elif menu == "一覧・出力":
        history_list.render_history()

if __name__ == "__main__":
    run_app()