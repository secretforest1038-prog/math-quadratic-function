import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import tempfile

# -------------------------------------------------------------------------
# [설정 및 페이지 레이아웃]
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="포물선 운동 섬광사진 생성기",
    page_icon="⚽",
    layout="centered"
)

st.title("⚽ 공의 궤적으로 만나는 이차함수")
st.subtitle("직접 촬영한 공 던지기 영상으로 나만의 섬광사진을 만들고 포물선을 확인해 보세요!")
st.markdown("---")

# -------------------------------------------------------------------------
# [Helper 함수: 샘플 더미 영상 생성 로직]
# -------------------------------------------------------------------------
def create_mock_video():
    """영상이 없을 때 테스트할 수 있는 가상의 포물선 운동 영상을 생성합니다."""
    temp_dir = tempfile.gettempdir()
    mock_video_path = os.path.join(temp_dir, "mock_trajectory.mp4")
    
    # 영상 스펙 설정 (640x480, 30fps, 2초)
    width, height = 640, 480
    fps = 30
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(mock_video_path, fourcc, fps, (width, height))
    
    # 포물선 궤적 파라미터 (y = a(x-h)^2 + k 형태의 물리적 모사)
    # x는 50부터 590까지 이동
    total_frames = 60
    x_start, x_end = 50, 590
    
    for i in range(total_frames):
        # 배경은 약간 어두운 교실 혹은 체육관 느낌 (짙은 회색)
        frame = np.ones((height, width, 3), dtype=np.uint8) * 40
        
        # 현재 프레임까지의 공의 궤적을 계산하여 진행 중인 공을 그림
        t = i / (total_frames - 1)
        curr_x = int(x_start + (x_end - x_start) * t)
        # 최고점 h=320, k=100 (y축은 아래가 대칭이므로 뒤집어서 계산)
        # y = 0.002 * (x - 320)^2 + 100
        curr_y = int(0.0025 * (curr_x - 320)**2 + 100)
        
        # 공 그리기 (형광 연두색 공, 반지름 15)
        cv2.circle(frame, (curr_x, curr_y), 15, (0, 255, 128), -1)
        
        out.write(frame)
        
    out.release()
    return mock_video_path

