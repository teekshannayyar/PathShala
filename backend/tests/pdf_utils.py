"""Build tiny but valid PDFs by hand, so tests need no PDF-writing dependency."""


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines: list[str]) -> bytes:
    """Return a one-page PDF showing `lines` in Helvetica (empty list: blank page).

    The text is real, extractable text, so pdfplumber reads it back.
    """
    content_ops = []
    if lines:
        content_ops.append("BT /F1 11 Tf 14 TL 50 780 Td")
        for line in lines:
            content_ops.append(f"({_escape(line)}) Tj T*")
        content_ops.append("ET")
    stream = "\n".join(content_ops).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


SAMPLE_LINES = [
    "Photosynthesis is the process plants use to turn light into chemical energy.",
    "It takes place in the chloroplasts, which contain the green pigment chlorophyll.",
    "Chlorophyll absorbs red and blue light and reflects green light.",
    "The light reactions split water and release oxygen as a by-product.",
    "The Calvin cycle uses carbon dioxide to build glucose molecules.",
    "Mitochondria later break glucose down during cellular respiration.",
    "Cellular respiration releases energy that the cell stores as ATP.",
]


if __name__ == "__main__":  # regenerate tests/fixtures/sample.pdf
    import pathlib

    target = pathlib.Path(__file__).parent / "fixtures" / "sample.pdf"
    target.write_bytes(make_pdf(SAMPLE_LINES))
    print(f"wrote {target}")
