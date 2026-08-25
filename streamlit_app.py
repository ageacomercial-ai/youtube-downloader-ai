import streamlit as st
import requests
import os
import tempfile
import re

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

COBALT_API = "https://api.cobalt.tools"


def get_video_info(url):
    try:
        resp = requests.post(
            f"{COBALT_API}/",
            json={"url": url},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        data = resp.json()
        return data
    except Exception as e:
        return {"error": str(e)}


def download_with_cobalt(url, download_type, quality):
    payload = {"url": url}

    if download_type == "Vídeo (MP4)":
        payload["videoQuality"] = quality.replace("p", "") if "p" in quality else "1080"
        payload["filenameStyle"] = "pretty"
    elif download_type == "Áudio (MP3)":
        payload["downloadMode"] = "audio"
        payload["audioFormat"] = "mp3"
    elif download_type == "Áudio (M4A)":
        payload["downloadMode"] = "audio"
        payload["audioFormat"] = "m4a"

    resp = requests.post(
        f"{COBALT_API}/",
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=120,
    )

    if resp.status_code == 200:
        data = resp.json()
        if "url" in data:
            file_url = data["url"]
            filename = data.get("filename", "download")
            file_resp = requests.get(file_url, timeout=120, stream=True)
            if file_resp.status_code == 200:
                return file_resp.content, filename
        return None, data.get("error", "Erro desconhecido")
    else:
        try:
            err = resp.json()
            return None, err.get("error", f"HTTP {resp.status_code}")
        except:
            return None, f"HTTP {resp.status_code}"


def get_video_info_fallback(url):
    try:
        from yt_dlp import YoutubeDL
        ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", ""),
            "channel": info.get("channel", info.get("uploader", "")),
            "thumbnail": info.get("thumbnail", ""),
            "duration_string": info.get("duration_string", ""),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
        }
    except:
        return None


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def is_youtube_url(url):
    patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=',
        r'(https?://)?youtu\.be/',
        r'(https?://)?(www\.)?youtube\.com/playlist\?list=',
        r'(https?://)?(www\.)?youtube\.com/shorts/',
    ]
    return any(re.search(p, url) for p in patterns)


tab_single, tab_playlist = st.tabs(["🎬 Baixar Vídeo", "📋 Baixar Playlist"])

with tab_single:
    url = st.text_input(
        "Cole o link do vídeo do YouTube:",
        placeholder="https://www.youtube.com/watch?v=... ou https://youtu.be/..."
    )

    if url:
        if not is_youtube_url(url):
            st.error("Link inválido. Cole um link do YouTube.")
        else:
            try:
                info = get_video_info_fallback(url)

                if info:
                    col_thumb, col_info = st.columns([1, 2])
                    with col_thumb:
                        if info.get("thumbnail"):
                            st.image(info["thumbnail"], use_container_width=True)
                    with col_info:
                        st.subheader(info.get("title", "Sem título"))
                        st.caption(f"Canal: {info.get('channel', 'N/A')}")
                        st.caption(f"Duração: {info.get('duration_string', 'N/A')}")
                        if info.get("view_count"):
                            st.caption(f"Views: {info['view_count']:,}")
                        if info.get("like_count"):
                            st.caption(f"Likes: {info['like_count']:,}")

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
                            "1080p",
                            "720p",
                            "480p",
                            "360p"
                        ])
                    else:
                        quality = "N/A"

                if st.button("⬇️ Baixar", type="primary", use_container_width=True):
                    with st.spinner("Baixando via cobalt..."):
                        file_data, filename_or_error = download_with_cobalt(url, download_type, quality)

                        if file_data:
                            st.success("Download concluído!")

                            ext = ".mp4" if "Vídeo" in download_type else (".mp3" if "MP3" in download_type else ".m4a")
                            mime = "video/mp4" if "Vídeo" in download_type else "audio/mpeg"

                            safe_title = "".join(c for c in (info.get("title", "video") if info else "video") if c.isalnum() or c in ' -_').strip()[:80]
                            if not safe_title:
                                safe_title = "video"

                            st.download_button(
                                f"📥 Baixar {safe_title}{ext}",
                                data=file_data,
                                file_name=f"{safe_title}{ext}",
                                mime=mime,
                                use_container_width=True
                            )
                        else:
                            st.error(f"Erro: {filename_or_error}")

            except Exception as e:
                st.error(f"Erro: {e}")

with tab_playlist:
    st.info("A API do cobalt não suporta playlists. Use a aba individual para baixar vídeo por vídeo.")

    playlist_url = st.text_input(
        "Cole o link da playlist (extrai os links individuais):",
        placeholder="https://www.youtube.com/playlist?list=...",
        key="playlist_input"
    )

    if playlist_url:
        try:
            from yt_dlp import YoutubeDL
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)

            entries = playlist_info.get('entries', [])
            st.subheader(f"📋 {playlist_info.get('title', 'Playlist')}")
            st.caption(f"Total: {len(entries)} vídeos")

            for i, entry in enumerate(entries[:50], 1):
                title = entry.get('title', f'Vídeo {i}')
                vid_id = entry.get('id', '')
                vid_url = f"https://www.youtube.com/watch?v={vid_id}"
                with st.expander(f"{i}. {title}"):
                    st.code(vid_url)
                    dl_type = st.selectbox("Formato:", ["Vídeo (MP4)", "Áudio (MP3)"], key=f"pl_type_{i}")
                    if st.button(f"⬇️ Baixar {i}", key=f"pl_dl_{i}"):
                        with st.spinner(f"Baixando {title}..."):
                            file_data, result = download_with_cobalt(vid_url, dl_type, "720p")
                            if file_data:
                                ext = ".mp4" if "Vídeo" in dl_type else ".mp3"
                                mime = "video/mp4" if "Vídeo" in dl_type else "audio/mpeg"
                                safe = "".join(c for c in title if c.isalnum() or c in ' -_').strip()[:80]
                                st.download_button(
                                    f"📥 Baixar {safe}{ext}",
                                    data=file_data,
                                    file_name=f"{safe}{ext}",
                                    mime=mime,
                                    key=f"pl_dl_btn_{i}"
                                )
                            else:
                                st.error(f"Erro: {result}")

        except Exception as e:
            st.error(f"Erro ao carregar playlist: {e}")

with st.sidebar:
    st.header("⚙️ Configurações")
    st.markdown("---")
    st.markdown("### ⬇️ YouTube Downloader")
    st.markdown("**100% Gratuito & Open Source**")
    st.markdown("---")
    st.markdown("#### Tecnologias:")
    st.markdown("- **API:** cobalt.tools")
    st.markdown("- **Interface:** Streamlit")
    st.markdown("---")
    st.markdown("#### Como usar:")
    st.markdown("1. Cole o link do vídeo")
    st.markdown("2. Escolha formato e qualidade")
    st.markdown("3. Clique em Baixar")
    st.markdown("---")
    st.markdown("#### Formatos:")
    st.markdown("- 🎬 MP4 (vídeo)")
    st.markdown("- 🎵 MP3, M4A (áudio)")

st.divider()
st.markdown("""
<div style="text-align:center; color:#888; padding:1rem;">
    <p>Powered by <a href="https://cobalt.tools" target="_blank">cobalt.tools</a> — open source</p>
    <p>Sem cadastro. Sem limites. Sem propagandas.</p>
</div>
""", unsafe_allow_html=True)
