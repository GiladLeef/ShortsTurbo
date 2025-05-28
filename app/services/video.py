import glob
import os
import random
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

import ffmpeg
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models import const
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.utils import utils
from app.services.ffmpeg_wrapper import FFmpegWrapper

class SubClippedVideoClip:
    def __init__(self, file_path, start_time=None, end_time=None, width=None, height=None, duration=None):
        self.file_path = file_path
        self.start_time = start_time
        self.end_time = end_time
        self.width = width
        self.height = height
        if duration is None:
            self.duration = end_time - start_time
        else:
            self.duration = duration

    def __str__(self):
        return f"SubClippedVideoClip(file_path={self.file_path}, start_time={self.start_time}, end_time={self.end_time}, duration={self.duration}, width={self.width}, height={self.height})"


def delete_files(files: List[str] | str):
    if isinstance(files, str):
        files = [files]
        
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            logger.warning(f"Failed to delete file {file}: {str(e)}")

def get_bgm_file(bgm_type: str = "random", bgm_file: str = ""):
    if not bgm_type:
        return ""

    if bgm_file and os.path.exists(bgm_file):
        return bgm_file

    if bgm_type == "random":
        suffix = "*.mp3"
        song_dir = utils.songDir()
        files = glob.glob(os.path.join(song_dir, suffix))
        if not files:
            logger.warning("No background music files found")
            return ""
        return random.choice(files)

    return ""


