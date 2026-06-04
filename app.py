import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import tempfile
import io

# -------------------------------------------------------------------------
# [설정 및 페이지 레이아웃]
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="공의 궤적과 이차함수",
    page_icon="⚽",
    layout="centered"
)

# 기존 에러(st.subtitle)를 해결하기 위해 st.markdown으로 변경 및 한글화
st.title("⚽ 공의 궤적으로 만나는 이차함수")
st.markdown("### **직접 촬영한 공 던지기 영상으로 나만의 섬광사진을 만들고 포물선을 확인해 보세요!**")
st.markdown("---")

# -------------------------------------------------------------------------
# [기능 1: 가상 샘플 영상 생성 함수]
# -------------------------------------------------------------------------
def create_mock_video():
    """영상이 없을 때 테스트할 수 있는 가상의 포물선 운동 영상을 생성합니다."""
    temp_dir = tempfile.gettempdir()
    mock_video_path = os.path.join(temp_dir, "mock_trajectory.mp4")
    
    width, height = 640, 480
    fps = 30
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(mock_video_path, fourcc, fps, (width, height))
    
    total_frames = 60
    x_start, x_end = 50, 590
    
    for i in range(total_frames):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 40 # 어두운 배경
        t = i / (total_frames - 1)
        curr_x = int(x_start + (x_end - x_start) * t)
        curr_y = int(0.0025 * (curr_x - 320)**2 + 100) # 포물선 궤적 계산
        
        cv2.circle(frame, (curr_x, curr_y), 15, (0, 255, 128), -1) # 형광색 공
        out.write(frame)
        
    out.release()
    return mock_video_path

# -------------------------------------------------------------------------
# [기능 2: 영상 처리 및 섬광사진 생성 함수]
# -------------------------------------------------------------------------
def generate_strobe_image(video_path, frame_interval=3):
    """영상의 프레임들을 합성하여 섬광사진 효과를 만듭니다."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception("영상을 열 수 없습니다. 파일 형식을 확인해주세요.")
        
    success, first_frame = cap.read()
    if not success:
        raise Exception("영상의 첫 프레임을 읽을 수 없습니다.")
        
    strobe_acc = first_frame.copy()
    frame_count = 0
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        frame_count += 1
        if frame_count % frame_interval == 0:
            strobe_acc = cv2.max(strobe_acc, frame) # 최댓값 누적으로 잔상 생성
            
    cap.release()
    strobe_rgb = cv2.cvtColor(strobe_acc, cv2.COLOR_BGR2RGB)
    return Image.fromarray(strobe_rgb)

# -------------------------------------------------------------------------
# [기능 3: 수학적 요소(모눈종이, 좌표축) 추가 함수]
# -------------------------------------------------------------------------
def draw_math_grid(image, show_grid=True, show_axis=True):
    """이미지 위에 수학 탐구용 모눈종이와 x, y축을 그립니다."""
    img_canvas = image.copy()
    draw = ImageDraw.Draw(img_canvas)
    width, height = img_canvas.size
    
    # 모눈종이 선 그리기
    if show_grid:
        grid_size = 40
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill=(180, 180, 180), width=1)
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill=(180, 180, 180), width=1)
            
    # 좌표축 그리기
    if show_axis:
        axis_offset = 40
        axis_color = (255, 69, 0) # 주황빛 붉은색
        
        # x축 및 y축
        draw.line([(0, height - axis_offset), (width, height - axis_offset)], fill=axis_color, width=3)
        draw.line([(axis_offset, 0), (axis_offset, height)], fill=axis_color, width=3)
        
        # 한글 및 기호 표시
        draw.text((axis_offset - 15, height - axis_offset + 5), "O", fill=axis_color)
        draw.text((width - 20, height - axis_offset - 15), "X", fill=axis_color)
        draw.text((axis_offset + 10, 5), "Y", fill=axis_color)
        
    return img_canvas


# -------------------------------------------------------------------------
# [사용자 화면(UI) 구성 - 위에서 아래로 흐르는 단일 페이지 구조]
# -------------------------------------------------------------------------

# 사이드바 설정 영역 (모두 한글화)
with st.sidebar:
    st.header("⚙️ 실험 및 분석 설정")
    use_sample = st.checkbox("샘플 영상으로 테스트하기", value=False, 
                             help="준비된 영상이 없다면 체크하여 가상 영상을 확인해보세요.")
    
    st.markdown("---")
    st.subheader("💡 섬광 간격 설정")
    frame_interval = st.slider("잔상 표시 간격 (프레임)", min_value=1, max_value=10, value=3)
    
    st.markdown("---")
    st.subheader("📊 수학적 시각화 옵션")
    show_grid = st.checkbox("모눈종이(그리드) 보이기", value=True)
    show_axis = st.checkbox("x축, y축 좌표계 보이기", value=True)

# 메인 화면 영역
video_path = None

# [1단계] 파일 업로드 (이제 접속하자마자 무조건 첫 화면에 보입니다)
st.header("1️⃣ 공 던지기 영상 가져오기")

if use_sample:
    st.success("샘플 가상 영상 모드가 켜졌습니다. 아래에서 확인해보세요.")
    video_path = create_mock_video()
    st.video(video_path)
else:
    # 한글 안내와 업로드 버튼 배치
    uploaded_file = st.file_uploader(
        "스마트폰으로 촬영한 포물선 영상을 여기에 넣어주세요 (.mp4, .mov, .avi)", 
        type=["mp4", "mov", "avi"]
    )
    
    if uploaded_file is not None:
        st.success(f"성공적으로 가져왔습니다: {uploaded_file.name}")
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        video_path = tfile.name
        st.video(uploaded_file)
    else:
        st.info("💡 왼쪽 메뉴에서 '샘플 영상으로 테스트하기'를 누르거나, 직접 촬영한 영상을 업로드해 주세요.")

st.markdown("---")

# [2단계 & 3단계] 결과 처리 및 다운로드
if video_path is not None:
    st.header("2️⃣ 섬광사진 분석 및 결과")
    
    # 이미지 생성 프로세스 진행 (한글 스피너 띄우기)
    with st.spinner("🎬 영상을 분석하여 섬광사진을 만들고 있습니다. 잠시만 기다려주세요..."):
        try:
            raw_img = generate_strobe_image(video_path, frame_interval)
            
            # 수학적 효과 적용
            final_image = draw_math_grid(raw_img, show_grid=show_grid, show_axis=show_axis)
            
            # 화면에 최종 이미지 출력
            st.image(final_image, caption="수학적 요소가 포함된 최종 분석 이미지", use_container_width=True)
            
            # 다운로드 파일 변환
            img_byte_arr = io.BytesIO()
            final_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            st.markdown("### 3️⃣ 결과 저장하기")
            st.markdown("공이 그리는 곡선의 꼭짓점 좌표를 찾아보고, 아래 버튼을 눌러 사진을 보관하세요!")
            
            # 한글 다운로드 버튼
            st.download_button(
                label="💾 나의 포물선 사진 다운로드 받기",
                data=img_byte_arr,
                file_name="나의_포물선_섬광사진.png",
                mime="image/png"
            )
            
        except Exception as e:
            st.error(f"영상 분석 중 오류가 발생했습니다. 파일 형식을 다시 확인해 주세요. (에러 내용: {e})")
