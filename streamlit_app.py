import streamlit as st
import yt_dlp
import os
import tempfile
from pathlib import Path

st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="⬇️",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a0a0a 0%, #2d0a0a 50%, #1a0a0a 100%);
    }
    .main-title {
        text-align: center; color: #ff4444; font-size: 2.5em;
        font-weight: bold; margin-bottom: 0;
        text-shadow: 0 0 20px rgba(255,68,68,0.5);
    }
    .subtitle {
        text-align: center; color: #888; font-size: 1.1em; margin-top: -10px;
    }
    div[data-testid="stDownloadButton"] button {
        background: #ff444422 !important; color: #ff4444 !important;
        border: 1px solid #ff444444 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">⬇️ YouTube Downloader</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Baixe vídeos e áudios do YouTube — 100% Gratuito</p>', unsafe_allow_html=True)


def get_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info


def format_size(size_bytes):
    if size_bytes is None:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def download_video(url, quality, download_type, output_path):
    base_opts = {
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/',
        },
        'extractor_args': {'youtube': {'player_client': ['ios', 'web', 'mweb']}},
    }

    if download_type == "Vídeo (MP4)":
        format_map = {
            "Melhor qualidade": 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            "1080p": 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best',
            "720p": 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best',
            "480p": 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best',
            "360p": 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best',
        }
        ydl_opts = {
            **base_opts,
            'format': format_map.get(quality, 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'),
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
        }
    else:
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3' if download_type == "Áudio (MP3)" else 'm4a',
                'preferredquality': '192',
            }],
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if download_type == "Áudio (MP3)":
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"
        elif download_type == "Áudio (M4A)":
            base, _ = os.path.splitext(filename)
            filename = base + ".m4a"
    return filename


tab_single, tab_playlist = st.tabs(["🎬 Baixar Vídeo", "📋 Baixar Playlist"])

