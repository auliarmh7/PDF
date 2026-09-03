import streamlit as st
from pypdf import PdfReader, PdfWriter
import subprocess
import tempfile
import os
import shutil


# ============================================================
# KONFIGURASI STREAMLIT
# ============================================================

st.set_page_config(
    page_title="PDF Tool",
    page_icon="📄",
    layout="wide"
)


# ============================================================
# JUDUL
# ============================================================

st.title("📄 PDF Tool")
st.write("Split, Merge, dan Compress PDF")


# ============================================================
# FUNGSI MENCARI GHOSTSCRIPT
# ============================================================

def find_ghostscript():
    """
    Mencari Ghostscript 64-bit.
    Prioritas:
    1. PATH Windows
    2. C:\\Program Files\\gs\\...\\bin\\gswin64c.exe
    """

    # 1. Cek PATH
    gs = shutil.which("gswin64c")

    if gs:
        return gs

    # 2. Cek lokasi instalasi umum Ghostscript
    base_path = r"C:\Program Files\gs"

    if os.path.exists(base_path):
        possible_paths = []

        for folder in os.listdir(base_path):
            bin_path = os.path.join(
                base_path,
                folder,
                "bin",
                "gswin64c.exe"
            )
            possible_paths.append(bin_path)

        # Urutkan supaya versi terbaru biasanya diperiksa lebih dulu
        possible_paths.sort(reverse=True)

        for path in possible_paths:
            if os.path.isfile(path):
                return path

    return None


# ============================================================
# FUNGSI FORMAT UKURAN FILE
# ============================================================

def format_size(size_bytes):
    """Mengubah ukuran byte menjadi B, KB, MB, atau GB."""

    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"

    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"

    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# ============================================================
# FUNGSI MERGE PDF
# ============================================================

def merge_pdf(files):

    writer = PdfWriter()

    for uploaded_file in files:
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)

        for page in reader.pages:
            writer.add_page(page)

    output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )
    output.close()

    with open(output.name, "wb") as f:
        writer.write(f)

    return output.name


# ============================================================
# FUNGSI SPLIT PDF
# ============================================================

def split_pdf(uploaded_file, start_page, end_page):

    uploaded_file.seek(0)
    reader = PdfReader(uploaded_file)
    writer = PdfWriter()

    total_pages = len(reader.pages)

    start_index = start_page - 1
    end_index = min(end_page, total_pages)

    for i in range(start_index, end_index):
        writer.add_page(reader.pages[i])

    output = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )
    output.close()

    with open(output.name, "wb") as f:
        writer.write(f)

    return output.name


# ============================================================
# FUNGSI COMPRESS PDF
# KHUSUS UNTUK PDF HASIL SCAN
# ============================================================