# -------------------------------------------------------------------------
# [Core 함수: 영상 처리 및 섬광사진 생성]
# -------------------------------------------------------------------------
def generate_strobe_image(video_path, frame_interval=3):
    """
    영상의 프레임을 읽어와 지정된 간격으로 프레임을 합성(최댓값 누적)하여
    섬광사진 효과를 만들어냅니다.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception("영상을 열 수 없습니다. 파일 형식을 확인해주세요.")
        
    success, first_frame = cap.read()
    if not success:
        raise Exception("영상의 첫 번째 프레임을 읽을 수 없습니다.")
        
    # 결과물 베이스로 사용할 첫 프레임 (배경)
    strobe_acc = first_frame.copy()
    
    frame_count = 0
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        frame_count += 1
        # 교사가 설정한 프레임 간격마다 공의 위치(밝은 부분)를 합성
        if frame_count % frame_interval == 0:
            # cv2.max를 통해 움직이는 밝은 공의 잔상을 누적시킵니다.
            strobe_acc = cv2.max(strobe_acc, frame)
            
    cap.release()
    # OpenCV(BGR) 이미지를 Streamlit/Pillow(RGB) 포맷으로 변환
    strobe_rgb = cv2.cvtColor(strobe_acc, cv2.COLOR_BGR2RGB)
    return Image.fromarray(strobe_rgb)

# -------------------------------------------------------------------------
# [Helper 함수: 수학적 요소(모눈종이 및 좌표축) 오버레이]
# -------------------------------------------------------------------------
def draw_math_grid(image, show_grid=True, show_axis=True):
    """이미지 위에 수학적 탐구를 위한 그리드와 x, y축을 오버레이합니다."""
    img_canvas = image.copy()
    draw = ImageDraw.Draw(img_canvas)
    width, height = img_canvas.size
    
    # 1. 모눈종이(그리드) 그리기
    if show_grid:
        grid_size = 40  # 40픽셀 간격
        # 세로선
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill=(180, 180, 180), width=1)
        # 가로선
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill=(180, 180, 180), width=1)
            
    # 2. 간단한 x축, y축 좌표계 그리기 (화면 좌하단을 원점과 유사하게 세팅)
    if show_axis:
        axis_offset = 40
        axis_color = (255, 69, 0) # 원점 및 축은 오렌지레드 색상
        
        # x축 (하단에서 40픽셀 위)
        draw.line([(0, height - axis_offset), (width, height - axis_offset)], fill=axis_color, width=3)
        # y축 (좌측에서 40픽셀 우측)
        draw.line([(axis_offset, 0), (axis_offset, height)], fill=axis_color, width=3)
        
        # 원점(O) 및 축 이름 텍스트 표시
        draw.text((axis_offset - 15, height - axis_offset + 5), "O", fill=axis_color)
        draw.text((width - 20, height - axis_offset - 15), "X", fill=axis_color)
        draw.text((axis_offset + 10, 5), "Y", fill=axis_color)
        
    return img_canvas


# -------------------------------------------------------------------------
# [UI 구현: 3단계 진행 가이드]
# -------------------------------------------------------------------------

# 사이드바: 설정 및 테스트 옵션
with st.sidebar:
    st.header("⚙️ 실험 및 분석 설정")
    
    # 샘플 데이터 테스트 모드 활성화 체크박스
    use_sample = st.checkbox("샘플 영상으로 테스트하기", value=False, 
                             help="준비된 영상이 없다면 체크하여 가상 포물선 영상을 확인해보세요.")
    
    st.subheader("💡 섬광 간격 설정")
    # 숫자가 작을수록 공이 촘촘하게, 클수록 듬성듬성 보임
    frame_interval = st.slider("잔상 표시 간격 (프레임 단위)", min_value=1, max_value=10, value=3,
                               help="값이 작을수록 공의 궤적이 촘촘하게 연결됩니다.")
    
    st.subheader("📊 수학적 시각화 옵션")
    show_grid = st.checkbox("모눈종이(그리드) 보이기", value=True)
    show_axis = st.checkbox("x축, y축 좌표계 보이기", value=True)

# 본문 레이아웃
tab1, tab2, tab3 = st.tabs(["1️⃣ 영상 업로드", "2️⃣ 섬광사진 생성", "3️⃣ 분석 및 다운로드"])

video_path = None

# --- TAB 1: 영상 업로드 ---
with tab1:
    st.header("1. 공 던지기 영상 가져오기")
    st.info("어두운 배경에서 야광공이나 밝은색 공을 던지면 가장 깨끗한 궤적이 만들어집니다.")
    
    if use_sample:
        st.success("샘플 가상 영상 모드가 활성화되었습니다. [2단계] 탭으로 이동하세요.")
        video_path = create_mock_video()
        # 샘플 영상 재생 확인
        st.video(video_path)
    else:
        uploaded_file = st.file_uploader(
            "스마트폰으로 촬영한 포물선 영상 업로드 (.mp4, .mov, .avi)", 
            type=["mp4", "mov", "avi"]
        )
        
        if uploaded_file is not None:
            st.success(f"파일 업로드 완료: {uploaded_file.name} ({uploaded_file.size/1024/1024:.2f} MB)")
            
            # OpenCV에서 읽을 수 있도록 임시 파일로 저장
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(uploaded_file.read())
            video_path = tfile.name
            
            # 원본 영상 미리보기
            st.video(uploaded_file)
        else:
            st.warning("영상을 업로드하거나 좌측 사이드바에서 '샘플 영상으로 테스트하기'를 선택해주세요.")

# --- TAB 2 & 3: 분석 및 다운로드 (영상이 준비되었을 때만 작동) ---
if video_path is not None:
    # 미리 백엔드에서 이미지 변환을 수행하고 세션 상태에 저장하여 UI 지연을 방지
    if 'raw_strobe_img' not in st.session_state or st.button("🔄 설정 반영하여 다시 계산하기"):
        with st.spinner("🎬 영상을 분석하여 섬광사진을 생성하고 있습니다... 잠시만 기다려주세요!"):
            try:
                st.session_state.raw_strobe_img = generate_strobe_image(video_path, frame_interval)
            except Exception as e:
                st.error(f"영상 처리 중 오류가 발생했습니다: {e}")
                st.session_state.raw_strobe_img = None

    # 섬광사진이 성공적으로 생성되었다면
    if st.session_state.raw_strobe_img is not None:
        
        # TAB 2 화면 구성
        with tab2:
            st.header("2. 다중 노출 섬광사진 생성 완료")
            st.caption("비행하는 공의 모든 순간이 한 장의 사진에 기록되었습니다.")
            
            # 기본 섬광사진 출력
            st.image(st.session_state.raw_strobe_img, caption="변환된 섬광사진 원본", use_container_width=True)
            st.success("공의 흔적이 아름다운 선을 그리나요? [3️⃣ 분석 및 다운로드] 탭에서 수학적 그래프와 비교해보세요!")

        # TAB 3 화면 구성
        with tab3:
            st.header("3. 포물선 분석 및 결과 저장")
            st.markdown("""
            - **질문 1:** 공이 그리는 곡선은 위로 볼록한가요, 아래로 볼록한가요?
            - **질문 2:** 모눈종이와 좌표축을 기준으로 이 포물선의 **최고점(꼭짓점)**의 좌표는 어디일까요?
            """)
            
            # 시각화 옵션 적용한 최종 이미지 생성
            final_image = draw_math_grid(
                st.session_state.raw_strobe_img, 
                show_grid=show_grid, 
                show_axis=show_axis
            )
            
            # 최종 결과 이미지 출력
            st.image(final_image, caption="수학적 요소가 추가된 분석 이미지", use_container_width=True)
            
            # 다운로드를 위해 이미지를 임시 바이트로 변환
            import io
            img_byte_arr = io.BytesIO()
            final_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # 다운로드 버튼 제공
            st.download_button(
                label="💾 나의 포물선 사진 다운로드받기",
                data=img_byte_arr,
                file_name="my_parabola_strobe.png",
                mime="image/png"
            )
else:
    with tab2:
        st.info("1단계에서 영상을 업로드하면 섬광사진이 이곳에 표시됩니다.")
    with tab3:
        st.info("영상이 변환된 후 좌표축 위에서 포물선을 분석할 수 있습니다.")