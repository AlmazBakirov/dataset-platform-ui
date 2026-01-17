import streamlit as st
from core.auth import require_role
from core.config import settings
from core.api_client import ApiClient
from core import mock_backend
from core.ui import header
from core.ui_helpers import api_call

require_role(["labeler", "admin", "universal"])
header("Annotate", "MVP: классификация (выбор классов). Task выбирается на странице My Tasks.")

def client() -> ApiClient:
    return ApiClient(
        settings.backend_url,
        token=st.session_state.get("token"),
        timeout_s=settings.request_timeout_s,
    )

# 1) Берем task_id из session_state (основной сценарий)
default_task_id = str(st.session_state.get("selected_task_id", "")).strip()

# 2) Оставляем поле ввода как fallback, но не заставляем пользователя копировать
task_id = st.text_input(
    "Task ID",
    value=default_task_id,
    placeholder="Выберите задачу в My Tasks",
).strip()

if task_id:
    st.session_state["selected_task_id"] = task_id
else:
    st.info("Сначала выберите задачу на странице **My Tasks** и нажмите **Annotate**.")
    if st.button("Back to My Tasks"):
        st.switch_page("pages/20_labeler_tasks.py")
    st.stop()

def do_get_task():
    return mock_backend.mock_get_task(task_id) if settings.use_mock else client().get_task(task_id)

task = api_call("Load task", do_get_task, spinner="Loading task...", show_payload=True)
if not task:
    st.stop()

st.subheader(task.get("title", "Task"))

images = task.get("images", [])
if not images:
    st.warning("No images in task.")
    st.stop()

# classes: prefer backend
classes = task.get("classes") or st.session_state.get("cached_classes") or ["pothole", "crosswalk", "traffic_light", "road_sign"]
st.session_state["cached_classes"] = classes

# --- индекс изображения (сохранение в session_state, чтобы не сбрасывался) ---
idx_key = f"img_idx_{task_id}"
if idx_key not in st.session_state:
    st.session_state[idx_key] = 0

idx = st.number_input(
    "Image index",
    min_value=0,
    max_value=len(images) - 1,
    value=int(st.session_state[idx_key]),
    step=1,
)

# sync index
st.session_state[idx_key] = int(idx)

img = images[int(idx)]
image_id = str(img.get("image_id", "")).strip()
if not image_id:
    st.error("Image record missing image_id.")
    st.stop()

st.write(f"Image: **{image_id}**")

if img.get("url"):
    st.image(img["url"], use_container_width=True)
else:
    st.info("Mock: нет URL. В проде backend должен отдавать ссылку на превью/объект в storage.")

# labels key per image to keep selection when navigating
labels_key = f"labels_{task_id}_{image_id}"
selected = st.multiselect("Labels", options=classes, key=labels_key)

auto_next = st.checkbox("Auto-next after Save", value=True)

def do_save():
    if settings.use_mock:
        return mock_backend.mock_save_labels(task_id, image_id, list(selected))
    return client().save_labels(task_id, image_id, list(selected))

if st.button("Save labels", type="primary"):
    resp = api_call("Save labels", do_save, spinner="Saving...", show_payload=True)
    if resp is not None:
        st.success("Saved.")
        if auto_next and int(idx) < len(images) - 1:
            st.session_state[idx_key] = int(idx) + 1
            st.rerun()

st.divider()
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    if st.button("Back to My Tasks", key="back_tasks"):
        st.switch_page("pages/20_labeler_tasks.py")
with c2:
    if st.button("Next image", disabled=(int(idx) >= len(images) - 1), key="next_img"):
        st.session_state[idx_key] = int(idx) + 1
        st.rerun()
with c3:
    st.caption("Task ID берется из My Tasks и хранится в st.session_state['selected_task_id'].")
