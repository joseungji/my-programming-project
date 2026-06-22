import datetime
import json
import os
import numpy as np
import pandas as pd
import streamlit as st

# 0. Matplotlib 한글 폰트 설정 (Streamlit Cloud 대응)
#    ── pyplot보다 먼저 font_manager만 임포트하여 폰트 설정을 선행해야 함 ──
import matplotlib
import matplotlib.font_manager as fm
import shutil as _shutil

def _init_korean_font():
    """OS별 한글 폰트를 감지하여 matplotlib 전역 설정에 반영한다."""
    system = __import__("platform").system()
    mpl_rc = matplotlib.rcParams  # plt 대신 matplotlib 직접 사용

    if system == "Windows":
        mpl_rc["font.family"] = "Malgun Gothic"
        mpl_rc["axes.unicode_minus"] = False
        return "Malgun Gothic"

    if system == "Darwin":
        mpl_rc["font.family"] = "AppleGothic"
        mpl_rc["axes.unicode_minus"] = False
        return "AppleGothic"

    # ── Linux (Streamlit Cloud) ──────────────────────────────
    # 1) matplotlib 폰트 캐시 디렉토리 통째로 삭제 (가장 확실한 초기화)
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "matplotlib")
    if os.path.isdir(cache_dir):
        _shutil.rmtree(cache_dir, ignore_errors=True)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            pass

    # 2) font manager 완전 재구축
    fm._load_fontmanager(try_read_cache=False)

    # 3) 재구축된 fontManager에서 NanumGothic 계열 폰트 검색
    font_path = None
    for font_entry in fm.fontManager.ttflist:
        if "Nanum" in font_entry.name and "Gothic" in font_entry.name and "Coding" not in font_entry.name:
            font_path = font_entry.fname
            break

    # 4) 발견된 폰트가 없으면 디스크 직접 검색 fallback
    if not font_path:
        import glob as _glob
        for search in ["/usr/share/fonts/**/NanumGothic*.ttf", "/usr/share/fonts/**/nanumgothic*.ttf"]:
            try:
                matches = _glob.glob(search, recursive=True)
                if matches:
                    font_path = matches[0]
                    break
            except Exception:
                pass

    # 5) 폰트 등록 및 rcParams 설정
    if font_path and os.path.exists(font_path):
        try:
            if font_path not in [f.fname for f in fm.fontManager.ttflist]:
                fm.fontManager.addfont(font_path)
            prop = fm.FontProperties(fname=font_path)
            font_name = prop.get_name()

            mpl_rc["font.family"] = "sans-serif"
            sans = list(mpl_rc["font.sans-serif"])
            sans = [f for f in sans if f != font_name]  # 중복 제거
            mpl_rc["font.sans-serif"] = [font_name] + sans
            mpl_rc["axes.unicode_minus"] = False
            return font_name
        except Exception:
            pass

    mpl_rc["axes.unicode_minus"] = False
    return None

_korean_font_name = _init_korean_font()

# ── 폰트 초기화 완료 후 pyplot 임포트 ──
import matplotlib.pyplot as plt

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="방구석 화장대 스마트 매니저", page_icon="💄", layout="wide"
)

st.markdown(
    """
    <div style='
        display: inline-block;
        padding: 20px 50px;
        margin: 0 auto 10px auto;
        border-radius: 100px;
        background-color: #fff;
        background-image: radial-gradient(circle, #f0d0d8 1px, transparent 1px);
        background-size: 12px 12px;
        border: 4px dashed #e8a0b4;
        outline: 3px dotted #e8a0b4;
        outline-offset: 3px;
        box-shadow: 0 4px 15px rgba(200, 150, 150, 0.2);
        text-align: center;
    '>
        <h1 style='font-size: 2.8rem; margin: 0; color: #4A2025;'>💄 방구석 화장대 스마트 매니저</h1>
    </div>
    """,
    unsafe_allow_html=True,
)
# 과제 정보 (오른쪽 상단)
st.markdown(
    "<p style='text-align: right; font-size: 0.85rem; color: #000000; margin: 0; padding: 0;'>"
    "비즈니스프로그래밍1 과제<br>C531225 조승지"
    "</p>",
    unsafe_allow_html=True,
)

# 테마 색상 세션 초기화
if "theme_color" not in st.session_state:
    st.session_state.theme_color = "#FFD1DC"  # 기본 파스텔 핑크

theme_colors = {
    "🌸 핑크": "#FFD1DC",
    "🌿 연두": "#D1F2D1",
    "☁️ 하늘": "#D1E8FF",
    "⭐ 노랑": "#FFF5D1",
}

# 테마별 글자색 및 강조색 정의
theme_text_colors = {
    "#FFD1DC": "#4A2025",
    "#D1F2D1": "#1A3D1A",
    "#D1E8FF": "#1A2D4A",
    "#FFF5D1": "#4A3D1A",
}
current_theme = st.session_state.theme_color
text_color = theme_text_colors.get(current_theme, "#333333")

# 더 연한 파스텔톤 배경색 (입력창, 선택지 등)
light_theme_colors = {
    "#FFD1DC": "#FFE8ED",
    "#D1F2D1": "#E8F8E8",
    "#D1E8FF": "#E8F3FF",
    "#FFF5D1": "#FFFAE8",
}
light_bg = light_theme_colors.get(current_theme, "#FFFFFF")