def compress_pdf(input_path, output_path, quality):

    ghostscript = find_ghostscript()

    if ghostscript is None:
        raise FileNotFoundError(
            "Ghostscript tidak ditemukan. "
            "Pastikan Ghostscript sudah terinstall."
        )

    # --------------------------------------------------------
    # Preset compression
    #
    # color_dpi = resolusi gambar warna
    # gray_dpi  = resolusi gambar grayscale
    # mono_dpi  = resolusi gambar hitam-putih
    # jpeg_quality = kualitas JPEG
    # --------------------------------------------------------

    settings = {

        "Kompresi Maksimal": {
            "color_dpi": 100,
            "gray_dpi": 100,
            "mono_dpi": 150,
            "jpeg_quality": 45
        },

        "Dokumen Kantor": {
            "color_dpi": 120,
            "gray_dpi": 120,
            "mono_dpi": 180,
            "jpeg_quality": 55
        },

        "Seimbang": {
            "color_dpi": 150,
            "gray_dpi": 150,
            "mono_dpi": 200,
            "jpeg_quality": 65
        },

        "Kualitas Tinggi": {
            "color_dpi": 200,
            "gray_dpi": 200,
            "mono_dpi": 250,
            "jpeg_quality": 75
        }
    }

    if quality not in settings:
        quality = "Seimbang"

    config = settings[quality]

    # --------------------------------------------------------
    # Ghostscript command
    #
    # Perbaikan penting untuk PDF scan:
    # - DownsampleThreshold=1.0
    #   agar gambar benar-benar diturunkan resolusinya
    #   ketika resolusi sumber lebih tinggi dari target.
    #
    # - PassThroughJPEGImages=false
    #   agar JPEG dari scanner tidak hanya dilewatkan begitu saja,
    #   tetapi diproses ulang sesuai kualitas yang dipilih.
    #
    # - DCTEncode
    #   menggunakan JPEG compression untuk gambar warna/grayscale.
    #
    # - CCITTFaxEncode
    #   sangat efisien untuk scan hitam-putih 1-bit.
    # --------------------------------------------------------

    command = [
        ghostscript,

        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",

        "-dNOPAUSE",
        "-dBATCH",
        "-dSAFER",

        # Optimasi
        "-dOptimize=true",
        "-dDetectDuplicateImages=true",

        # Jangan sekadar meneruskan JPEG dari PDF lama.
        # Paksa Ghostscript memproses ulang JPEG.
        "-dPassThroughJPEGImages=false",

        # ====================================================
        # COLOR IMAGE
        # ====================================================

        "-dDownsampleColorImages=true",
        "-dColorImageDownsampleType=/Bicubic",
        f"-dColorImageResolution={config['color_dpi']}",
        "-dColorImageDownsampleThreshold=1.0",

        "-dAutoFilterColorImages=false",
        "-dColorImageFilter=/DCTEncode",

        # ====================================================
        # GRAYSCALE IMAGE
        # ====================================================

        "-dDownsampleGrayImages=true",
        "-dGrayImageDownsampleType=/Bicubic",
        f"-dGrayImageResolution={config['gray_dpi']}",
        "-dGrayImageDownsampleThreshold=1.0",

        "-dAutoFilterGrayImages=false",
        "-dGrayImageFilter=/DCTEncode",

        # ====================================================
        # MONOCHROME / BLACK-WHITE
        # ====================================================

        "-dDownsampleMonoImages=true",
        "-dMonoImageDownsampleType=/Subsample",
        f"-dMonoImageResolution={config['mono_dpi']}",
        "-dMonoImageDownsampleThreshold=1.0",

        "-dMonoImageFilter=/CCITTFaxEncode",

        # Kualitas JPEG
        f"-dJPEGQ={config['jpeg_quality']}",

        # Output
        f"-sOutputFile={output_path}",

        input_path
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:

        error_message = result.stderr.strip()

        if not error_message:
            error_message = result.stdout.strip()

        raise RuntimeError(
            "Ghostscript gagal melakukan compression:\n\n"
            + error_message
        )

    if not os.path.isfile(output_path):
        raise RuntimeError(
            "File hasil compression tidak berhasil dibuat."
        )

    if os.path.getsize(output_path) == 0:
        raise RuntimeError(
            "File hasil compression berukuran 0 KB."
        )


# ============================================================
# FUNGSI COMPRESS + PILIH FILE TERKECIL
# ============================================================

def compress_and_get_result(input_path, output_path, quality):
    """
    Compress PDF.
    Jika hasil Ghostscript justru lebih besar dari file asli,
    hasil asli akan digunakan sebagai fallback.
    """

    original_size = os.path.getsize(input_path)

    compress_pdf(
        input_path,
        output_path,
        quality
    )

    compressed_size = os.path.getsize(output_path)

    # Jika hasil compression lebih besar,
    # jangan berikan file yang lebih besar kepada pengguna.
    if compressed_size >= original_size:

        os.remove(output_path)

        shutil.copy2(
            input_path,
            output_path
        )

        final_size = original_size
        actually_compressed = False

    else:

        final_size = compressed_size
        actually_compressed = True

    if original_size > 0:
        reduction = (
            (original_size - final_size)
            / original_size
            * 100
        )
    else:
        reduction = 0

    return {
        "original_size": original_size,
        "final_size": final_size,
        "reduction": reduction,
        "actually_compressed": actually_compressed
    }


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Pengaturan")

menu = st.sidebar.radio(
    "Pilih fitur",
    [
        "📄 Split PDF",
        "🔗 Merge PDF",
        "🗜️ Compress PDF",
        "🔗🗜️ Merge + Compress"
    ]
)


# ============================================================
# SPLIT PDF
# ============================================================

if menu == "📄 Split PDF":

    st.header("📄 Split PDF")

    uploaded_file = st.file_uploader(
        "Pilih file PDF",
        type=["pdf"],
        key="split"
    )

    if uploaded_file:

        try:

            reader = PdfReader(uploaded_file)
            total_pages = len(reader.pages)

            st.success(
                f"PDF memiliki {total_pages} halaman."
            )

            col1, col2 = st.columns(2)

            with col1:

                start_page = st.number_input(
                    "Halaman awal",
                    min_value=1,
                    max_value=total_pages,
                    value=1
                )

            with col2:

                end_page = st.number_input(
                    "Halaman akhir",
                    min_value=1,
                    max_value=total_pages,
                    value=total_pages
                )

            output_name = st.text_input(
                "Nama file hasil",
                "hasil_split.pdf"
            )

            if st.button(
                "📄 Pisahkan PDF",
                use_container_width=True
            ):

                if start_page > end_page:

                    st.error(
                        "Halaman awal tidak boleh lebih besar "
                        "dari halaman akhir."
                    )

                else:

                    try:

                        output_path = split_pdf(
                            uploaded_file,
                            start_page,
                            end_page
                        )

                        with open(
                            output_path,
                            "rb"
                        ) as f:

                            pdf_data = f.read()

                        st.success(
                            "PDF berhasil dipisahkan!"
                        )

                        st.download_button(
                            "⬇️ Download PDF",
                            data=pdf_data,
                            file_name=output_name,
                            mime="application/pdf",
                            use_container_width=True
                        )

                    except Exception as e:

                        st.error(
                            f"Terjadi kesalahan: {e}"
                        )

        except Exception as e:

            st.error(
                f"PDF tidak dapat dibaca: {e}"
            )


# ============================================================
# MERGE PDF
# ============================================================

elif menu == "🔗 Merge PDF":

    st.header("🔗 Merge PDF")

    uploaded_files = st.file_uploader(
        "Pilih beberapa file PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="merge"
    )

    if uploaded_files:

        st.subheader("File yang dipilih")

        total_size = 0

        for i, file in enumerate(uploaded_files):

            size_mb = (
                file.size
                / (1024 * 1024)
            )

            total_size += size_mb

            st.write(
                f"{i + 1}. **{file.name}** "
                f"— {size_mb:.2f} MB"
            )

        st.write(
            f"Total: **{total_size:.2f} MB**"
        )

        output_name = st.text_input(
            "Nama file hasil",
            "hasil_merge.pdf"
        )

        if st.button(
            "🔗 Gabungkan PDF",
            use_container_width=True
        ):

            try:

                output_path = merge_pdf(
                    uploaded_files
                )

                with open(
                    output_path,
                    "rb"
                ) as f:

                    pdf_data = f.read()

                st.success(
                    "PDF berhasil digabungkan!"
                )

                st.download_button(
                    "⬇️ Download PDF",
                    data=pdf_data,
                    file_name=output_name,
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:

                st.error(
                    f"Terjadi kesalahan: {e}"
                )


# ============================================================
# COMPRESS PDF
# ============================================================

elif menu == "🗜️ Compress PDF":

    st.header("🗜️ Compress PDF")

    st.caption(
        "Mode ini dioptimalkan untuk PDF hasil scan printer/scanner."
    )

    uploaded_file = st.file_uploader(
        "Pilih satu file PDF",
        type=["pdf"],
        key="compress"
    )

    quality = st.selectbox(
        "Kualitas Compression",
        [
            "Kompresi Maksimal",
            "Dokumen Kantor",
            "Seimbang",
            "Kualitas Tinggi"
        ],
        index=2
    )

    st.info(
        "Untuk dokumen hasil scan, mulai dari "
        "**Dokumen Kantor** atau **Seimbang**."
    )

    if uploaded_file:

        original_size_bytes = uploaded_file.size

        st.info(
            f"Ukuran awal: "
            f"**{format_size(original_size_bytes)}**"
        )

        output_name = st.text_input(
            "Nama file hasil",
            "hasil_compress.pdf"
        )

        if st.button(
            "🗜️ Compress PDF",
            use_container_width=True
        ):

            with tempfile.TemporaryDirectory() as temp_dir:

                input_path = os.path.join(
                    temp_dir,
                    "input.pdf"
                )

                output_path = os.path.join(
                    temp_dir,
                    "output.pdf"
                )

                with open(
                    input_path,
                    "wb"
                ) as f:

                    f.write(
                        uploaded_file.getbuffer()
                    )

                try:

                    with st.spinner(
                        "Sedang melakukan compression..."
                    ):

                        result = compress_and_get_result(
                            input_path,
                            output_path,
                            quality
                        )

                    with open(
                        output_path,
                        "rb"
                    ) as f:

                        pdf_data = f.read()

                    if result["actually_compressed"]:

                        st.success(
                            "PDF berhasil dikompres!"
                        )

                    else:

                        st.warning(
                            "Ghostscript tidak menghasilkan file "
                            "yang lebih kecil. File asli digunakan "
                            "agar hasil tidak menjadi lebih besar."
                        )

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Ukuran Awal",
                        format_size(
                            result["original_size"]
                        )
                    )

                    col2.metric(
                        "Ukuran Akhir",
                        format_size(
                            result["final_size"]
                        )
                    )

                    col3.metric(
                        "Pengurangan",
                        f"{result['reduction']:.1f}%"
                    )

                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_data,
                        file_name=output_name,
                        mime="application/pdf",
                        use_container_width=True
                    )

                except Exception as e:

                    st.error(
                        f"Gagal melakukan compress: {e}"
                    )