def combine_videos(
    combined_video_path: str,
    video_paths: List[str],
    audio_file: str,
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_concat_mode: VideoConcatMode = VideoConcatMode.random,
    video_transition_mode: VideoTransitionMode = None,
    max_clip_duration: int = 5,
    threads: int = 2,
) -> str:
    # For performance, use direct FFMPEG concatenation instead of frame-by-frame processing
    # when transitions are not needed
    use_direct_ffmpeg = (video_transition_mode is None or 
                        video_transition_mode.value == VideoTransitionMode.none.value)
    
    # Get audio duration using FFmpegWrapper
    audio_duration = FFmpegWrapper.get_video_duration(audio_file)
    logger.info(f"audio duration: {audio_duration} seconds")
    logger.info(f"maximum clip duration: {max_clip_duration} seconds")
    
    output_dir = os.path.dirname(combined_video_path)

    aspect = VideoAspect(video_aspect)
    video_width, video_height = aspect.to_resolution()

    # Prepare video clips information
    subclipped_items = []
    for video_path in video_paths:
        try:
            clip_info = ffmpeg.probe(video_path)
            video_stream = next((s for s in clip_info['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                clip_duration = float(clip_info['format']['duration'])
                clip_w = int(video_stream['width'])
                clip_h = int(video_stream['height'])
                
                start_time = 0
                while start_time < clip_duration:
                    end_time = min(start_time + max_clip_duration, clip_duration)
                    if clip_duration - start_time >= 1.0:  # At least 1 second long segments
                        subclipped_items.append(SubClippedVideoClip(
                            file_path=video_path, 
                            start_time=start_time, 
                            end_time=end_time, 
                            width=clip_w, 
                            height=clip_h))
                    start_time = end_time
                    if video_concat_mode.value == VideoConcatMode.sequential.value:
                        break
        except Exception as e:
            logger.error(f"Error analyzing video {video_path}: {str(e)}")
            continue

    # Random order for clips if requested
    if video_concat_mode.value == VideoConcatMode.random.value:
        random.shuffle(subclipped_items)
        
    logger.debug(f"total subclipped items: {len(subclipped_items)}")
    
    # Process as many clips as needed to match audio duration
    processed_clips = []
    video_duration = 0
    
    # Using optimized FFmpeg approach
    logger.info("Using optimized direct FFMPEG concatenation")
    
    # Function to prepare a clip segment with FFMPEG
    def prepare_clip_segment(idx, item):
        try:
            output_file = f"{output_dir}/temp-clip-{idx}.mp4"
            
            # Get segment duration
            segment_duration = min(item.end_time - item.start_time, max_clip_duration)
            
            # Use FFmpegWrapper to trim the video
            if not FFmpegWrapper.trim_video(
                input_file=item.file_path,
                output_file=output_file,
                start_time=item.start_time,
                duration=segment_duration,
                fast_seek=True
            ):
                return idx, None, 0
            
            # Resize the video if needed
            if item.width != video_width or item.height != video_height:
                resized_file = f"{output_dir}/temp-resized-{idx}.mp4"
                if not FFmpegWrapper.resize_video(
                    input_file=output_file,
                    output_file=resized_file,
                    width=video_width,
                    height=video_height,
                    maintain_aspect_ratio=True,
                    pad=True
                ):
                    return idx, None, 0
                
                # Replace the original output file with the resized one
                delete_files(output_file)
                os.rename(resized_file, output_file)
            
            # Apply transition if needed
            if video_transition_mode and video_transition_mode.value != VideoTransitionMode.none.value:
                transition_file = f"{output_dir}/temp-transition-{idx}.mp4"
                
                if video_transition_mode.value == VideoTransitionMode.fade_in.value:
                    transition_type = "fadein"
                elif video_transition_mode.value == VideoTransitionMode.fade_out.value:
                    transition_type = "fadeout"
                else:
                    transition_type = "fade"
                    
                if not FFmpegWrapper.apply_transition(
                    input_file=output_file,
                    output_file=transition_file,
                    transition_type=transition_type,
                    duration=1.0
                ):
                    return idx, None, 0
                
                # Replace the original output file with the transitioned one
                delete_files(output_file)
                os.rename(transition_file, output_file)
            
            return idx, output_file, segment_duration
        except Exception as e:
            logger.error(f"Error preparing clip segment {idx}: {str(e)}")
            return idx, None, 0
    
    # Process clips in parallel using ThreadPoolExecutor
    max_workers = min(os.cpu_count() or 4, 8)  # Use up to 8 worker threads
    logger.info(f"Processing video segments using {max_workers} parallel workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, item in enumerate(subclipped_items):
            if video_duration >= audio_duration:
                break
            futures.append(executor.submit(prepare_clip_segment, i, item))
            video_duration += min(item.end_time - item.start_time, max_clip_duration)
        
        # Collect results as they complete
        for future in as_completed(futures):
            idx, output_file, duration = future.result()
            if output_file:
                processed_clips.append((idx, output_file, duration))
    
    # Sort clips by index to maintain order
    processed_clips.sort()
    processed_clips = [clip[1] for clip in processed_clips]
    
    if not processed_clips:
        logger.warning("No clips available for combining")
        return ""
    
    # Concatenate clips using FFmpeg wrapper
    logger.info("Concatenating video segments with FFmpeg")
    
    # If we have only one clip, just add audio to it
    if len(processed_clips) == 1:
        logger.info("Only one clip to process, adding audio directly")
        if not FFmpegWrapper.add_audio(
            video_file=processed_clips[0],
            audio_file=audio_file,
            output_file=combined_video_path,
            volume=1.0
        ):
            logger.error("Failed to add audio to the single clip")
            delete_files(processed_clips)
            return ""
        
        logger.info("Video generation completed successfully")
        delete_files(processed_clips)
        return combined_video_path
    
    # For multiple clips, concatenate them first
    temp_concat_video = f"{output_dir}/temp-concat-video.mp4"
    if not FFmpegWrapper.concat_videos(
        input_files=processed_clips,
        output_file=temp_concat_video,
        with_audio=False
    ):
        logger.error("Failed to concatenate video clips")
        delete_files(processed_clips)
        return ""
    
    # Add audio to the concatenated video
    if not FFmpegWrapper.add_audio(
        video_file=temp_concat_video,
        audio_file=audio_file,
        output_file=combined_video_path,
        volume=1.0
    ):
        logger.error("Failed to add audio to the concatenated video")
        delete_files(processed_clips + [temp_concat_video])
        return ""
    
    # Clean up temporary files
    delete_files(processed_clips + [temp_concat_video])
    
    logger.info("Video combining completed successfully")
    return combined_video_path


def generate_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_file: str,
    params: VideoParams,
):
    aspect = VideoAspect(params.video_aspect)
    video_width, video_height = aspect.to_resolution()

    logger.info(f"Generating video: {video_width} x {video_height}")
    logger.info(f"  ① video: {video_path}")
    logger.info(f"  ② audio: {audio_path}")
    logger.info(f"  ③ subtitle: {subtitle_path}")
    logger.info(f"  ④ output: {output_file}")

    # Get directory for temp files
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if subtitles are enabled and font is available
    font_path = ""
    if params.subtitle_enabled:
        if not params.font_name:
            params.font_name = "STHeitiMedium.ttc"
        font_path = os.path.join(utils.fontDir(), params.font_name)
        # Use os.path.normpath for cross-platform path normalization
        font_path = os.path.normpath(font_path)
        logger.info(f"  ⑤ font: {font_path}")
    
    # Check for background music
    bgm_file = get_bgm_file(bgm_type=params.bgm_type, bgm_file=params.bgm_file)
    
    # Generate the video using FFmpegWrapper's complete video generation function
    result = FFmpegWrapper.generate_video_from_script(
        video_clips=[video_path],
        audio_file=audio_path,
        subtitle_file=subtitle_path if params.subtitle_enabled else None,
        output_file=output_file,
        width=video_width,
        height=video_height,
        max_clip_duration=100000,  # Use a large value since we're using the entire video
        font=params.font_name,
        font_size=params.font_size,
        font_color=params.text_fore_color,
        subtitle_position=params.subtitle_position,
        outline_color=params.stroke_color,
        outline_width=params.stroke_width,
        background_music=bgm_file,
        voice_volume=params.voice_volume,
        bgm_volume=params.bgm_volume
    )
    
    if result:
        logger.info("Video generation completed successfully")
    else:
        logger.error("Failed to generate video")
    
    return


def preprocess_video(materials: List[MaterialInfo], clip_duration=4):
    for material in materials:
        if not material.url:
            continue

        ext = utils.parseExtension(material.url)
        
        # Get dimensions using FFmpeg
        try:
            width, height = FFmpegWrapper.get_video_dimensions(material.url)
        except Exception:
            logger.error(f"Failed to get dimensions for {material.url}")
            continue
            
        if width < 480 or height < 480:
            logger.warning(f"Low resolution material: {width}x{height}, minimum 480x480 required")
            continue

        # For images, create a video with zoom effect
        if ext in const.FILE_TYPE_IMAGES:
            logger.info(f"Processing image: {material.url}")
            video_file = f"{material.url}.mp4"
            
            # Use FFmpegWrapper to create a video with zoom effect
            if FFmpegWrapper.add_zoom_effect(
                image_file=material.url,
                output_file=video_file,
                duration=clip_duration,
                zoom_factor=1.2
            ):
                logger.success(f"Image processed: {video_file}")
                material.url = video_file
            else:
                logger.error(f"Failed to process image: {material.url}")
                
    return materials