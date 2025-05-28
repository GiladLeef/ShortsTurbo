import os
import platform
import sys
import re
from uuid import uuid4

import streamlit as st
from loguru import logger

# Add the root directory of the project to the system path to allow importing modules from the project
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.config import config
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import voice
from app.services import task as tm
from app.utils import utils

# Helper function for API key handling
def get_keys_from_config(cfg_key):
    api_keys = config.app.get(cfg_key, [])
    if isinstance(api_keys, str):
        api_keys = [api_keys]
    api_key = ", ".join(api_keys)
    return api_key


def save_keys_to_config(cfg_key, value):
    value = value.replace(" ", "")
    if value:
        config.app[cfg_key] = value.split(",")


# Helper function to extract keywords from script content
def extract_keywords_from_script(script_content, filename=None):
    """
    Extract keywords from script content or filename as fallback.
    
    Args:
        script_content (str): The content of the script
        filename (str, optional): The filename to use as fallback for keywords
        
    Returns:
        tuple: (processed_script, keywords_list)
    """
    # Check if the file contains keywords in a header section
    script_lines = script_content.strip().split('\n')
    keywords = []
    
    # Look for Keywords: keyword1, keyword2, keyword3 format at the beginning
    if script_lines and script_lines[0].startswith("Keywords:"):
        try:
            # Extract keywords list
            keywords_line = script_lines[0].replace("Keywords:", "").strip()
            # Parse as comma-separated list
            keywords = [k.strip() for k in keywords_line.split(",")]
            # Remove the keywords line from the script content
            script_content = "\n".join(script_lines[1:]).strip()
        except Exception as e:
            if filename:
                logger.warning(f"Failed to parse keywords from script {filename}: {str(e)}")
            else:
                logger.warning(f"Failed to parse keywords from script: {str(e)}")
    
    # If no keywords found in file, extract from filename (as fallback)
    if not keywords and filename:
        file_keywords = re.sub(r'\.txt$', '', filename)
        file_keywords = re.sub(r'[_\-]', ' ', file_keywords)
        keywords = [file_keywords]
    
    return script_content, keywords


st.set_page_config(
    page_title="ShortsTurbo",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "Report a bug": "https://github.com/GiladLeef/ShortsTurbo/issues",
        "About": "# ShortsTurbo\nSimply provide a script for a video, and it will "
        "automatically generate the video materials, video subtitles, "
        "and video background music before synthesizing a high-definition short "
        "video.\n\nhttps://github.com/GiladLeef/ShortsTurbo",
    },
)

streamlit_style = """
<style>
h1 {
    padding-top: 0 !important;
}
</style>
"""
st.markdown(streamlit_style, unsafe_allow_html=True)

font_dir = os.path.join(root_dir, "resource", "fonts")
scripts_dir = os.path.join(root_dir, "storage", "scripts")
if not os.path.exists(scripts_dir):
    os.makedirs(scripts_dir)

if "video_script" not in st.session_state:
    st.session_state["video_script"] = ""
if "video_terms" not in st.session_state:
    st.session_state["video_terms"] = ""
if "ui_language" not in st.session_state:
    st.session_state["ui_language"] = "en"

title_col = st.columns([1])[0]

with title_col:
    st.title(f"ShortsTurbo v{config.projectVersion}")

st.session_state["ui_language"] = "en"
config.ui["language"] = "en"

config.ui["hide_log"] = True

support_locales = [
    "en-US",  
]

def get_all_fonts():
    fonts = []
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".ttf") or file.endswith(".ttc"):
                fonts.append(file)
    fonts.sort()
    return fonts

def get_all_songs():
    songs = []
    for root, dirs, files in os.walk(song_dir):
        for file in files:
            if file.endswith(".mp3"):
                songs.append(file)
    return songs

