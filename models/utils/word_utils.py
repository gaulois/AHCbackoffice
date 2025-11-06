import io
import tempfile
from docx import Document
from docx.shared import Inches

def add_qr_to_word(input_file_stream, qr_bytes, client_id):
    """
    Insère un QR code en haut à droite d’un document Word (.docx)
    et renvoie un flux binaire prêt à être uploadé dans MinIO.
    """
    # Crée un fichier temporaire pour sauvegarder le Word original
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        tmp_file.write(input_file_stream.read())
        tmp_file_path = tmp_file.name

    # Ouvre le document Word
    doc = Document(tmp_file_path)

    # Crée une section si nécessaire (utile pour forcer le QR en haut)
    section = doc.sections[0]
    header = section.header
    paragraph = header.paragraphs[0] if header.paragraphs else header.add_paragraph()

    # Crée une image temporaire du QR
    qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_temp.write(qr_bytes.getvalue())
    qr_temp.close()

    # Ajoute le QR dans l'en-tête du document (toujours visible en haut à droite)
    run = paragraph.add_run()
    run.add_picture(qr_temp.name, width=Inches(1.2))

    # Aligne le QR à droite
    paragraph.alignment = 2  # 0=left, 1=center, 2=right

    # Sauvegarde le nouveau document dans un flux mémoire
    output_stream = io.BytesIO()
    doc.save(output_stream)
    output_stream.seek(0)

    return output_stream