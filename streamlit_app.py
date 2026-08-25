import streamlit as st
import os
import io
import tempfile
import asyncio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, TextClip, ColorClip,
    CompositeAudioClip
)
from moviepy.video.fx.all import resize, fadein, fadeout

st.set_page_config(
    page_title="YouTube Video Creator",
    page_icon="🎬",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a0a2e 0%, #1a0a3e 50%, #0a0a2e 100%);
    }
    .main-title {
        text-align: center; color: #ff6666; font-size: 2.5em;
        font-weight: bold; margin-bottom: 0;
        text-shadow: 0 0 20px rgba(255,102,102,0.5);
    }
    .subtitle {
        text-align: center; color: #888; font-size: 1.1em; margin-top: -10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🎬 YouTube Video Creator</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Crie vídeos para YouTube com imagens + narração — 100% Gratuito</p>', unsafe_allow_html=True)

VOICES = {
    "Português BR - Feminino": "pt-BR-FranciscaNeural",
    "Português BR - Masculino": "pt-BR-AntonioNeural",
    "Inglês US - Feminino": "en-US-JennyNeural",
    "Inglês US - Masculino": "en-US-GuyNeural",
    "Espanhol - Feminino": "es-ES-ElviraNeural",
    "Espanhol - Masculino": "es-ES-AlvaroNeural",
    "Francês - Feminino": "fr-FR-DeniseNeural",
    "Francês - Masculino": "fr-FR-HenriNeural",
}

RESOLUTIONS = {
    "1080p (1920x1080)": (1920, 1080),
    "720p (1280x720)": (1280, 720),
    "4K (3840x2160)": (3840, 2160),
    "Vertical 1080p (1080x1920)": (1080, 1920),
    "Shorts (1080x1920)": (1080, 1920),
}


def generate_narration(text, voice, rate, output_path):
    async def _gen():
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
    asyncio.run(_gen())


def prepare_image(image_bytes, target_w, target_h):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        new_h = target_h
        new_w = int(new_h * img_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return np.array(img)


def add_text_overlay(img_array, text, position="bottom", font_size=60, color="white"):
    if not text.strip():
        return img_array

    img = Image.fromarray(img_array)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    if position == "bottom":
        x = (img.width - text_w) // 2
        y = img.height - text_h - 40
    elif position == "top":
        x = (img.width - text_w) // 2
        y = 40
    else:
        x = (img.width - text_w) // 2
        y = (img.height - text_h) // 2

    for offset in range(3):
        draw.text((x-1, y-1), text, fill="black", font=font)
        draw.text((x+1, y-1), text, fill="black", font=font)
        draw.text((x-1, y+1), text, fill="black", font=font)
        draw.text((x+1, y+1), text, fill="black", font=font)

    draw.text((x, y), text, fill=color, font=font)
    return np.array(img)


def ken_burns(img_array, duration, zoom_start=1.0, zoom_end=1.15, direction="in"):
    h, w = img_array.shape[:2]
    frames = int(duration * 24)
    clips = []

    for i in range(frames):
        progress = i / max(frames - 1, 1)
        if direction == "in":
            zoom = zoom_start + (zoom_end - zoom_start) * progress
        else:
            zoom = zoom_end - (zoom_end - zoom_start) * progress

        new_w = int(w * zoom)
        new_h = int(h * zoom)

        img_pil = Image.fromarray(img_array)
        img_resized = img_pil.resize((new_w, new_h), Image.LANCZOS)

        left = (new_w - w) // 2
        top = (new_h - h) // 2
        frame = np.array(img_resized.crop((left, top, left + w, top + h)))
        clips.append(frame)

    return clips


def create_video(
    images_data, slide_texts, narration_texts, narration_config,
    resolution, slide_duration, transition_duration, enable_ken_burns,
    enable_text_overlay, text_position, bg_music_bytes, bg_music_volume,
    output_path
):
    target_w, target_h = resolution
    fps = 24
    all_clips = []

    for i, (img_bytes, slide_text, narr_text) in enumerate(zip(images_data, slide_texts, narration_texts)):
        prepared = prepare_image(img_bytes, target_w, target_h)

        if enable_text_overlay and slide_text.strip():
            prepared = add_text_overlay(prepared, slide_text, text_position, font_size=max(40, target_h // 20))

        audio_path = None
        clip_duration = slide_duration

        if narr_text.strip():
            audio_path = os.path.join(tempfile.gettempdir(), f"narr_{i}.mp3")
            rate = narration_config.get("rate", "+0%")
            voice = narration_config.get("voice", "pt-BR-FranciscaNeural")
            generate_narration(narr_text, voice, rate, audio_path)
            audio_clip = AudioFileClip(audio_path)
            clip_duration = max(slide_duration, audio_clip.duration + 1)

        if enable_ken_burns:
            direction = "in" if i % 2 == 0 else "out"
            kb_frames = ken_burns(prepared, clip_duration, direction=direction)
            def make_frame(t, frames=kb_frames, dur=clip_duration):
                idx = min(int(t / dur * len(frames)), len(frames) - 1)
                return frames[idx]
            video_clip = ImageClip(prepared).set_duration(clip_duration)
        else:
            video_clip = ImageClip(prepared).set_duration(clip_duration)

        video_clip = video_clip.set_fps(fps)

        if i > 0 and transition_duration > 0:
            video_clip = fadein(video_clip, transition_duration)

        if audio_path and os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            video_clip = video_clip.set_audio(audio_clip)

        all_clips.append(video_clip)

    final = concatenate_videoclips(all_clips, method="compose")

    if bg_music_bytes:
        music_path = os.path.join(tempfile.gettempdir(), "bg_music.mp3")
        with open(music_path, "wb") as f:
            f.write(bg_music_bytes)
        try:
            music = AudioFileClip(music_path)
            if music.duration > final.duration:
                music = music.subclip(0, final.duration)
            music = music.volumex(bg_music_volume)

            if final.audio:
                mixed = CompositeAudioClip([final.audio, music])
                final = final.set_audio(mixed)
            else:
                final = final.set_audio(music)
        except:
            pass

    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )

    for clip in all_clips:
        clip.close()
    final.close()


st.divider()

tab_config, tab_slide, tab_narr = st.tabs(["⚙️ Configurações", "🖼️ Slides", "🎤 Narração"])

with tab_config:
    col_res, col_timing = st.columns(2)

    with col_res:
        res_label = st.selectbox("Resolução:", list(RESOLUTIONS.keys()), index=0)
        resolution = RESOLUTIONS[res_label]

    with col_timing:
        slide_duration = st.slider("Duração por slide (seg):", 3, 30, 5)
        transition_duration = st.slider("Duração da transição (seg):", 0, 3, 1)

    enable_ken_burns = st.checkbox("Efeito Ken Burns (zoom suave)", value=True)
    enable_text_overlay = st.checkbox("Mostrar texto sobre imagem", value=True)
    text_position = st.selectbox("Posição do texto:", ["bottom", "top", "center"])

    st.divider()
    st.subheader("🎵 Música de Fundo (opcional)")
    bg_music = st.file_uploader("Upload música (MP3, WAV):", type=["mp3", "wav"], key="bg_music")
    bg_music_volume = st.slider("Volume da música:", 0.0, 1.0, 0.15, 0.05)

with tab_slide:
    st.subheader("Upload de Imagens")
    uploaded_images = st.file_uploader(
        "Envie as imagens (arraste para reordenar):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True
    )

    slide_texts = []
    if uploaded_images:
        st.info(f"{len(uploaded_images)} imagem(ns) carregada(s)")
        for i, img in enumerate(uploaded_images):
            img.seek(0)
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(img, width=150, caption=f"Slide {i+1}")
            with cols[1]:
                txt = st.text_input(
                    f"Texto do slide {i+1}:",
                    placeholder="Texto opcional sobre a imagem",
                    key=f"slide_text_{i}"
                )
                slide_texts.append(txt)

with tab_narr:
    st.subheader("Narração")
    voice_name = st.selectbox("Voz:", list(VOICES.keys()), index=0)
    narr_rate = st.slider("Velocidade da narração:", -50, 50, 0, format="%+d%%")

    narration_texts = []
    if uploaded_images:
        for i in range(len(uploaded_images)):
            narr = st.text_area(
                f"Narração do slide {i+1}:",
                placeholder=f"Texto que será narrado no slide {i+1}...",
                height=80,
                key=f"narr_{i}"
            )
            narration_texts.append(narr)

st.divider()

if st.button("🎬 Gerar Vídeo", type="primary", use_container_width=True):
    if not uploaded_images:
        st.error("Envie pelo menos uma imagem!")
    else:
        images_data = []
        for img in uploaded_images:
            img.seek(0)
            images_data.append(img.read())

        narration_config = {
            "voice": VOICES[voice_name],
            "rate": f"{narr_rate:+d}%",
        }

        bg_music_bytes = None
        if bg_music:
            bg_music.seek(0)
            bg_music_bytes = bg_music.read()

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            output_path = tmp.name

        progress = st.progress(0, text="Preparando...")
        progress.progress(10, text="Gerando narrações...")

        try:
            create_video(
                images_data=images_data,
                slide_texts=slide_texts,
                narration_texts=narration_texts,
                narration_config=narration_config,
                resolution=resolution,
                slide_duration=slide_duration,
                transition_duration=transition_duration,
                enable_ken_burns=enable_ken_burns,
                enable_text_overlay=enable_text_overlay,
                text_position=text_position,
                bg_music_bytes=bg_music_bytes,
                bg_music_volume=bg_music_volume,
                output_path=output_path,
            )

            progress.progress(100, text="Concluído!")

            file_size = os.path.getsize(output_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if file_size < 1024.0:
                    size_str = f"{file_size:.1f} {unit}"
                    break
                file_size /= 1024.0

            st.success(f"Vídeo gerado com sucesso! Tamanho: {size_str}")

            with open(output_path, "rb") as f:
                video_data = f.read()

            st.video(video_data)

            st.download_button(
                "📥 Baixar Vídeo MP4",
                data=video_data,
                file_name="meu_video_youtube.mp4",
                mime="video/mp4",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Erro ao gerar vídeo: {e}")
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

with st.sidebar:
    st.header("🎬 YouTube Video Creator")
    st.markdown("---")
    st.markdown("**100% Gratuito & Open Source**")
    st.markdown("---")
    st.markdown("#### Funcionalidades:")
    st.markdown("- 🖼️ Múltiplas imagens")
    st.markdown("- 🎤 Narração neural (30 vozes)")
    st.markdown("- 🎵 Música de fundo")
    st.markdown("- 🎞️ Efeito Ken Burns")
    st.markdown("- ✍️ Texto sobre imagens")
    st.markdown("- 📐 Resolução até 4K")
    st.markdown("- 📱 Vertical (Shorts)")
    st.markdown("---")
    st.markdown("#### Como usar:")
    st.markdown("1. Configure resolução e tempo")
    st.markdown("2. Envie as imagens")
    st.markdown("3. Escreva textos e narrações")
    st.markdown("4. Clique em Gerar Vídeo")
    st.markdown("---")
    st.markdown("#### Tecnologias:")
    st.markdown("- **Vídeo:** MoviePy + FFmpeg")
    st.markdown("- **Voz:** Edge TTS (Microsoft)")
    st.markdown("- **Interface:** Streamlit")
    st.markdown("---")
    st.markdown("#### Dicas YouTube:")
    st.markdown("- Use 16:9 (1080p) para vídeos normais")
    st.markdown("- Use 9:16 (1080x1920) para Shorts")
    st.markdown("- 5-10 slides = vídeo de 1-2 min")

st.divider()
st.markdown("""
<div style="text-align:center; color:#888; padding:1rem;">
    <p>🎬 Imagens + 🎤 Voz Neural + 🎵 Música = 📺 Vídeo YouTube</p>
    <p>Tudo gratuito. Sem marca d'água. Sem cadastro.</p>
</div>
""", unsafe_allow_html=True)