def open_task_folder(task_id):
    try:
        sys = platform.system()
        path = os.path.join(root_dir, "storage", "tasks", task_id)
        if os.path.exists(path):
            if sys == "Windows":
                os.system(f"start {path}")
            if sys == "Darwin":
                os.system(f"open {path}")
    except Exception as e:
        logger.error(e)

def scroll_to_bottom():
    js = """
    <script>
        console.log("scroll_to_bottom");
        function scroll(dummy_var_to_force_repeat_execution){
            var sections = parent.document.querySelectorAll('section.main');
            console.log(sections);
            for(let index = 0; index<sections.length; index++) {
                sections[index].scrollTop = sections[index].scrollHeight;
            }
        }
        scroll(1);
    </script>
    """
    st.components.v1.html(js, height=0, width=0)

def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):

        file_path = record["file"].path

        relative_path = os.path.relpath(file_path, root_dir)

        record["file"].path = f"./{relative_path}"

        record["message"] = record["message"].replace(root_dir, ".")

        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level}</> | "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )

init_log()

panel = st.columns(3)
left_panel = panel[0]
middle_panel = panel[1]
right_panel = panel[2]

params = VideoParams(video_subject="")
uploaded_files = []
script_files = []

with left_panel:
    with st.container(border=True):
        st.write("Script Settings")

        script_input_type = st.radio(
            "Script Input Method",
            options=["Text Input", "File Upload", "Batch Processing"],
            horizontal=True
        )

        if script_input_type == "Text Input":

            params.video_script = st.text_area(
                "Video Script", value=st.session_state["video_script"], height=280
            )

            params.video_terms = st.text_area(
                "Video Keywords", value=st.session_state["video_terms"]
            )

        elif script_input_type == "File Upload":

            uploaded_script = st.file_uploader(
                "Upload Script File", 
                type=["txt"], 
                accept_multiple_files=False
            )

            if uploaded_script:

                script_content = uploaded_script.getvalue().decode("utf-8")

                processed_content, keywords = extract_keywords_from_script(script_content, uploaded_script.name)

                params.video_script = processed_content
                st.session_state["video_script"] = processed_content

                st.text_area("Script Content", value=processed_content, height=280)

                params.video_terms = keywords
                params.original_filename = uploaded_script.name
                st.session_state["video_terms"] = ", ".join(keywords)

                params.video_terms = st.text_area(
                    "Video Keywords", 
                    value=", ".join(keywords)
                )

        elif script_input_type == "Batch Processing":

            script_files = st.file_uploader(
                "Upload Script Files", 
                type=["txt"], 
                accept_multiple_files=True
            )

            if script_files:
                st.success(f"Uploaded {len(script_files)} script files")

                script_data = []
                for file in script_files:
                    content = file.getvalue().decode("utf-8")

                    processed_content, keywords = extract_keywords_from_script(content, file.name)

                    preview = processed_content[:100] + "..." if len(processed_content) > 100 else processed_content

                    script_data.append({
                        "Filename": file.name, 
                        "Preview": preview,
                        "Keywords": ", ".join(keywords)
                    })

                script_df = st.dataframe(
                    script_data,
                    column_config={
                        "Filename": st.column_config.TextColumn("Filename"),
                        "Preview": st.column_config.TextColumn("Content Preview"),
                        "Keywords": st.column_config.TextColumn("Keywords")
                    },
                    hide_index=True
                )

            st.info(
                "Batch processing will process all uploaded scripts with the same video settings. "
                "Keywords will be extracted from each script file. Each script will generate a video with the same name."
            )

            if script_files and st.button("Save Scripts to Disk"):
                for file in script_files:
                    file_path = os.path.join(scripts_dir, file.name)
                    with open(file_path, "wb") as f:
                        f.write(file.getvalue())
                st.success(f"Saved {len(script_files)} scripts to {scripts_dir}")