with tab_single:
    url = st.text_input(
        "Cole o link do vídeo do YouTube:",
        placeholder="https://www.youtube.com/watch?v=..."
    )

    if url:
        try:
            info = get_video_info(url)

            col_thumb, col_info = st.columns([1, 2])

            with col_thumb:
                thumbnail = info.get('thumbnail', '')
                if thumbnail:
                    st.image(thumbnail, use_container_width=True)

            with col_info:
                st.subheader(info.get('title', 'Sem título'))
                st.caption(f"Canal: {info.get('channel', 'N/A')}")
                st.caption(f"Duração: {info.get('duration_string', 'N/A')}")
                st.caption(f"Views: {info.get('view_count', 0):,}")
                st.caption(f"Likes: {info.get('like_count', 0):,}")

            st.divider()

            col_type, col_quality = st.columns(2)

            with col_type:
                download_type = st.selectbox("Formato:", [
                    "Vídeo (MP4)",
                    "Áudio (MP3)",
                    "Áudio (M4A)",
                ])

            with col_quality:
                if "Vídeo" in download_type:
                    quality = st.selectbox("Qualidade:", [
                        "Melhor qualidade",
                        "1080p",
                        "720p",
                        "480p",
                        "360p"
                    ])
                else:
                    quality = "Melhor qualidade"

            if st.button("⬇️ Baixar", type="primary", use_container_width=True):
                with tempfile.TemporaryDirectory() as tmpdir:
                    with st.spinner("Baixando... Isso pode levar alguns minutos."):
                        try:
                            filename = download_video(url, quality, download_type, tmpdir)
                            files = os.listdir(tmpdir)
                            if not files:
                                st.error("Nenhum arquivo foi baixado.")
                            else:
                                filepath = os.path.join(tmpdir, files[0])
                                file_size = os.path.getsize(filepath)
                                st.success(f"Download concluído! Tamanho: {format_size(file_size)}")

                                with open(filepath, 'rb') as f:
                                    file_data = f.read()

                                ext = os.path.splitext(filepath)[1]
                                mime_map = {
                                    '.mp4': 'video/mp4',
                                    '.mp3': 'audio/mpeg',
                                    '.m4a': 'audio/mp4',
                                    '.webm': 'video/webm',
                                }
                                mime = mime_map.get(ext, 'application/octet-stream')
                                safe_title = "".join(c for c in info.get('title', 'video') if c.isalnum() or c in ' -_').strip()

                                st.download_button(
                                    f"📥 Baixar {safe_title}{ext}",
                                    data=file_data,
                                    file_name=f"{safe_title}{ext}",
                                    mime=mime,
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Erro ao baixar: {e}")

        except Exception as e:
            st.error(f"Erro ao obter informações: {e}")

with tab_playlist:
    playlist_url = st.text_input(
        "Cole o link da playlist do YouTube:",
        placeholder="https://www.youtube.com/playlist?list=..."
    )

    if playlist_url:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)

            st.subheader(f"📋 {playlist_info.get('title', 'Playlist')}")
            st.caption(f"Total de vídeos: {len(playlist_info.get('entries', []))}")

            entries = playlist_info.get('entries', [])
            for i, entry in enumerate(entries[:50], 1):
                title = entry.get('title', f'Vídeo {i}')
                with st.expander(f"{i}. {title}"):
                    vid_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                    st.code(vid_url)

            st.divider()

            playlist_dl_type = st.selectbox("Formato (playlist):", [
                "Vídeo (MP4)",
                "Áudio (MP3)"
            ], key="playlist_type")

            if st.button("⬇️ Baixar Playlist", type="primary", use_container_width=True):
                with tempfile.TemporaryDirectory() as tmpdir:
                    with st.spinner(f"Baixando {len(entries)} vídeos... Isso pode demorar."):
                        try:
                            if "Vídeo" in playlist_dl_type:
                                ydl_opts = {
                                    'format': 'best[ext=mp4]/best',
                                    'outtmpl': os.path.join(tmpdir, '%(playlist_index)s - %(title)s.%(ext)s'),
                                    'noplaylist': False,
                                }
                            else:
                                ydl_opts = {
                                    'format': 'bestaudio/best',
                                    'outtmpl': os.path.join(tmpdir, '%(playlist_index)s - %(title)s.%(ext)s'),
                                    'postprocessors': [{
                                        'key': 'FFmpegExtractAudio',
                                        'preferredcodec': 'mp3',
                                        'preferredquality': '192',
                                    }],
                                    'noplaylist': False,
                                }

                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([playlist_url])

                            files = sorted(os.listdir(tmpdir))
                            total_size = sum(os.path.getsize(os.path.join(tmpdir, f)) for f in files)

                            st.success(f"Playlist baixada! {len(files)} arquivos, {format_size(total_size)} total")

                            for f in files:
                                filepath = os.path.join(tmpdir, f)
                                with open(filepath, 'rb') as file:
                                    data = file.read()
                                ext = os.path.splitext(f)[1]
                                mime_map = {
                                    '.mp4': 'video/mp4',
                                    '.mp3': 'audio/mpeg',
                                    '.m4a': 'audio/mp4',
                                    '.webm': 'video/webm',
                                }
                                mime = mime_map.get(ext, 'application/octet-stream')
                                st.download_button(
                                    f"📥 {f}",
                                    data=data,
                                    file_name=f,
                                    mime=mime
                                )

                        except Exception as e:
                            st.error(f"Erro ao baixar playlist: {e}")

        except Exception as e:
            st.error(f"Erro ao carregar playlist: {e}")

with st.sidebar:
    st.header("⚙️ Configurações")
    st.markdown("---")
    st.markdown("### ⬇️ YouTube Downloader")
    st.markdown("**100% Gratuito & Open Source**")
    st.markdown("---")
    st.markdown("#### Tecnologias:")
    st.markdown("- **Downloader:** yt-dlp")
    st.markdown("- **Interface:** Streamlit")
    st.markdown("---")
    st.markdown("#### Como usar:")
    st.markdown("1. Cole o link do vídeo ou playlist")
    st.markdown("2. Escolha formato e qualidade")
    st.markdown("3. Clique em Baixar")
    st.markdown("---")
    st.markdown("#### Formatos suportados:")
    st.markdown("- 🎬 MP4 (vídeo)")
    st.markdown("- 🎵 MP3, M4A (áudio)")
    st.markdown("- 📋 Playlists completas")

st.divider()
st.markdown("""
<div style="text-align:center; color:#888; padding:1rem;">
    <p>Powered by <a href="https://github.com/yt-dlp/yt-dlp" target="_blank">yt-dlp</a> — open source</p>
    <p>Sem cadastro. Sem limites. Sem propagandas.</p>
</div>
""", unsafe_allow_html=True)