# ============================================================
# MERGE + COMPRESS
# ============================================================

else:

    st.header("🔗🗜️ Merge + Compress PDF")

    uploaded_files = st.file_uploader(
        "Pilih beberapa file PDF",
        type=["pdf"],
        accept_multiple_files=True,
        key="merge_compress"
    )

    quality = st.selectbox(
        "Kualitas kompresi",
        [
            "Kompresi Maksimal",
            "Dokumen Kantor",
            "Seimbang",
            "Kualitas Tinggi"
        ],
        index=1,
        key="merge_quality"
    )

    if uploaded_files:

        total_size_bytes = sum(
            file.size
            for file in uploaded_files
        )

        st.info(
            f"Total ukuran awal: "
            f"**{format_size(total_size_bytes)}**"
        )

        output_name = st.text_input(
            "Nama file hasil",
            "hasil_merge_compress.pdf"
        )

        if st.button(
            "🔗🗜️ Merge + Compress",
            use_container_width=True
        ):

            try:

                with tempfile.TemporaryDirectory() as temp_dir:

                    merged_path = os.path.join(
                        temp_dir,
                        "merged.pdf"
                    )

                    compressed_path = os.path.join(
                        temp_dir,
                        "compressed.pdf"
                    )

                    # ========================================
                    # MERGE
                    # ========================================

                    writer = PdfWriter()

                    for uploaded_file in uploaded_files:

                        uploaded_file.seek(0)

                        reader = PdfReader(
                            uploaded_file
                        )

                        for page in reader.pages:
                            writer.add_page(page)

                    with open(
                        merged_path,
                        "wb"
                    ) as f:

                        writer.write(f)

                    # ========================================
                    # COMPRESS
                    # ========================================

                    with st.spinner(
                        "Sedang merge dan compress..."
                    ):

                        result = compress_and_get_result(
                            merged_path,
                            compressed_path,
                            quality
                        )

                    # ========================================
                    # BACA HASIL
                    # ========================================

                    with open(
                        compressed_path,
                        "rb"
                    ) as f:

                        pdf_data = f.read()

                    # Ukuran dibandingkan dengan TOTAL FILE AWAL
                    final_size = len(pdf_data)

                    if final_size < total_size_bytes:

                        reduction = (
                            (total_size_bytes - final_size)
                            / total_size_bytes
                            * 100
                        )

                        st.success(
                            "PDF berhasil di-merge dan dikompres!"
                        )

                    else:

                        reduction = 0

                        st.warning(
                            "Hasil merge + compress tidak lebih kecil "
                            "dari total file awal."
                        )

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Ukuran Awal",
                        format_size(total_size_bytes)
                    )

                    col2.metric(
                        "Ukuran Akhir",
                        format_size(final_size)
                    )

                    col3.metric(
                        "Pengurangan",
                        f"{reduction:.1f}%"
                    )

                    st.download_button(
                        "⬇️ Download PDF",
                        data=pdf_data,
                        file_name=output_name,
                        mime="application/pdf",
                        use_container_width=True
                    )

            except Exception as e:

                st.error(
                    f"Terjadi kesalahan: {e}"
                )
