"""
FFmpeg Wrapper Module - Direct FFmpeg operations for video processing
Provides a more efficient alternative to MoviePy by using FFmpeg directly
"""

import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union

from loguru import logger

class FFmpegWrapper:
    """
    Wrapper around FFmpeg command line tools for efficient video processing
    """
    
    @staticmethod
    def probe(file_path: str) -> Dict[str, Any]:
        """
        Get video/audio file metadata using ffprobe
        
        Args:
            file_path: Path to the video/audio file
            
        Returns:
            Dictionary containing file metadata
        """
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", file_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error probing file {file_path}: {e.stderr}")
            raise RuntimeError(f"Error probing file: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing ffprobe output: {e}")
            raise RuntimeError(f"Error parsing ffprobe output: {e}")
    
    @staticmethod
    def get_video_duration(file_path: str) -> float:
        """
        Get the duration of a video file
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Duration in seconds
        """
        try:
            info = FFmpegWrapper.probe(file_path)
            return float(info["format"]["duration"])
        except (KeyError, ValueError) as e:
            logger.error(f"Error getting video duration: {e}")
            return 0.0
    
    @staticmethod
    def get_video_dimensions(file_path: str) -> Tuple[int, int]:
        """
        Get the width and height of a video file
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Tuple of (width, height)
        """
        try:
            info = FFmpegWrapper.probe(file_path)
            for stream in info["streams"]:
                if stream["codec_type"] == "video":
                    return int(stream["width"]), int(stream["height"])
            return 0, 0
        except (KeyError, ValueError) as e:
            logger.error(f"Error getting video dimensions: {e}")
            return 0, 0
    
    @staticmethod
    def trim_video(input_file: str, output_file: str, start_time: float, 
                   duration: Optional[float] = None, fast_seek: bool = True) -> bool:
        """
        Cut a segment from a video file
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            start_time: Start time in seconds
            duration: Duration in seconds (optional)
            fast_seek: Use faster seeking method
            
        Returns:
            True if successful, False otherwise
        """
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        
        # Use fast seeking when possible
        if fast_seek and start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        
        cmd.extend(["-i", input_file])
        
        # Use slower but more accurate seeking when needed
        if not fast_seek and start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        
        if duration:
            cmd.extend(["-t", str(duration)])
            
        # Copy streams without re-encoding for speed
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", 
            output_file
        ])
        
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error trimming video: {e}")
            return False
    
    @staticmethod
    def resize_video(input_file: str, output_file: str, width: int, height: int, 
                    maintain_aspect_ratio: bool = True, pad: bool = True) -> bool:
        """
        Resize a video to specified dimensions
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            width: Target width
            height: Target height
            maintain_aspect_ratio: Whether to maintain the aspect ratio
            pad: Whether to pad the video to the target dimensions
            
        Returns:
            True if successful, False otherwise
        """
        filter_complex = f"scale={width}:{height}"
        
        if maintain_aspect_ratio:
            filter_complex = f"scale={width}:{height}:force_original_aspect_ratio=decrease"
            
            if pad:
                filter_complex += f",pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_file,
            "-vf", filter_complex,
            "-c:v", "libx264", "-preset", "ultrafast", 
            "-c:a", "copy",
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error resizing video: {e}")
            return False
    
    @staticmethod
    def concat_videos(input_files: List[str], output_file: str, 
                     with_audio: bool = True) -> bool:
        """
        Concatenate multiple video files
        
        Args:
            input_files: List of input video file paths
            output_file: Output video file path
            with_audio: Whether to include audio in the output
            
        Returns:
            True if successful, False otherwise
        """
        # Only proceed if we have input files
        if not input_files:
            logger.error("No input files provided for concatenation")
            return False
            
        # Create a temporary file listing the input files
        temp_dir = os.path.dirname(output_file)
        list_file = os.path.join(temp_dir, f"concat_list_{os.path.basename(output_file)}.txt")
        
        try:
            with open(list_file, "w") as f:
                for file_path in input_files:
                    if os.path.exists(file_path):
                        f.write(f"file '{file_path}'\n")
                    else:
                        logger.warning(f"File not found: {file_path}")
            
            # Check if the list file has content
            if os.path.getsize(list_file) == 0:
                logger.error("No valid input files for concatenation")
                return False
            
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", list_file
            ]
            
            if not with_audio:
                cmd.extend(["-an"])
                
            cmd.extend([
                "-c:v", "copy",  # Use copy codec for faster processing
                "-c:a", "aac", "-b:a", "192k",
                output_file
            ])
            
            subprocess.run(cmd, check=True)
            return True
            
        except Exception as e:
            logger.error(f"Error concatenating videos: {e}")
            return False
        finally:
            # Clean up the temporary list file
            if os.path.exists(list_file):
                os.remove(list_file)
    
    @staticmethod
    def add_subtitles(video_file: str, subtitle_file: str, output_file: str, 
                     font: str = "", font_size: int = 24, 
                     font_color: str = "white", position: str = "bottom",
                     outline_color: str = "black", outline_width: float = 1.0,
                     background_color: str = "") -> bool:
        """
        Add subtitles to a video file
        
        Args:
            video_file: Input video file path
            subtitle_file: Subtitle file path (srt format)
            output_file: Output video file path
            font: Font name
            font_size: Font size
            font_color: Font color (hex or named color)
            position: Subtitle position (top, bottom, center)
            outline_color: Outline color
            outline_width: Outline width
            background_color: Background color (optional)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Adding subtitles: font={font}, size={font_size}, position={position}")
        
        # Verify files exist
        if not os.path.exists(video_file):
            logger.error(f"Input video file not found: {video_file}")
            return False
            
        if not os.path.exists(subtitle_file):
            logger.error(f"Subtitle file not found: {subtitle_file}")
            return False
            
        # Set alignment based on position
        alignment = "2"  # Default: bottom center
        if position == "top":
            alignment = "6"  # Top center
        elif position == "center":
            alignment = "10"  # Middle center
        
        # Scale font size based on video resolution (assuming height is usually 1080 or 1920)
        # For 1080p, font_size is used as-is; for higher resolutions, we scale proportionally
        actual_width, actual_height = FFmpegWrapper.get_video_dimensions(video_file)
        if actual_height <= 0:
            actual_height = 1080  # Default to 1080p if we can't get dimensions
            
        # Adjust font size based on video resolution - use much smaller base size
        # Use a maximum of 24 points for 1080p video, scale down for larger resolutions
        base_size = 24  # Base size for 1080p
        # Hard limit the font size to reasonable values regardless of input
        adjusted_font_size = min(font_size // 3, int(base_size * (actual_height / 1080)))
        logger.info(f"Adjusted font size from {font_size} to {adjusted_font_size} for {actual_width}x{actual_height} video")
        
        # Limit outline width to a reasonable value
        adjusted_outline_width = min(outline_width, 0.8)
        
        # Construct the subtitle style with proper formatting
        style = f"FontName='{font}',FontSize={adjusted_font_size},PrimaryColour='{font_color}'"
        style += f",OutlineColour='{outline_color}',BorderStyle=1,Outline={adjusted_outline_width}"
        style += f",Alignment={alignment},MarginV=30,Bold=0"
        
        # Only add background if specifically requested
        if background_color and background_color.lower() != "transparent":
            style += f",BackColour='{background_color}'"
            style += ",BorderStyle=4,Shadow=0"  # BoxStyle with no shadow
        else:
            # No background, just outline
            style += ",BorderStyle=1,Shadow=0"

        # Create a temporary subtitle filter file
        temp_dir = os.path.dirname(output_file)
        filter_file = os.path.join(temp_dir, "subtitle_filter.txt")
        
        try:
            # Write the filter to a file to avoid command line escaping issues
            subtitle_path = subtitle_file.replace('\\', '/')
            with open(filter_file, "w", encoding="utf-8") as f:
                f.write(f"subtitles='{subtitle_path}':force_style='{style}'")
            
            # Use the filter file approach
            cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "info",
                "-i", video_file,
                "-filter_complex_script", filter_file,
                "-c:v", "libx264", "-preset", "medium", 
                "-c:a", "copy",
                output_file
            ]
            
            # Log the command
            logger.debug(f"FFmpeg subtitle command: {' '.join(cmd)}")
            
            # Run the command
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                logger.error(f"Error adding subtitles: {process.stderr}")
                # Try alternative hard-coded subtitle
                return FFmpegWrapper._add_subtitles_hardcoded(video_file, subtitle_file, output_file, font, adjusted_font_size, font_color, position)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding subtitles: {e}")
            # Try alternative approach
            return FFmpegWrapper._add_subtitles_hardcoded(video_file, subtitle_file, output_file, font, adjusted_font_size, font_color, position)
        finally:
            if os.path.exists(filter_file):
                os.remove(filter_file)
    
    @staticmethod
    def _add_subtitles_hardcoded(video_file: str, subtitle_file: str, output_file: str,
                              font: str = "", font_size: int = 24,
                              font_color: str = "white", position: str = "bottom") -> bool:
        """Fallback method for adding subtitles using direct subtitle burning"""
        logger.info("Trying alternative subtitle method with hardcoded subtitles")
        
        # Reduce font size to ensure it's not too large
        # Use a very conservative size (16-20pt is good for most videos)
        adjusted_font_size = min(font_size // 3, 20)
        logger.info(f"Using font size {adjusted_font_size} for hardcoded subtitles")
        
        try:
            # Create a temporary subtitles file with simpler formatting
            temp_srt = os.path.join(os.path.dirname(output_file), "temp_subtitles.ass")
            
            # Convert SRT to ASS format with specific styling
            convert_cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", subtitle_file,
                # Add custom ASS styling during conversion
                "-c:s", "ass",
                temp_srt
            ]
            
            subprocess.run(convert_cmd, check=True)
            
            # Modify the ASS file to adjust styling
            try:
                with open(temp_srt, 'r', encoding='utf-8') as f:
                    ass_content = f.read()
                
                # Add font size adjustment to the Style section
                if "Style: Default" in ass_content:
                    # Change Default style settings
                    ass_content = ass_content.replace(
                        "Style: Default,",
                        f"Style: Default,{font},{adjusted_font_size},&H{font_color.replace('#', '')},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0.5,0,2,"
                    )
                
                with open(temp_srt, 'w', encoding='utf-8') as f:
                    f.write(ass_content)
            except Exception as e:
                logger.warning(f"Could not modify ASS file: {e}")
            
            # Now burn the subtitles using the ASS file
            subtitle_cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", video_file,
                "-vf", f"ass={temp_srt}",
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy",
                output_file
            ]
            
            subprocess.run(subtitle_cmd, check=True)
            
            if os.path.exists(temp_srt):
                os.remove(temp_srt)
                
            return True
            
        except Exception as e:
            logger.error(f"Error with alternative subtitle method: {e}")
            
            # Last resort: try with basic subtitles and minimal formatting
            try:
                logger.info("Trying basic subtitle rendering as last resort")
                basic_cmd = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", video_file,
                    "-vf", f"subtitles={subtitle_file}:force_style='FontSize={min(16, adjusted_font_size)}'",
                    "-c:v", "libx264", "-preset", "medium",
                    "-c:a", "copy",
                    output_file
                ]
                subprocess.run(basic_cmd, check=True)
                return True
            except Exception as e2:
                logger.error(f"Final subtitle attempt failed: {e2}")
                return False
    
    @staticmethod
    def add_audio(video_file: str, audio_file: str, output_file: str, 
                 volume: float = 1.0) -> bool:
        """
        Replace or add audio to a video file
        
        Args:
            video_file: Input video file path
            audio_file: Audio file path
            output_file: Output video file path
            volume: Audio volume factor
            
        Returns:
            True if successful, False otherwise
        """
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_file, "-i", audio_file,
            "-filter_complex", f"[1:a]volume={volume}[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac",
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error adding audio: {e}")
            return False
    
    @staticmethod
    def add_background_music(video_file: str, audio_file: str, bgm_file: str, 
                           output_file: str, voice_volume: float = 1.0, 
                           bgm_volume: float = 0.3, fade_duration: int = 3) -> bool:
        """
        Add background music to a video with existing audio
        
        Args:
            video_file: Input video file path
            audio_file: Main audio file path (voice)
            bgm_file: Background music file path
            output_file: Output video file path
            voice_volume: Voice volume factor
            bgm_volume: Background music volume factor
            fade_duration: Fade duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_file, "-i", audio_file, "-i", bgm_file,
            "-filter_complex", 
            f"[1:a]volume={voice_volume}[a1];"
            f"[2:a]volume={bgm_volume},afade=out:st=3:d={fade_duration},aloop=loop=-1:size=0[a2];"
            f"[a1][a2]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error adding background music: {e}")
            return False
    
    @staticmethod
    def add_zoom_effect(image_file: str, output_file: str, duration: int = 5, 
                       zoom_factor: float = 1.2) -> bool:
        """
        Create a video with zoom effect from a static image
        
        Args:
            image_file: Input image file path
            output_file: Output video file path
            duration: Video duration in seconds
            zoom_factor: Final zoom factor
            
        Returns:
            True if successful, False otherwise
        """
        # Calculate zoom parameters
        zoom_start = 1.0
        zoom_end = zoom_factor
        
        # Apply zoompan filter for zoom effect
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", image_file, "-t", str(duration),
            "-vf", f"zoompan=z='min({zoom_start}+(in/{duration*25})*{zoom_end-zoom_start},{zoom_end})':d=1:s=1920x1080",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error adding zoom effect: {e}")
            return False
    
    @staticmethod
    def apply_transition(input_file: str, output_file: str, 
                        transition_type: str = "fade", duration: float = 1.0) -> bool:
        """
        Apply transition effect to a video
        
        Args:
            input_file: Input video file path
            output_file: Output video file path
            transition_type: Type of transition (fade, fadein, fadeout, slide)
            duration: Transition duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        # Set up filter based on transition type
        filter_complex = ""
        
        if transition_type == "fadein":
            filter_complex = f"fade=t=in:st=0:d={duration}"
        elif transition_type == "fadeout":
            # Get video duration to calculate fadeout start time
            video_duration = FFmpegWrapper.get_video_duration(input_file)
            fade_start = max(0, video_duration - duration)
            filter_complex = f"fade=t=out:st={fade_start}:d={duration}"
        elif transition_type == "fade":
            filter_complex = f"fade=t=in:st=0:d={duration},fade=t=out:st=outpts-{duration}:d={duration}"
        
        if not filter_complex:
            logger.error(f"Unsupported transition type: {transition_type}")
            return False
        
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_file,
            "-vf", filter_complex,
            "-c:a", "copy",
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error applying transition: {e}")
            return False
    
    @staticmethod
    def generate_video_from_script(
        video_clips: List[str],
        audio_file: str,
        subtitle_file: str,
        output_file: str,
        width: int = 1080,
        height: int = 1920,
        max_clip_duration: int = 5,
        font: str = "",
        font_size: int = 60,
        font_color: str = "#FFFFFF",
        subtitle_position: str = "bottom",
        outline_color: str = "#000000",
        outline_width: float = 1.5,
        background_music: str = "",
        voice_volume: float = 1.0,
        bgm_volume: float = 0.3
    ) -> bool:
        """
        Generate a complete video from script and clips
        
        Args:
            video_clips: List of video clip paths
            audio_file: Audio file path
            subtitle_file: Subtitle file path
            output_file: Output video file path
            width: Video width
            height: Video height
            max_clip_duration: Maximum duration for each clip in seconds
            font: Font name for subtitles
            font_size: Font size for subtitles
            font_color: Font color for subtitles
            subtitle_position: Subtitle position
            outline_color: Outline color for subtitles
            outline_width: Outline width for subtitles
            background_music: Background music file path (optional)
            voice_volume: Voice volume factor
            bgm_volume: Background music volume factor
            
        Returns:
            True if successful, False otherwise
        """
        if not video_clips:
            logger.error("No video clips provided")
            return False
            
        # Create temporary directory for intermediate files
        temp_dir = os.path.dirname(output_file)
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # 1. Process and prepare all clips
            processed_clips = []
            
            for i, clip_path in enumerate(video_clips):
                # a. Trim clip if needed
                duration = min(FFmpegWrapper.get_video_duration(clip_path), max_clip_duration)
                if duration <= 0:
                    continue
                    
                trimmed_clip = os.path.join(temp_dir, f"trimmed_{i}.mp4")
                if not FFmpegWrapper.trim_video(clip_path, trimmed_clip, 0, duration):
                    continue
                
                # b. Resize clip
                resized_clip = os.path.join(temp_dir, f"resized_{i}.mp4")
                if not FFmpegWrapper.resize_video(trimmed_clip, resized_clip, width, height):
                    continue
                
                processed_clips.append(resized_clip)
            
            if not processed_clips:
                logger.error("No valid clips after processing")
                return False
                
            # 2. Concatenate clips
            combined_video = os.path.join(temp_dir, "combined.mp4")
            if not FFmpegWrapper.concat_videos(processed_clips, combined_video):
                return False
                
            # 3. Add audio/music and subtitles
            with_audio = os.path.join(temp_dir, "with_audio.mp4")
            
            if background_music and os.path.exists(background_music):
                # Add voice and background music
                logger.info(f"Adding background music: {background_music}")
                if not FFmpegWrapper.add_background_music(
                    combined_video, audio_file, background_music, 
                    with_audio, voice_volume, bgm_volume
                ):
                    return False
            else:
                # Add just the voice audio
                logger.info("Adding voice audio without background music")
                if not FFmpegWrapper.add_audio(combined_video, audio_file, with_audio, voice_volume):
                    return False
            
            # Always add subtitles as a final step
            if subtitle_file and os.path.exists(subtitle_file):
                logger.info(f"Adding subtitles with font: {font}, size: {font_size}, position: {subtitle_position}")
                return FFmpegWrapper.add_subtitles(
                    with_audio, subtitle_file, output_file,
                    font, font_size, font_color, subtitle_position,
                    outline_color, outline_width
                )
            else:
                # Just use the audio version if no subtitles
                logger.warning("No subtitle file found, copying audio version as final output")
                shutil.copy(with_audio, output_file)
                return True
                    
        except Exception as e:
            logger.error(f"Error generating video: {e}")
            return False
        finally:
            # Clean up temporary files
            for pattern in ["trimmed_*.mp4", "resized_*.mp4", "combined.mp4", "with_audio.mp4"]:
                for file in [f for f in os.listdir(temp_dir) if f.startswith(pattern.replace("*", ""))]:
                    try:
                        os.remove(os.path.join(temp_dir, file))
                    except:
                        pass
        
        return True 