with middle_panel:
    with st.container(border=True):
        st.write("Video Settings")
        video_concat_modes = [
            ("Sequential", "sequential"),
            ("Random (Recommended)", "random"),
        ]
        video_sources = [
            ("Pexels", "pexels"),
            ("Pixabay", "pixabay"),
            ("Local file", "local"),
        ]

        saved_video_source_name = config.app.get("video_source", "pexels")
        saved_video_source_index = [v[1] for v in video_sources].index(
            saved_video_source_name
        )

        selected_index = st.selectbox(
            "Video Source",
            options=range(len(video_sources)),
            format_func=lambda x: video_sources[x][0],
            index=saved_video_source_index,
        )
        params.video_source = video_sources[selected_index][1]
        config.app["video_source"] = params.video_source

        if params.video_source == "pexels":
            pexels_api_key = get_keys_from_config("pexels_api_keys")
            pexels_api_key = st.text_input(
                "Pexels API Key", value=pexels_api_key, type="password"
            )
            save_keys_to_config("pexels_api_keys", pexels_api_key)

        elif params.video_source == "pixabay":
            pixabay_api_key = get_keys_from_config("pixabay_api_keys")
            pixabay_api_key = st.text_input(
                "Pixabay API Key", value=pixabay_api_key, type="password"
            )
            save_keys_to_config("pixabay_api_keys", pixabay_api_key)

        if params.video_source == "local":
            uploaded_files = st.file_uploader(
                "Upload Local Videos/Images",
                type=["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
            )

        selected_index = st.selectbox(
            "Video Concatenation Mode",
            index=1,
            options=range(
                len(video_concat_modes)
            ),
            format_func=lambda x: video_concat_modes[x][0],
        )
        params.video_concat_mode = VideoConcatMode(
            video_concat_modes[selected_index][1]
        )

        video_transition_modes = [
            ("None", VideoTransitionMode.none.value),
            ("FadeIn", VideoTransitionMode.fade_in.value),
            ("FadeOut", VideoTransitionMode.fade_out.value),
        ]
        selected_index = st.selectbox(
            "Video Transition Mode",
            options=range(len(video_transition_modes)),
            format_func=lambda x: video_transition_modes[x][0],
            index=0,
        )
        params.video_transition_mode = VideoTransitionMode(
            video_transition_modes[selected_index][1]
        )

        video_aspect_ratios = [
            ("Portrait 9:16", VideoAspect.portrait.value),
            ("Landscape 16:9", VideoAspect.landscape.value),
        ]
        selected_index = st.selectbox(
            "Video Aspect Ratio",
            options=range(
                len(video_aspect_ratios)
            ),
            format_func=lambda x: video_aspect_ratios[x][0],
        )
        params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])

        params.video_clip_duration = st.selectbox(
            "Maximum Clip Duration (seconds)", options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=1
        )

        if script_input_type != "Batch Processing":
            params.video_count = st.selectbox(
                "Number of Videos Generated",
                options=[1, 2, 3, 4, 5],
                index=0,
            )
        else:

            params.video_count = 1

    with st.container(border=True):
        st.write("Audio Settings")

        tts_servers = [
            ("azure-tts-v1", "Azure TTS V1"),
            ("azure-tts-v2", "Azure TTS V2"),
            ("siliconflow", "SiliconFlow TTS"),
        ]

        saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
        saved_tts_server_index = 0
        for i, (server_value, _) in enumerate(tts_servers):
            if server_value == saved_tts_server:
                saved_tts_server_index = i
                break

        selected_tts_server_index = st.selectbox(
            "TTS Server",
            options=range(len(tts_servers)),
            format_func=lambda x: tts_servers[x][1],
            index=saved_tts_server_index,
        )

        selected_tts_server = tts_servers[selected_tts_server_index][0]
        config.ui["tts_server"] = selected_tts_server

        filtered_voices = []

        if selected_tts_server == "siliconflow":

            filtered_voices = voice.get_siliconflow_voices()
        else:

            all_voices = voice.get_all_azure_voices(filter_locals=None)

            for v in all_voices:
                if selected_tts_server == "azure-tts-v2":

                    if "V2" in v:
                        filtered_voices.append(v)
                else:

                    if "V2" not in v:
                        filtered_voices.append(v)

        friendly_names = {
            v: v.replace("Female", "Female")
            .replace("Male", "Male")
            .replace("Neural", "")
            for v in filtered_voices
        }

        saved_voice_name = config.ui.get("voice_name", "")
        saved_voice_name_index = 0

        if saved_voice_name in friendly_names:
            saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name)
        else:

            for i, v in enumerate(filtered_voices):
                if v.lower().startswith(st.session_state["ui_language"].lower()):
                    saved_voice_name_index = i
                    break

        if saved_voice_name_index >= len(friendly_names) and friendly_names:
            saved_voice_name_index = 0

        if friendly_names:
            selected_friendly_name = st.selectbox(
                "Voice Selection",
                options=list(friendly_names.values()),
                index=min(saved_voice_name_index, len(friendly_names) - 1)
                if friendly_names
                else 0,
            )

            voice_name = list(friendly_names.keys())[
                list(friendly_names.values()).index(selected_friendly_name)
            ]
            params.voice_name = voice_name
            config.ui["voice_name"] = voice_name
        else:

            st.warning(
                "No voices available for the selected TTS server. Please select another server."
            )
            params.voice_name = ""
            config.ui["voice_name"] = ""

        if selected_tts_server == "azure-tts-v2" or (
            voice_name and voice.is_azure_v2_voice(voice_name)
        ):
            saved_azure_speech_region = config.azure.get("speech_region", "")
            saved_azure_speech_key = config.azure.get("speech_key", "")
            azure_speech_region = st.text_input(
                "Azure Region",
                value=saved_azure_speech_region,
                key="azure_speech_region_input",
            )
            azure_speech_key = st.text_input(
                "Azure API Key",
                value=saved_azure_speech_key,
                type="password",
                key="azure_speech_key_input",
            )
            config.azure["speech_region"] = azure_speech_region
            config.azure["speech_key"] = azure_speech_key

        if selected_tts_server == "siliconflow" or (
            voice_name and voice.is_siliconflow_voice(voice_name)
        ):
            saved_siliconflow_api_key = config.siliconflow.get("api_key", "")

            siliconflow_api_key = st.text_input(
                "SiliconFlow API Key",
                value=saved_siliconflow_api_key,
                type="password",
                key="siliconflow_api_key_input",
            )

            st.info(
                "SiliconFlow TTS Settings"
                + ":\n"
                + "- "
                + "Speed: Range [0.25, 4.0], default is 1.0"
                + "\n"
                + "- "
                + "Volume: Uses Speech Volume setting, default 1.0 maps to gain 0"
            )

            config.siliconflow["api_key"] = siliconflow_api_key

        params.voice_volume = st.selectbox(
            "Speech Volume",
            options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0],
            index=2,
        )

        params.voice_rate = st.selectbox(
            "Speech Rate",
            options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0],
            index=2,
        )

        bgm_options = [
            ("No Background Music", ""),
            ("Random Background Music", "random"),
            ("Custom Background Music", "custom"),
        ]
        selected_index = st.selectbox(
            "Background Music",
            index=1,
            options=range(len(bgm_options)),
            format_func=lambda x: bgm_options[x][0],
        )

        params.bgm_type = bgm_options[selected_index][1]

        if params.bgm_type == "custom":
            custom_bgm_file = st.text_input(
                "Custom Music File Path", key="custom_bgm_file_input"
            )
            if custom_bgm_file and os.path.exists(custom_bgm_file):
                params.bgm_file = custom_bgm_file

        params.bgm_volume = st.selectbox(
            "Background Music Volume",
            options=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            index=2,
        )

