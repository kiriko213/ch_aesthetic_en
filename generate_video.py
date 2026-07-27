import os
import requests
import random
import re
import edge_tts
import gtts
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip, ImageClip, ColorClip, concatenate_videoclips, CompositeAudioClip, vfx, afx
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# Pillow 10.0.0以降でのANTIALIASエラー対策
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

def normalize_text_for_speech(text, language="ja"):
    """
    ナレーション用にテキストを最適化する。
    - 適切な位置に句読点を挿入して「間」を作る
    - アルファベットの読みをカタカナに変換（誤読防止）
    """
    if language == "ja":
        # 誤読防止
        text = text.replace("VS", "バーサス").replace("vs", "バーサス")
        text = text.replace("AI", "エーアイ")
        # 文末に句点がない場合に補完（間を空けるため）
        if not text.endswith(("。", "！", "？")):
            text += "。"
        # 長い文章に適度な読点を打つ
        text = text.replace("、", "、").replace("  ", " ")
    else:
        text = text.replace("VS", "versus").replace("vs", "versus")
    return text

def create_boxed_text_image(text, size=(1080, 1920), fontsize=60):
    """
    中央に2-3行の読みやすい字幕画像を生成。日本語・英語の両対応。
    """
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if os.name == 'nt':
        font_path = "C:\\Windows\\Fonts\\meiryo.ttc"
    else:
        # Linux (Ubuntu) 環境向けのフォント候補（CJKおよび英字標準）
        font_candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]
        font_path = next((p for p in font_candidates if os.path.exists(p)), None)
    
    font = ImageFont.truetype(font_path, fontsize) if font_path and os.path.exists(font_path) else ImageFont.load_default()

    # 最大3行程度に収める
    max_width = 850
    
    # 日本語/中国語などの全角文字が含まれるか判定
    is_cjk = any(ord(char) > 0x2000 for char in text)
    
    if is_cjk:
        # 日本語などの文字単位での分割
        words = list(text.strip())
        join_char = ""
    else:
        # 英語などの単語単位での分割
        words = text.strip().split()
        join_char = " "
        
    lines = []
    current_line = ""
    
    for word in words:
        test_line = (current_line + join_char + word).strip() if current_line else word
        if draw.textbbox((0, 0), test_line, font=font)[2] > max_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    
    # 描画位置の計算
    line_spacing = 30
    total_text_height = sum([draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1] for l in lines]) + line_spacing * (len(lines) - 1)
    
    box_width = 950
    box_height = total_text_height + 120
    box_x = (size[0] - box_width) // 2
    box_y = (size[1] - box_height) // 2
    
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle([box_x, box_y, box_x + box_width, box_y + box_height], radius=40, fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    current_y = box_y + 60
    for line in lines:
        w = draw.textbbox((0, 0), line, font=font)[2]
        x = (size[0] - w) // 2
        draw.text((x, current_y), line, font=font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0,0,0))
        current_y += draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] + line_spacing
        
    return img

async def generate_speech(text, output_path, voice="ja-JP-NanamiNeural", rate="+5%"):
    """
    音声合成を行い、ファイルが正しく生成されたかチェックする。
    edge_ttsがGitHub Actionsで403エラーになる場合、gTTSにフォールバックする。
    """
    text = text.strip() if text else ""
    if not text:
        print("[SPEECH_LOG] generate_speech called with empty or None text. Skipping TTS generation.")
        return

    edge_tts_ver = getattr(edge_tts, '__version__', 'unknown')
    print(f"[SPEECH_LOG] Voice: {voice} | edge-tts Version: {edge_tts_ver} | Rate: {rate}")
    try:
        print(f"[SPEECH_LOG] Selected TTS Engine: edge-tts")
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
            raise Exception("Generated audio file is empty or too small.")
        print(f"[SPEECH_LOG] Successfully generated speech using TTS Engine: edge-tts")
    except Exception as e:
        print(f"[SPEECH_LOG] edge-tts Error: {e}, falling back to gTTS...")
        try:
            lang = "ja" if "ja-JP" in voice else "en"
            print(f"[SPEECH_LOG] Selected TTS Engine: gTTS (Fallback)")
            tts = gtts.gTTS(text=text, lang=lang)
            tts.save(output_path)
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                raise Exception("gTTS output is empty.")
            print(f"[SPEECH_LOG] Successfully generated speech using TTS Engine: gTTS (Fallback)")
        except Exception as fallback_e:
            print(f"[SPEECH_LOG] gTTS Fallback Error: {fallback_e}")
            raise

async def fetch_best_visual(query, api_key, target_animal="dog", forbidden_animals=["cat"], work_dir="."):
    """
    対象動物と禁止キーワードを厳格に指定してPexelsから複数動画を検索し、最大3本の動画パスのリストを返す。
    """
    headers = {"Authorization": api_key}
    
    # 除外クエリの作成
    exclude = " ".join([f"-{a}" for a in forbidden_animals])
    
    # 検索クエリの構築
    base_queries = [
        f"{target_animal} {query}",
        target_animal,
        f"cute {target_animal}"
    ]

    queries = [f"{q} {exclude}".strip() for q in base_queries]
    print(f"[DEBUG] Pexels Strict Queries: {queries}")
    
    for q in queries:
        try:
            v_url = f"https://api.pexels.com/videos/search?query={q}&per_page=15&orientation=portrait"
            res = requests.get(v_url, headers=headers)
            res.raise_for_status()
            v_data = res.json()
            if v_data.get('videos'):
                videos = v_data['videos']
                downloaded_paths = []
                for v in videos:
                    video_files = [f for f in v.get('video_files', []) if f.get('width', 0) >= 720]
                    if not video_files and v.get('video_files'):
                        video_files = v['video_files']
                    if video_files:
                        best_file = video_files[0]
                        path = os.path.join(work_dir, f"temp_bg_{len(downloaded_paths)}.mp4")
                        v_res = requests.get(best_file['link'])
                        with open(path, 'wb') as f:
                            f.write(v_res.content)
                        downloaded_paths.append(path)
                        if len(downloaded_paths) >= 3:
                            break
                
                # 取得数が3本未満の場合は再利用して3本にするフォールバック
                if downloaded_paths:
                    base_count = len(downloaded_paths)
                    while len(downloaded_paths) < 3:
                        downloaded_paths.append(downloaded_paths[len(downloaded_paths) % base_count])
                    return downloaded_paths, "video"
        except Exception as e:
            print(f"[WARN] Pexels Search Error for '{q}': {e}")
            continue
    return None, None