# CSS 배경 및 글자 스타일 적용
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {current_theme};
    }}
    .stMarkdown, .stText, p, span, label, div {{
        color: {text_color} !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {text_color} !important;
    }}
    .stExpander summary {{
        color: {text_color} !important;
    }}
    .stDataFrame {{
        color: #333 !important;
    }}
    /* 탭 버튼 스타일: 흰색 배경 + 검정 글자 + 굵은 테두리 */
    .stTabs [data-baseweb="tab"] {{
        background-color: white !important;
        color: #222 !important;
        border: 2px solid #ccc !important;
        border-bottom: none !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 10px 20px !important;
        margin-right: 4px !important;
        font-weight: 600 !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        border-color: #999 !important;
        background-color: #fdfdfd !important;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background-color: white !important;
        color: #111 !important;
        border-width: 3px !important;
        border-color: #888 !important;
        border-bottom: 3px solid white !important;
        font-weight: 700 !important;
    }}
    /* 탭 패널 아래 테두리 */
    .stTabs [role="tablist"] {{
        border-bottom: 3px solid #ccc !important;
    }}
    /* 모든 버튼 스타일: 흰색 배경 + 검정 글자 + 굵은 테두리 */
    .stButton > button {{
        background-color: white !important;
        color: #222 !important;
        border: 2px solid #ccc !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}
    .stButton > button:hover {{
        border-color: #999 !important;
        background-color: #f5f5f5 !important;
    }}
    .stButton > button[kind="primary"] {{
        background-color: white !important;
        color: #222 !important;
        border: 2px solid #888 !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        border-color: #555 !important;
        background-color: #f0f0f0 !important;
    }}
    /* 폼 제출 버튼도 동일하게 */
    .stFormSubmitButton > button {{
        background-color: white !important;
        color: #222 !important;
        border: 2px solid #888 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }}
    .stFormSubmitButton > button:hover {{
        border-color: #555 !important;
        background-color: #f0f0f0 !important;
    }}
    /* 입력 필드 스타일: 흰색 배경 + 검정 글자 */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
        background-color: white !important;
        color: #000000 !important;
        border: 2px solid #ccc !important;
        border-radius: 8px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus, .stTextArea textarea:focus {{
        border-color: #888 !important;
    }}
    /* select 박스도 흰색 배경 */
    .stSelectbox div[data-baseweb="select"] > div {{
        background-color: white !important;
        color: #000000 !important;
        border: 2px solid #ccc !important;
        border-radius: 8px !important;
    }}
    .stSelectbox div[data-baseweb="select"] span {{
        color: #000000 !important;
    }}
    /* multiselect 입력 */
    .stMultiSelect div[data-baseweb="select"] > div {{
        background-color: white !important;
    }}
    .stMultiSelect div[data-baseweb="input"] {{
        background-color: white !important;
    }}
    .stMultiSelect input {{
        background-color: white !important;
        color: #000000 !important;
    }}
    /* 클릭했을 때 나오는 선택지들(팝오버/리스트박스) - 더욱 강력한 선택자 사용 */
    li[role="option"], ul[role="listbox"], div[data-baseweb="popover"] * {{
        background-color: white !important;
        color: #000000 !important;
    }}
    li[role="option"]:hover, li[role="option"][aria-selected="true"] {{
        background-color: white !important;
        color: #000000 !important;
    }}
    /* 폼 내부 배경 */
    [data-testid="stForm"] {{
        background-color: white !important;
        border-radius: 12px !important;
        padding: 16px !important;
        border: 2px solid #ccc !important;
    }}
    /* 데이터프레임 헤더 배경 */
    .stDataFrame thead th {{
        background-color: white !important;
        color: #000000 !important;
    }}
    .stDataFrame tbody td {{
        background-color: white !important;
        color: #000000 !important;
    }}
    /* expander 내부 배경 */
    .stExpander > div[data-testid="stExpanderDetails"] {{
        background-color: white !important;
        border-radius: 0 0 10px 10px !important;
        padding: 12px !important;
        border: 2px solid #ccc !important;
        border-top: none !important;
    }}
    /* info/success/warning 박스 배경 */
    .stAlert {{
        background-color: white !important;
        border: 2px solid #ccc !important;
        border-radius: 8px !important;
        color: #000000 !important;
    }}
    .stAlert p {{
        color: #000000 !important;
    }}
    /* 캡션 텍스트 */
    .stCaption {{
        color: #555 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# 배경음악 재생 (플레이리스트 - 순차 재생)
import streamlit.components.v1 as components

# static/assets 폴더 절대 경로 (Streamlit Cloud 호환)
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "assets")
playlist_data = []  # [(파일명, 파일 URL), ...]
if os.path.exists(assets_dir):
    try:
        mp3_files = sorted([f for f in os.listdir(assets_dir) if f.lower().endswith(".mp3")])
        for mp3_file in mp3_files:
            # Streamlit의 정적 파일 서빙 URL 형식 사용
            file_url = f"/app/static/assets/{mp3_file}"
            playlist_data.append((mp3_file, file_url))
    except Exception:
        pass  # MP3 로딩 실패 시 무시하고 계속 진행

# 테마 선택 버튼들 (BGM 컨트롤러 위에 표시)
theme_col1, theme_col2, theme_col3, theme_col4, theme_col5 = st.columns([1, 1, 1, 1, 4])
with theme_col1:
    if st.button("🌸 핑크", key="theme_pink", use_container_width=True):
        st.session_state.theme_color = theme_colors["🌸 핑크"]
        st.rerun()
with theme_col2:
    if st.button("🌿 연두", key="theme_green", use_container_width=True):
        st.session_state.theme_color = theme_colors["🌿 연두"]
        st.rerun()
with theme_col3:
    if st.button("☁️ 하늘", key="theme_sky", use_container_width=True):
        st.session_state.theme_color = theme_colors["☁️ 하늘"]
        st.rerun()
with theme_col4:
    if st.button("⭐ 노랑", key="theme_yellow", use_container_width=True):
        st.session_state.theme_color = theme_colors["⭐ 노랑"]
        st.rerun()

if playlist_data:
    # JavaScript 플레이리스트 생성
    js_playlist = ", ".join([f'"{name}"' for name, _ in playlist_data])
    js_sources = "\n".join(
        [f'<source src="{url}" data-name="{name}" type="audio/mpeg">' for name, url in playlist_data]
    )

    components.html(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            .bgm-container {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 8px 14px;
                background: #f8f9fa;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                font-family: sans-serif;
                max-width: 550px;
            }}
            .bgm-icon {{
                font-size: 24px;
                cursor: pointer;
                user-select: none;
                transition: transform 0.15s;
            }}
            .bgm-icon:hover {{
                transform: scale(1.15);
            }}
            .bgm-icon.playing {{
                animation: pulse 1.2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ transform: scale(1); }}
                50% {{ transform: scale(1.25); }}
            }}
            .bgm-vol {{
                width: 80px;
                accent-color: #ff6b6b;
                cursor: pointer;
            }}
            .bgm-btn {{
                padding: 5px 10px;
                border: none;
                border-radius: 8px;
                background: #ff6b6b;
                color: white;
                font-size: 13px;
                cursor: pointer;
                transition: background 0.2s;
                white-space: nowrap;
            }}
            .bgm-btn:hover {{
                background: #e55a5a;
            }}
            .bgm-btn.paused {{
                background: #6c757d;
            }}
            .bgm-btn.paused:hover {{
                background: #5a6268;
            }}
            .bgm-info {{
                font-size: 12px;
                color: #555;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 130px;
            }}
        </style>
        </head>
        <body style="margin:0; overflow:hidden;">
        <div class="bgm-container">
            <span class="bgm-icon playing" id="icon" title="배경음악 재생/일시정지">🎵</span>
            <span class="bgm-info" id="trackInfo" title="현재 트랙"></span>
            <span style="font-size:13px; color:#555; min-width:22px; text-align:center;" id="volLabel">35%</span>
            <input type="range" class="bgm-vol" id="vol" min="0" max="100" value="35" title="음량">
            <button class="bgm-btn" id="prevBtn" title="이전 곡">⏮</button>
            <button class="bgm-btn" id="playBtn" title="재생/일시정지">⏸</button>
            <button class="bgm-btn" id="nextBtn" title="다음 곡">⏭</button>
        </div>
        <audio id="bgm">
            {js_sources}
        </audio>
        <script>
            const audio = document.getElementById('bgm');
            const icon = document.getElementById('icon');
            const vol = document.getElementById('vol');
            const volLabel = document.getElementById('volLabel');
            const playBtn = document.getElementById('playBtn');
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            const trackInfo = document.getElementById('trackInfo');
            const playlist = [{js_playlist}];
            let currentTrack = 0;

            // 트랙 이름 단축 표시
            function shortName(name) {{
                // 확장자 제거 후 25자로 자르기
                let n = name.replace(/\\.mp3$/i, '');
                if (n.length > 25) n = n.substring(0, 22) + '...';
                return n;
            }}

            function updateTrackInfo() {{
                trackInfo.textContent = '🎶 ' + shortName(playlist[currentTrack]);
            }}

            function loadTrack(index) {{
                // source 중 해당 인덱스만 활성화
                const sources = audio.querySelectorAll('source');
                sources.forEach((src, i) => {{
                    if (i === index) {{
                        src.setAttribute('data-active', 'true');
                    }} else {{
                        src.removeAttribute('data-active');
                    }}
                }});
                // 현재 source src를 audio.src에 직접 설정
                const targetSrc = sources[index].getAttribute('src');
                audio.src = targetSrc;
                audio.load();
                currentTrack = index;
                updateTrackInfo();
            }}

            // 초기 로드
            loadTrack(0);
            audio.volume = 0.35;

            // 곡 종료 시 다음 곡 자동 재생
            audio.addEventListener('ended', () => {{
                currentTrack = (currentTrack + 1) % playlist.length;
                loadTrack(currentTrack);
                audio.play().catch(() => {{}});
            }});

            // 자동 재생 시도
            function tryAutoplay() {{
                audio.play().then(() => {{
                    icon.classList.add('playing');
                    playBtn.textContent = '⏸';
                }}).catch(() => {{
                    icon.classList.remove('playing');
                    playBtn.textContent = '▶';
                }});
            }}
            tryAutoplay();

            // 재생/일시정지 토글
            function togglePlay() {{
                if (audio.paused) {{
                    audio.play().then(() => {{
                        icon.classList.add('playing');
                        playBtn.textContent = '⏸';
                    }});
                }} else {{
                    audio.pause();
                    icon.classList.remove('playing');
                    playBtn.textContent = '▶';
                }}
            }}
            icon.addEventListener('click', togglePlay);
            playBtn.addEventListener('click', togglePlay);

            // 이전/다음 곡
            prevBtn.addEventListener('click', () => {{
                currentTrack = (currentTrack - 1 + playlist.length) % playlist.length;
                loadTrack(currentTrack);
                audio.play().then(() => {{
                    icon.classList.add('playing');
                    playBtn.textContent = '⏸';
                }});
            }});
            nextBtn.addEventListener('click', () => {{
                currentTrack = (currentTrack + 1) % playlist.length;
                loadTrack(currentTrack);
                audio.play().then(() => {{
                    icon.classList.add('playing');
                    playBtn.textContent = '⏸';
                }});
            }});

            // 볼륨 조절
            vol.addEventListener('input', () => {{
                audio.volume = vol.value / 100;
                volLabel.textContent = vol.value + '%';
            }});
        </script>
        </body>
        </html>
        """,
        height=62,
    )

# 입력 필드 한글 기본 입력 설정
st.markdown(
    """
    <style>
    input {
        ime-mode: active;
    }
    </style>
    <script>
    // 모든 input에 한글 입력 모드 및 autocapitalize 방지 설정
    const observer = new MutationObserver(() => {
        document.querySelectorAll('input[type="text"], textarea').forEach(el => {
            el.setAttribute('lang', 'ko');
            el.setAttribute('autocapitalize', 'off');
            el.setAttribute('autocomplete', 'off');
            el.style.imeMode = 'active';
        });
        // body에도 lang=ko 설정
        document.body.setAttribute('lang', 'ko');
        document.documentElement.setAttribute('lang', 'ko');
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // 초기 실행
    document.body.setAttribute('lang', 'ko');
    document.documentElement.setAttribute('lang', 'ko');
    </script>
    """,
    unsafe_allow_html=True,
)

# 2. 영구 저장 파일 경로
DATA_FILE = "cosmetics_data.json"


def load_data():
    """JSON 파일에서 데이터를 불러온다. 파일이 없으면 샘플 데이터를 생성한다."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
        df = pd.DataFrame(records)
        # 날짜 컬럼 복원
        df["구매일"] = pd.to_datetime(df["구매일"])
        df["유통기한날짜"] = pd.to_datetime(df["유통기한날짜"])
        return df

    # 파일 없으면 샘플 데이터 생성 후 저장
    sample = pd.DataFrame(
        [
            {
                "제품명": "A사 촉촉 쿠션",
                "카테고리": "베이스",
                "구매일": "2026-01-10",
                "가격": 35000,
                "유통기한날짜": "2026-07-10",
                "폐기여부": False,
            },
            {
                "제품명": "B사 벨벳 틴트",
                "카테고리": "립",
                "구매일": "2025-11-15",
                "가격": 18000,
                "유통기한날짜": "2026-05-15",
                "폐기여부": False,
            },
            {
                "제품명": "C사 데일리 팔레트",
                "카테고리": "아이",
                "구매일": "2025-03-20",
                "가격": 45000,
                "유통기한날짜": "2027-03-20",
                "폐기여부": False,
            },
            {
                "제품명": "D사 수분 크림",
                "카테고리": "스킨케어",
                "구매일": "2026-04-01",
                "가격": 38000,
                "유통기한날짜": "2026-08-15",
                "폐기여부": False,
            },
            {
                "제품명": "E사 매트 립스틱",
                "카테고리": "립",
                "구매일": "2025-12-25",
                "가격": 22000,
                "유통기한날짜": "2026-03-01",
                "폐기여부": False,
            },
        ]
    )
    save_data(sample)
    return sample


def save_data(df):
    """DataFrame을 JSON 파일로 저장한다."""
    records = df.to_dict(orient="records")
    # Timestamp → 문자열 변환
    for r in records:
        for key in ("구매일", "유통기한날짜"):
            val = r.get(key)
            if isinstance(val, pd.Timestamp):
                r[key] = val.strftime("%Y-%m-%d")
            elif pd.isna(val):
                r[key] = None
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


# 세션 상태에 데이터 로드 (초기화되어도 파일에서 복원)
if "cosmetics_df" not in st.session_state:
    st.session_state.cosmetics_df = load_data()

# 기존 세션에 폐기여부 컬럼이 없을 경우를 대비한 방어 코드
if "폐기여부" not in st.session_state.cosmetics_df.columns:
    st.session_state.cosmetics_df["폐기여부"] = False

# 전체 데이터 (지출 분석용 — 폐기여부 무관)
df_all = st.session_state.cosmetics_df.copy()
df_all["구매일"] = pd.to_datetime(df_all["구매일"])
df_all["유통기한날짜"] = pd.to_datetime(df_all["유통기한날짜"])
df_all["구매년월"] = df_all["구매일"].dt.to_period("M")

# 보유중인 제품만 필터링 (Tab 2, Tab 3 용)
df = df_all[df_all["폐기여부"] == False].copy()

today = pd.Timestamp(datetime.date.today())
df["남은일수"] = (df["유통기한날짜"] - today).dt.days

# ----------------------------------------------------------------
# ✨ 화면을 4개의 탭(창)으로 쪼개기
# ----------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📝 화장품 등록",
        "⚠️ 유통기한 경고방",
        "🔍 카테고리별 보관함",
        "📊 월간 지출 분석",
    ]
)

# ==========================================
# [첫번째 란] 입력란
# ==========================================
with tab1:
    st.subheader("📝 새로운 화장품 추가")
    st.write("새로 구매한 화장품 정보를 직접 정확하게 입력해 주세요.")

    with st.form(key="register_form_tab", clear_on_submit=True):
        col_left, col_right = st.columns(2)

        with col_left:
            new_name = st.text_input("제품명", placeholder="예: 무드 마스카라")
            new_category = st.selectbox(
                "제품 유형 (카테고리)", ["립", "아이", "베이스", "스킨케어", "기타"]
            )
            new_price = st.number_input(
                "구매 가격 (원)", min_value=0, value=None, step=1000, placeholder="가격을 입력하세요"
            )

        with col_right:
            # 년도와 월만 입력받음 (일은 입력하지 않음) — 기억안남 옵션 추가
            col_yr, col_mo = st.columns(2)
            with col_yr:
                year_options = ["기억안남"] + list(range(datetime.date.today().year, 2019, -1))
                new_purchase_year = st.selectbox(
                    "구매 년도",
                    year_options,
                    index=1,  # 기본값: 올해 (인덱스 1)
                )
            with col_mo:
                month_options = ["기억안남"] + list(range(1, 13))
                new_purchase_month = st.selectbox(
                    "구매 월",
                    month_options,
                    index=datetime.date.today().month,  # 기본값: 이번 달
                )
            # 구매일 처리: 기억안남이면 NaT, 아니면 해당 년월의 1일로 저장
            if new_purchase_year == "기억안남" or new_purchase_month == "기억안남":
                new_purchase_date = pd.NaT
            else:
                new_purchase_date = pd.Timestamp(datetime.date(new_purchase_year, new_purchase_month, 1))
            new_expiry_str = st.text_input(
                "유통기한 만료일 (숫자 6자리)",
                placeholder="예: 270320 → 2027년 3월 20일",
                help="년도2+월2+일2 = 총 6자리 숫자만 입력하세요. (예: 270320) 빈칸이면 알 수 없음 처리됩니다.",
            )

        submit_button = st.form_submit_button(label="내 화장대에 추가하기 ➕")

        if submit_button:
            if new_name:
                # 유통기한 숫자 6자리 파싱 (YYMMDD)
                new_expiry_date = pd.NaT
                if new_expiry_str.strip():
                    try:
                        cleaned = new_expiry_str.strip().replace(" ", "").replace("/", "").replace("-", "")
                        if len(cleaned) != 6 or not cleaned.isdigit():
                            raise ValueError
                        yy = int(cleaned[0:2])
                        mm = int(cleaned[2:4])
                        dd = int(cleaned[4:6])
                        # 두 자리 연도를 네 자리로 변환 (50 이상 → 1900년대, 50 미만 → 2000년대)
                        if yy >= 50:
                            full_year = 1900 + yy
                        else:
                            full_year = 2000 + yy
                        new_expiry_date = pd.Timestamp(datetime.date(full_year, mm, dd))
                    except:
                        st.error(f"⚠️ 유통기한 '{new_expiry_str}' 형식이 올바르지 않습니다. 숫자 6자리(YYMMDD)로 입력해 주세요. (예: 270320)")
                        st.stop()
                new_data = {
                    "제품명": new_name,
                    "카테고리": new_category,
                    "구매일": new_purchase_date,
                    "가격": new_price,
                    "유통기한날짜": new_expiry_date,
                    "폐기여부": False,
                }
                st.session_state.cosmetics_df = pd.concat(
                    [
                        st.session_state.cosmetics_df,
                        pd.DataFrame([new_data]),
                    ],
                    ignore_index=True,
                )
                save_data(st.session_state.cosmetics_df)
                st.success(f"✅ '{new_name}'이(가) 정상적으로 등록되었습니다! 탭을 이동해 확인하세요.")
                st.rerun()
            else:
                st.error("제품명을 입력해 주세요.")

# ==========================================
# [두번째 란] 유통기한 임박 및 만료 제품 분리 표 + 폐기 처리
# ==========================================
with tab2:
    st.subheader("🚨 유통기한 집중 관리실")

    # 1. 만료 임박 제품 (0일 이상 ~ 90일 이하 남은 제품)
    st.write("### ⚠️ 유통기한 만료 임박 제품 (3개월 이내)")
    imminent_df = df[(df["남은일수"] >= 0) & (df["남은일수"] <= 90)].copy()
    if not imminent_df.empty:
        imminent_df["디데이"] = imminent_df["남은일수"].apply(lambda x: f"D-{int(x)}" if pd.notna(x) else "알 수 없음")
        imminent_df["유통기한 만료일"] = imminent_df["유통기한날짜"].apply(lambda x: x.date() if pd.notna(x) else "알 수 없음")
        st.dataframe(
            imminent_df.sort_values(by="남은일수")[["제품명", "카테고리", "유통기한 만료일", "디데이"]],
            use_container_width=True,
        )
    else:
        st.success("3개월 이내에 만료되는 안전한 상태입니다! 🎉")

    st.markdown("---")

    # 2. 만료 제품 (남은일수가 음수인 제품)
    st.write("### 💀 유통기한 만료 제품")
    expired_df = df[df["남은일수"] < 0].copy()
    if not expired_df.empty:
        expired_df["지난 일수"] = expired_df["남은일수"].apply(
            lambda x: f"{abs(int(x))}일 지남" if pd.notna(x) else "알 수 없음"
        )
        expired_df["유통기한 만료일"] = expired_df["유통기한날짜"].apply(lambda x: x.date() if pd.notna(x) else "알 수 없음")
        st.dataframe(
            expired_df.sort_values(by="남은일수")[["제품명", "카테고리", "유통기한 만료일", "지난 일수"]],
            use_container_width=True,
        )
    else:
        st.info("유통기한이 지난 화장품이 없습니다. 깨끗한 화장대네요! 👍")

    st.markdown("---")

    # 3. 화장대 폐기 (버리기) 섹션
    st.write("### 🗑️ 화장대 정리 — 폐기 처리")
    st.caption("버린 화장품을 선택하면 Tab 2, Tab 3에서 사라집니다. (Tab 4 지출 내역에는 그대로 남음)")

    # 보유중인 전체 제품을 체크박스로 표시
    active_df = df.copy()
    active_df["표시명"] = active_df.apply(
        lambda row: f"{row['제품명']} ({row['카테고리']} | 유통기한: {row['유통기한날짜'].strftime('%Y-%m-%d') if pd.notna(row['유통기한날짜']) else '알 수 없음'})",
        axis=1,
    )

    if not active_df.empty:
        to_dispose = st.multiselect(
            "폐기할 제품을 선택하세요 (복수 선택 가능)",
            options=active_df["제품명"].tolist(),
            placeholder="버릴 제품을 골라주세요...",
        )

        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if st.button("🗑️ 선택 제품 폐기하기", type="primary", disabled=len(to_dispose) == 0):
                # session_state에서 해당 제품들의 폐기여부를 True로 변경
                mask = st.session_state.cosmetics_df["제품명"].isin(to_dispose)
                st.session_state.cosmetics_df.loc[mask, "폐기여부"] = True
                save_data(st.session_state.cosmetics_df)
                st.success(f"✅ 총 {len(to_dispose)}개 제품을 폐기 처리했습니다.")
                st.rerun()
        with col_btn2:
            disposed_count = st.session_state.cosmetics_df["폐기여부"].sum()
            if disposed_count > 0:
                st.info(f"📦 현재까지 총 {disposed_count}개의 제품을 폐기하셨습니다.")
    else:
        st.info("보유 중인 화장품이 없습니다.")

    # 4. 영구 삭제 섹션 — 모든 제품을 데이터에서 바로 완전히 제거
    st.markdown("---")
    st.write("### 💣 영구 삭제 (데이터에서 완전 제거)")
    st.caption("⚠️ 모든 제품(폐기 여부 무관)을 JSON 데이터에서 바로 완전히 삭제합니다. 이 작업은 되돌릴 수 없습니다.")

    all_for_delete_df = df_all.copy()
    if not all_for_delete_df.empty:
        all_for_delete_df["유통기한만료일"] = all_for_delete_df["유통기한날짜"].apply(
            lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "알 수 없음"
        )
        all_for_delete_df["구매일자"] = all_for_delete_df["구매일"].apply(
            lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "알 수 없음"
        )
        all_for_delete_df["상태"] = all_for_delete_df["폐기여부"].apply(lambda x: "🗑️ 폐기됨" if x else "✅ 보유중")
        all_for_delete_df["표시명"] = all_for_delete_df.apply(
            lambda row: f"[{row['상태']}] {row['제품명']} ({row['카테고리']} | 구매: {row['구매일자']} | 유통기한: {row['유통기한만료일']})",
            axis=1,
        )

        # 전체 제품 목록 표시
        st.dataframe(
            all_for_delete_df[["상태", "제품명", "카테고리", "구매일자", "유통기한만료일", "가격"]],
            use_container_width=True,
        )

        # 표시명과 제품명을 매핑한 dict 생성
        display_to_name = dict(zip(all_for_delete_df["표시명"], all_for_delete_df["제품명"]))

        selected_displays = st.multiselect(
            "영구 삭제할 제품을 선택하세요 (복수 선택 가능)",
            options=all_for_delete_df["표시명"].tolist(),
            placeholder="완전히 삭제할 제품을 골라주세요...",
            key="perm_delete_select",
        )

        to_delete_names = [display_to_name[d] for d in selected_displays]

        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            if st.button("💣 선택 제품 영구 삭제", type="primary", disabled=len(to_delete_names) == 0, key="perm_delete_btn"):
                # 선택된 제품을 DataFrame에서 완전히 제거
                mask = st.session_state.cosmetics_df["제품명"].isin(to_delete_names)
                st.session_state.cosmetics_df = st.session_state.cosmetics_df[~mask].reset_index(drop=True)
                save_data(st.session_state.cosmetics_df)
                st.success(f"✅ 총 {len(to_delete_names)}개 제품을 데이터에서 영구 삭제했습니다.")
                st.rerun()
        with col_del2:
            total_count = len(all_for_delete_df)
            disposed_count = len(all_for_delete_df[all_for_delete_df["폐기여부"] == True])
            st.info(f"📦 전체 {total_count}개 제품 중 {disposed_count}개가 폐기 상태입니다.")
    else:
        st.info("🗑️ 등록된 제품이 없습니다. 데이터가 깨끗합니다!")

# ==========================================
# [세번째 란] 카테고리별 세부 분리 보기
# ==========================================
with tab3:
    st.subheader("🔍 카테고리별 보관함")
    st.write("선택한 제품 유형별로 디데이가 얼마 남지 않은 순서대로 정렬됩니다.")

    categories = ["립", "아이", "베이스", "스킨케어", "기타"]
    for cat in categories:
        cat_df = df[df["카테고리"] == cat].copy()
        item_count = len(cat_df)
        # 각 카테고리별 expander — 클릭하면 표가 튀어나오는 형식
        with st.expander(f"💄 {cat}  ({item_count}개)", expanded=False):
            if not cat_df.empty:
                cat_df["유통기한만료일"] = cat_df["유통기한날짜"].apply(lambda x: x.date() if pd.notna(x) else "알 수 없음")
                cat_df["디데이"] = cat_df["남은일수"].apply(
                    lambda x: (f"D-{int(x)}" if x >= 0 else f"만료 ({abs(int(x))}일 지남)") if pd.notna(x) else "알 수 없음"
                )
                # 디데이가 얼마 안 남은 제품부터 나열
                sorted_cat_df = cat_df.sort_values(by="남은일수")
                st.dataframe(
                    sorted_cat_df[["제품명", "유통기한만료일", "디데이"]],
                    use_container_width=True,
                )
            else:
                st.info(f"'{cat}' 카테고리에 등록된 제품이 없습니다.")

# ==========================================
# [네번째 란] 달 단위 지출 분석 그래프 (폐기 제품도 포함)
# ==========================================
with tab4:
    st.subheader("📊 달 단위 지출 통계 및 과소비 진단")
    st.write("매달 화장품에 소비한 총액 흐름을 파악하여 충동구매를 방지합니다.")
    st.caption("※ 폐기한 제품의 구매 기록도 모두 포함된 통계입니다.")

    # df_all 사용 — 폐기여부와 무관하게 모든 구매 이력 포함
    # 구매일을 알 수 없는 제품은 따로 집계에서 제외 (NaT 처리)
    df_expense = df_all[df_all["구매일"].notna()].copy()
    df_expense["구매년도"] = df_expense["구매일"].dt.year.astype(int)
    unknown_count = df_all["구매일"].isna().sum()

    if unknown_count > 0:
        st.info(f"ℹ️ 구매일을 알 수 없는 제품 {unknown_count}개는 아래 그래프와 통계에서 제외되었습니다.")

    # 연도 선택 (기본값: 가장 최근 연도 = 올해)
    available_years = sorted(df_expense["구매년도"].unique(), reverse=True)

    if len(available_years) > 0:
        selected_year = st.selectbox(
            "📅 조회할 연도를 선택하세요",
            options=available_years,
            index=0,  # 기본값: 가장 최근 연도
        )

        year_df = df_expense[df_expense["구매년도"] == selected_year]
        monthly_expense = year_df.groupby("구매년월")["가격"].sum()

        if not monthly_expense.empty:
            # 인덱스를 시각화하기 좋게 텍스트(예: 2026-03)로 변환
            monthly_expense.index = monthly_expense.index.astype(str)

            col_table, col_chart = st.columns([1, 1.5])

            with col_table:
                st.write(f"📅 **{selected_year}년 월별 지출 요약**")
                expense_display = pd.DataFrame(monthly_expense).rename(
                    columns={"가격": "총 지출액"}
                )
                st.dataframe(expense_display.style.format("{:,.0f}원"))

                # 과소비 진단
                max_month = monthly_expense.idxmax()
                st.warning(
                    f"⚠️ **지름신 경고:** {selected_year}년에 가장 소비가 많았던 달은 **{max_month}** 이며, 총 **{monthly_expense[max_month]:,}원**을 지출하셨습니다!"
                )

            with col_chart:
                # Matplotlib 꺾은선/막대 혼합으로 달 단위 양상 시각화
                # (폰트는 파일 상단에서 이미 초기화됨)
                fig, ax = plt.subplots(figsize=(6, 3.8))

                monthly_expense.plot(
                    kind="line", marker="o", color="#ff6b6b", linewidth=2, ax=ax
                )
                monthly_expense.plot(kind="bar", color="#ffe3e3", alpha=0.7, ax=ax)

                ax.set_title(f"{selected_year}년 월별 화장품 지출 추이", fontsize=11, fontweight="bold")
                ax.set_ylabel("지출 금액 (원)", fontsize=9)
                ax.set_xlabel("구매 년월", fontsize=9)
                plt.xticks(rotation=45)
                plt.tight_layout()

                st.pyplot(fig)
        else:
            st.info(f"{selected_year}년에는 지출 내역이 없습니다.")
    else:
        st.info("지출 내역이 없습니다.")

    # 데이터 관리 섹션 — 카테고리별 실시간 수정 편집기
    st.markdown("---")
    with st.expander("✏️ 데이터 관리 — 등록 기록 수정", expanded=False):
        st.info("💡 각 카테고리별로 제품을 확인하고 셀을 직접 클릭하여 값을 수정할 수 있습니다. 수정 즉시 자동 저장됩니다.")

        # column_config로 컬럼별 편집 타입 지정 (공통)
        editor_cols = ["제품명", "카테고리", "구매일", "가격", "유통기한날짜", "폐기여부"]

        column_config = {
            "제품명": st.column_config.TextColumn("제품명", help="제품명을 수정하세요"),
            "카테고리": st.column_config.SelectboxColumn(
                "카테고리",
                options=["립", "아이", "베이스", "스킨케어", "기타"],
                help="카테고리를 선택하세요",
            ),
            "구매일": st.column_config.TextColumn(
                "구매일 (YYYY-MM-DD)",
                help="구매일 입력 (예: 2026-01-15). 모르면 빈칸으로 두세요.",
            ),
            "가격": st.column_config.NumberColumn("가격 (원)", min_value=0, step=1000, format="%d원"),
            "유통기한날짜": st.column_config.TextColumn(
                "유통기한 (YYYY-MM-DD)",
                help="유통기한 입력 (예: 2027-03-20)",
            ),
            "폐기여부": st.column_config.CheckboxColumn("폐기여부", help="체크하면 폐기 처리됩니다"),
        }

        # 비교를 위한 변환 함수
        def make_comparable(df):
            """DataFrame을 비교 가능한 dict 리스트로 변환 (NaT → None)"""
            records = df.to_dict(orient="records")
            for r in records:
                for key in ("구매일", "유통기한날짜"):
                    val = r.get(key)
                    if isinstance(val, pd.Timestamp):
                        r[key] = val.strftime("%Y-%m-%d")
                    elif pd.isna(val):
                        r[key] = None
            return records

        # 변경 감지 플래그
        data_changed = False
        all_edited_records = []

        categories = ["립", "아이", "베이스", "스킨케어", "기타"]
        for cat in categories:
            # 해당 카테고리의 제품만 필터링
            cat_products = st.session_state.cosmetics_df[st.session_state.cosmetics_df["카테고리"] == cat].copy()

            with st.expander(f"💄 {cat}  ({len(cat_products)}개)", expanded=False):
                if not cat_products.empty:
                    # 날짜 컬럼을 문자열로 변환
                    cat_products["구매일"] = cat_products["구매일"].apply(
                        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
                    )
                    cat_products["유통기한날짜"] = cat_products["유통기한날짜"].apply(
                        lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
                    )
                    cat_editor = cat_products[editor_cols]

                    edited_cat = st.data_editor(
                        cat_editor,
                        column_config=column_config,
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True,
                        key=f"editor_{cat}",
                    )

                    # 편집된 카테고리 데이터 파싱
                    for _, row in edited_cat.iterrows():
                        record = row.to_dict()
                        raw_purchase = str(record["구매일"]).strip()
                        if raw_purchase == "" or raw_purchase == "NaT":
                            record["구매일"] = pd.NaT
                        else:
                            try:
                                record["구매일"] = pd.Timestamp(raw_purchase)
                            except:
                                record["구매일"] = pd.NaT
                        raw_expiry = str(record["유통기한날짜"]).strip()
                        if raw_expiry == "" or raw_expiry == "NaT":
                            record["유통기한날짜"] = pd.NaT
                        else:
                            try:
                                record["유통기한날짜"] = pd.Timestamp(raw_expiry)
                            except:
                                record["유통기한날짜"] = pd.NaT
                        all_edited_records.append(record)
                else:
                    # 제품이 없어도 새로 추가할 수 있도록 빈 data_editor 제공
                    empty_df = pd.DataFrame(columns=editor_cols)
                    edited_cat = st.data_editor(
                        empty_df,
                        column_config=column_config,
                        num_rows="dynamic",
                        use_container_width=True,
                        hide_index=True,
                        key=f"editor_empty_{cat}",
                    )
                    for _, row in edited_cat.iterrows():
                        record = row.to_dict()
                        # 빈 data_editor에서 추가된 경우 카테고리 자동 설정
                        if not record.get("카테고리") or str(record.get("카테고리", "")).strip() == "":
                            record["카테고리"] = cat
                        raw_purchase = str(record.get("구매일", "")).strip()
                        if raw_purchase == "" or raw_purchase == "NaT":
                            record["구매일"] = pd.NaT
                        else:
                            try:
                                record["구매일"] = pd.Timestamp(raw_purchase)
                            except:
                                record["구매일"] = pd.NaT
                        raw_expiry = str(record.get("유통기한날짜", "")).strip()
                        if raw_expiry == "" or raw_expiry == "NaT":
                            record["유통기한날짜"] = pd.NaT
                        else:
                            try:
                                record["유통기한날짜"] = pd.Timestamp(raw_expiry)
                            except:
                                record["유통기한날짜"] = pd.NaT
                        all_edited_records.append(record)

        # 다른 카테고리에 속한 제품도 유지 (현재 세션에서 위 카테고리 목록 외 제품)
        other_products = st.session_state.cosmetics_df[~st.session_state.cosmetics_df["카테고리"].isin(categories)]
        if not other_products.empty:
            for _, row in other_products.iterrows():
                all_edited_records.append(row.to_dict())

        if all_edited_records:
            new_df = pd.DataFrame(all_edited_records)
            old_records = make_comparable(st.session_state.cosmetics_df)
            new_records_cmp = make_comparable(new_df)
            if old_records != new_records_cmp:
                st.session_state.cosmetics_df = new_df
                save_data(st.session_state.cosmetics_df)
                st.success("✅ 변경사항이 자동 저장되었습니다. 모든 탭에 반영됩니다.")
                st.rerun()

        st.caption("✏️ 셀을 클릭하여 값을 수정하세요. 하단의 + 버튼으로 새 행 추가, 행 선택 후 Delete 키로 행 삭제도 가능합니다. 수정 즉시 모든 탭에 자동 반영됩니다.")