with right_panel:
    with st.container(border=True):
        st.write("Subtitle Settings")
        params.subtitle_enabled = st.checkbox("Enable Subtitles", value=True)
        font_names = get_all_fonts()
        saved_font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
        saved_font_name_index = 0
        if saved_font_name in font_names:
            saved_font_name_index = font_names.index(saved_font_name)
        params.font_name = st.selectbox(
            "Font", font_names, index=saved_font_name_index
        )
        config.ui["font_name"] = params.font_name

        subtitle_positions = [
            ("Top", "top"),
            ("Center", "center"),
            ("Bottom", "bottom"),
            ("Custom", "custom"),
        ]
        selected_index = st.selectbox(
            "Position",
            index=2,
            options=range(len(subtitle_positions)),
            format_func=lambda x: subtitle_positions[x][0],
        )
        params.subtitle_position = subtitle_positions[selected_index][1]

        if params.subtitle_position == "custom":
            custom_position = st.text_input(
                "Custom Position (%)",
                value="70.0",
                key="custom_position_input",
            )
            try:
                params.custom_position = float(custom_position)
                if params.custom_position < 0 or params.custom_position > 100:
                    st.error("Please enter a value between 0 and 100")
            except ValueError:
                st.error("Please enter a valid number")

        font_cols = st.columns([0.3, 0.7])
        with font_cols[0]:
            saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
            params.text_fore_color = st.color_picker(
                "Font Color", saved_text_fore_color
            )
            config.ui["text_fore_color"] = params.text_fore_color

        with font_cols[1]:
            saved_font_size = config.ui.get("font_size", 24)
            params.font_size = st.slider("Font Size", 16, 36, saved_font_size)
            config.ui["font_size"] = params.font_size

        # Text background option (disabled by default)
        params.text_background_color = st.checkbox("Enable Text Background", value=False)

        stroke_cols = st.columns([0.3, 0.7])
        with stroke_cols[0]:
            params.stroke_color = st.color_picker("Outline Color", "#000000")
        with stroke_cols[1]:
            params.stroke_width = st.slider("Outline Width", 0.0, 1.5, 0.5)