async def assemble_video_professional(script, asset_path, asset_type, bgm_path, output_filename, voice="ja-JP-NanamiNeural", topic="", work_dir="."):
    raw_sections = [s.strip() for s in re.split(r'(?<=[。！!？\?\n])', script) if s.strip()]
    if len(raw_sections) > 3:
        n = len(raw_sections)
        sections = [" ".join(raw_sections[:n//2]), " ".join(raw_sections[n//2:])]
    else:
        sections = raw_sections

    temp_dir = os.path.join(work_dir, "temp_audio")
    os.makedirs(temp_dir, exist_ok=True)
    
    audio_clips = []
    curr = 0
    for i, txt in enumerate(sections):
        a_path = os.path.join(temp_dir, f"s_{i}.mp3")
        await generate_speech(txt, a_path, voice=voice)
        clip = AudioFileClip(a_path)
        audio_clips.append(clip.set_start(curr))
        curr += clip.duration
    
    # 修正：末尾のチラつきを防ぐため、durationを音声の合計時間に厳密に合わせる
    duration = min(curr, 15.0) 
    final_audio_content = CompositeAudioClip(audio_clips)
    
    bg_clips_to_close = []
    if asset_type == "video" and asset_path:
        path_list = asset_path if isinstance(asset_path, list) else [asset_path]
        processed_clips = []
        
        for p_path in path_list[:3]:
            try:
                c_raw = VideoFileClip(p_path).without_audio()
                bg_clips_to_close.append(c_raw)
                
                # 1. 縦横比を維持したまま、完全に「1080x1920」にリサイズおよび中央クロップ
                c_resized = c_raw.resize(height=1920)
                if c_resized.w < 1080:
                    c_resized = c_resized.resize(width=1080)
                c_cropped = c_resized.crop(x_center=c_resized.w/2, y_center=c_resized.h/2, width=1080, height=1920)
                bg_clips_to_close.extend([c_resized, c_cropped])
                
                # 2. 5秒間切り出し（足らない場合はループ）
                c_sub = c_cropped.subclip(0, min(5.0, c_cropped.duration)) if c_cropped.duration >= 5.0 else c_cropped.fx(vfx.loop, duration=5.0)
                bg_clips_to_close.append(c_sub)
                
                # 3. 軽量なズームインと色調補正（彩度・コントラスト微調整）および左右反転
                c_zoomed = c_sub.resize(lambda t: 1.0 + 0.03 * t)
                c_processed = c_zoomed.fx(vfx.colorx, 1.08).fx(vfx.mirror_x)
                bg_clips_to_close.extend([c_zoomed, c_processed])
                
                processed_clips.append(c_processed)
            except Exception as clip_err:
                print(f"[WARN] Failed to process clip {p_path}: {clip_err}")
                
        if processed_clips:
            bg_concat = concatenate_videoclips(processed_clips, method="compose")
            bg_clips_to_close.append(bg_concat)
            bg = bg_concat.fx(vfx.loop, duration=duration) if bg_concat.duration < duration else bg_concat.subclip(0, duration)
        else:
            bg = ColorClip(size=(1080, 1920), color=(30, 30, 30)).set_duration(duration)
    else:
        bg = ColorClip(size=(1080, 1920), color=(30, 30, 30)).set_duration(duration)

    subs = []
    t_curr = 0
    for i, txt in enumerate(sections):
        dur = audio_clips[i].duration
        # 字幕の表示時間も厳密に管理
        if t_curr + dur > duration:
            dur = duration - t_curr
        if dur <= 0: break
        
        img = create_boxed_text_image(txt)
        img_p = os.path.join(temp_dir, f"t_{i}.png")
        img.save(img_p)
        subs.append(ImageClip(img_p).set_start(t_curr).set_duration(dur))
        t_curr += dur

    final_audio = final_audio_content
    if bgm_path and os.path.exists(bgm_path):
        try:
            # BGMも動画の長さに合わせる
            bgm = AudioFileClip(bgm_path).volumex(0.15).fx(afx.audio_loop, duration=duration)
            final_audio = CompositeAudioClip([final_audio_content.volumex(1.0), bgm])
        except Exception as e:
            print(f"BGM loading failed: {e}")

    try:
        video = CompositeVideoClip([bg] + subs).set_audio(final_audio).set_duration(duration)
        video.write_videofile(output_filename, fps=30, codec="libx264", audio_codec="aac", ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "faststart"])
        
        # クリップの解放 (Windowsでのファイルロック対策)
        video.close()
        bg.close()
        for c in bg_clips_to_close:
            try:
                c.close()
            except Exception:
                pass
        for s in subs:
            s.close()
        final_audio.close()
        for a in audio_clips:
            a.close()
            
        return output_filename, True
    except Exception as e:
        print(f"Video assembly failed: {e}")
        return None, False