if script_input_type == "Batch Processing":
    start_button = st.button("Generate Videos from All Scripts", use_container_width=True, type="primary")
else:
    start_button = st.button("Generate Video", use_container_width=True, type="primary")

if start_button:
    config.save_config()

    if script_input_type == "Batch Processing" and script_files:

        def log_received(msg):
            pass
        logger.add(log_received)

        st.info(f"Starting batch processing of {len(script_files)} script files...")
        progress_bar = st.progress(0)

        results = []
        for i, script_file in enumerate(script_files):
            task_id = str(uuid4())
            script_content = script_file.getvalue().decode("utf-8")

            processed_content, keywords = extract_keywords_from_script(script_content, script_file.name)

            filename = script_file.name
            base_filename = os.path.splitext(filename)[0]

            batch_params = VideoParams(
                video_subject="",
                video_script=processed_content,
                video_terms=keywords,
                original_filename=script_file.name,  
                voice_name=params.voice_name,
                voice_rate=params.voice_rate,
                voice_volume=params.voice_volume,
                video_source=params.video_source,
                video_concat_mode=params.video_concat_mode,
                video_transition_mode=params.video_transition_mode,
                video_aspect=params.video_aspect,
                video_clip_duration=params.video_clip_duration,
                video_count=1,  
                subtitle_enabled=params.subtitle_enabled,
                font_name=params.font_name,
                subtitle_position=params.subtitle_position,
                text_fore_color=params.text_fore_color,
                font_size=params.font_size,
                stroke_color=params.stroke_color,
                stroke_width=params.stroke_width,
                bgm_type=params.bgm_type,
                bgm_file=params.bgm_file,
                bgm_volume=params.bgm_volume,
            )

            if params.video_source == "local" and uploaded_files:
                for file in uploaded_files:
                    file_path = os.path.join(utils.storage_dir("local_videos", create=True), f"{file.file_id}_{file.name}")
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                        m = MaterialInfo()
                        m.provider = "local"
                        m.url = file_path
                        if not batch_params.video_materials:
                            batch_params.video_materials = []
                        batch_params.video_materials.append(m)

            try:
                result = tm.start(task_id=task_id, params=batch_params)
                if result and "videos" in result:
                    video_files = result.get("videos", [])
                    if video_files:
                        results.append({
                            "filename": base_filename,
                            "task_id": task_id,
                            "videos": video_files
                        })
                    else:
                        logger.error(f"No videos generated for {filename}")
                else:
                    logger.error(f"Failed to generate video for {filename}")
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")

            progress_bar.progress((i + 1) / len(script_files))

        if results:
            st.success(f"Generated videos for {len(results)}/{len(script_files)} scripts")

            result_data = []
            for res in results:
                video_links = []
                for i, video_path in enumerate(res["videos"]):
                    video_links.append(f"[Video {i+1}]({video_path})")
                result_data.append({
                    "Script": res["filename"],
                    "Task ID": res["task_id"],
                    "Videos": ", ".join(video_links)
                })

            st.write("Generated Videos:")
            st.dataframe(
                result_data,
                column_config={
                    "Script": st.column_config.TextColumn("Script"),
                    "Task ID": st.column_config.TextColumn("Task ID"),
                    "Videos": st.column_config.LinkColumn("Video Links")
                },
                hide_index=True
            )

            st.write("Sample of Generated Videos:")
            sample_videos = min(3, len(results))
            video_cols = st.columns(sample_videos)
            for i in range(sample_videos):
                if i < len(results) and results[i]["videos"]:
                    video_cols[i].video(results[i]["videos"][0])
                    video_cols[i].caption(results[i]["filename"])
        else:
            st.error("No videos were successfully generated")

        logger.info("Batch video generation completed")
        scroll_to_bottom()

    else:
        task_id = str(uuid4())

        if script_input_type == "Text Input" and not params.video_script:
            st.error("Video Script cannot be empty")
            scroll_to_bottom()
            st.stop()

        if params.video_source not in ["pexels", "pixabay", "local"]:
            st.error("Please Select a Valid Video Source")
            scroll_to_bottom()
            st.stop()

        if params.video_source == "pexels" and not config.app.get("pexels_api_keys", ""):
            st.error("Please Enter the Pexels API Key")
            scroll_to_bottom()
            st.stop()

        if params.video_source == "pixabay" and not config.app.get("pixabay_api_keys", ""):
            st.error("Please Enter the Pixabay API Key")
            scroll_to_bottom()
            st.stop()

        if uploaded_files:
            local_videos_dir = utils.storage_dir("local_videos", create=True)
            for file in uploaded_files:
                file_path = os.path.join(local_videos_dir, f"{file.file_id}_{file.name}")
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                    m = MaterialInfo()
                    m.provider = "local"
                    m.url = file_path
                    if not params.video_materials:
                        params.video_materials = []
                    params.video_materials.append(m)

        def log_received(msg):
            pass
        logger.add(log_received)

        st.toast("Generating Video")
        logger.info("Start Generating Video")
        logger.info(utils.to_json(params))
        scroll_to_bottom()

        result = tm.start(task_id=task_id, params=params)
        if not result or "videos" not in result:
            st.error("Video Generation Failed")
            logger.error("Video Generation Failed")
            scroll_to_bottom()
            st.stop()

        video_files = result.get("videos", [])
        st.success("Video Generation Completed")
        try:
            if video_files:
                player_cols = st.columns(len(video_files) * 2 + 1)
                for i, url in enumerate(video_files):
                    player_cols[i * 2 + 1].video(url)
        except Exception:
            pass

        open_task_folder(task_id)
        logger.info("Video Generation Completed")
        scroll_to_bottom()

config.save_config()