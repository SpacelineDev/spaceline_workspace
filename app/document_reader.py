from __future__ import annotations

import csv
import io
import re
import posixpath
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_CHARS = 120_000
MAX_ZIP_ENTRIES = 2500
MAX_ZIP_EXPANDED_BYTES = 80 * 1024 * 1024
MAX_PDF_PAGES = 250

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".json", ".jsonl", ".ipynb", ".xml",
    ".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".py", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".sql", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".sh", ".ps1", ".bat", ".psm1", ".dockerfile",
    ".gitignore", ".env.example", ".vue", ".svelte", ".php", ".rb", ".swift", ".kt",
}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | {".csv", ".tsv", ".pdf", ".docx", ".xlsx", ".pptx"}
# Common project-control files are text even though they have no conventional suffix.
TEXT_FILENAMES = {
    "dockerfile", "containerfile", "makefile", "gnumakefile", "justfile", "procfile",
    "license", "notice", "authors", "contributing", "code_of_conduct",
    ".gitignore", ".dockerignore", ".gitattributes", ".editorconfig",
    ".prettierrc", ".prettierignore", ".eslintignore", ".watchmanconfig",
}
def path_extension(path: str | Path) -> str:
    target = Path(path)
    extension = target.suffix.lower()
    if extension:
        return extension
    return ".txt" if target.name.lower() in TEXT_FILENAMES else ""


def is_text_path(path: str | Path) -> bool:
    return path_extension(path) in (TEXT_EXTENSIONS | {".csv", ".tsv"})


def is_supported_path(path: str | Path) -> bool:
    return path_extension(path) in SUPPORTED_EXTENSIONS

_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def _is_protected_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    protected_dirs = {".git", ".ssh", ".aws", ".azure", ".gcloud", ".kube", ".docker", ".terraform", ".pulumi", ".auth", ".playwright"}
    exact = {
        ".npmrc", ".pypirc", ".netrc", ".dockercfg", ".git-credentials", ".pgpass", ".my.cnf",
        "credentials", "credentials.json", "auth.json", "cookies.json", "storage-state.json",
        "secret", "secrets", "secrets.json", "secret.json", "token.json", "oauth.json",
        "oauth_token.json", "service-account.json", "service_account.json", "id_rsa", "id_ed25519", "id_ecdsa",
        "id_dsa", "authorized_keys", "known_hosts", "terraform.tfstate", "terraform.tfvars",
    }
    return (
        any(part in protected_dirs for part in parts[:-1])
        or name in exact or name.startswith(".env") or name.endswith(".env") or ".env." in name
        or name.endswith((".pem", ".key", ".p8", ".p12", ".pfx", ".jks", ".keystore", ".tfstate", ".cookie"))
        or any(marker in name for marker in ("credential", "secret", "private_key", "privatekey", "serviceaccount", "firebase-adminsdk", "access_token", "refresh_token"))
    )


def redact_sensitive_text(content: str) -> tuple[str, int]:
    """Mask common credential assignments and recognizable tokens before cloud use."""
    value = str(content or "")
    redactions = 0

    def sub(pattern: str, replacement: str, flags: int = 0) -> None:
        nonlocal value, redactions
        value, count = re.subn(pattern, replacement, value, flags=flags)
        redactions += count

    # Match key/value settings in JSON, YAML, TOML, .env and code snippets.
    secret_name = (
        r"(?:api[_-]?key|openai_api_key|anthropic_api_key|gemini_api_key|"
        r"client[_-]?secret|secret(?:[_-]?key)?|access[_-]?token|refresh[_-]?token|"
        r"password|passwd|aws_secret_access_key|private[_-]?key|"
        r"service[_-]?account[_-]?key)"
    )
    sub(r"(?im)([\"']?\b" + secret_name + r"\b[\"']?\s*[:=]\s*[\"']?)([^\"'\s,;}\]]+)", r"\1[REDACTED]")
    # Private-key PEM blocks may span multiple lines.
    sub(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----", "[REDACTED PRIVATE KEY]")
    sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/-]{12,}=?", r"\1[REDACTED]")
    sub(r"(?i)([?&](?:api[_-]?key|key|token|access_token)=)[^&\s]+", r"\1[REDACTED]")
    for pattern in (
        r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b",
        r"\bAIza[A-Za-z0-9_-]{20,}\b",
        r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
        r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b",
        r"\bAKIA[0-9A-Z]{16}\b",
    ):
        sub(pattern, "[REDACTED TOKEN]")
    return value, redactions


def _clip(content: str) -> tuple[str, bool]:
    if len(content) <= MAX_EXTRACTED_CHARS:
        return content, False
    return content[:MAX_EXTRACTED_CHARS], True


def _safe_xml(data: bytes) -> ET.Element:
    # ElementTree does not resolve external entities; reject DTD declarations as
    # an additional guard before parsing untrusted office document XML.
    sample = data.upper()
    if b"<!DOCTYPE" in sample or b"<!ENTITY" in sample:
        raise ValueError("This document contains unsupported XML declarations.")
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        raise ValueError("This Office document is damaged or has invalid XML content.") from None


def _zip_members(path: Path) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise ValueError("This Office document is damaged or is not a valid Office file.") from None
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        archive.close()
        raise ValueError("This Office document contains too many internal parts to inspect safely.")
    if sum(item.file_size for item in infos) > MAX_ZIP_EXPANDED_BYTES:
        archive.close()
        raise ValueError("This Office document expands beyond the safe extraction limit.")
    for item in infos:
        internal = PurePosixPath(item.filename)
        if internal.is_absolute() or ".." in internal.parts:
            archive.close()
            raise ValueError("This Office document contains an unsafe internal file path.")
    return archive


def _read_xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    try:
        info = archive.getinfo(member)
        if info.file_size > 25 * 1024 * 1024:
            raise ValueError("A document part is too large to inspect safely.")
        return _safe_xml(archive.read(member))
    except KeyError:
        raise ValueError("This Office document is missing required content.") from None


def _docx(path: Path) -> tuple[str, dict[str, Any], list[str]]:
    warnings: list[str] = []
    chunks: list[str] = []
    with _zip_members(path) as archive:
        root = _read_xml(archive, "word/document.xml")
        body = root.find("w:body", _NS)
        if body is None:
            raise ValueError("This Word document has no readable body content.")
        for child in list(body):
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                text = "".join(node.text or "" for node in child.findall(".//w:t", _NS))
                if text.strip():
                    chunks.append(text)
            elif tag == "tbl":
                rows = []
                for row in child.findall("w:tr", _NS):
                    cells = []
                    for cell in row.findall("w:tc", _NS):
                        text = " ".join("".join(node.text or "" for node in para.findall(".//w:t", _NS))
                                        for para in cell.findall("w:p", _NS)).strip()
                        cells.append(text)
                    rows.append(" | ".join(cells))
                if rows:
                    chunks.append("[Table]\n" + "\n".join(rows) + "\n[/Table]")
        if not chunks:
            warnings.append("No extractable text was found. The document may contain only images or shapes.")
        try:
            footnotes = _read_xml(archive, "word/footnotes.xml")
            notes = ["".join(node.text or "" for node in item.findall(".//w:t", _NS))
                     for item in footnotes.findall("w:footnote", _NS)]
            notes = [note for note in notes if note.strip()]
            if notes:
                chunks.append("[Footnotes]\n" + "\n".join(notes))
        except ValueError:
            pass
    return "\n\n".join(chunks), {"kind": "document", "format": "DOCX"}, warnings


def _xlsx(path: Path) -> tuple[str, dict[str, Any], list[str]]:
    warnings: list[str] = []
    sections: list[str] = []
    formula_seen = False
    with _zip_members(path) as archive:
        workbook = _read_xml(archive, "xl/workbook.xml")
        rels = _read_xml(archive, "xl/_rels/workbook.xml.rels")
        rel_targets = {item.attrib.get("Id"): item.attrib.get("Target", "")
                       for item in rels.findall("rel:Relationship", _NS)}
        shared: list[str] = []
        try:
            shared_root = _read_xml(archive, "xl/sharedStrings.xml")
            for item in shared_root.findall("s:si", _NS):
                shared.append("".join(node.text or "" for node in item.findall(".//s:t", _NS)))
        except ValueError:
            pass
        sheet_nodes = workbook.findall("s:sheets/s:sheet", _NS)
        if not sheet_nodes:
            raise ValueError("This workbook does not contain any readable worksheets.")
        for sheet_index, sheet in enumerate(sheet_nodes[:30], 1):
            sheet_name = sheet.attrib.get("name") or f"Sheet {sheet_index}"
            rid = sheet.attrib.get(f"{{{_NS['r']}}}id")
            target = rel_targets.get(rid, "")
            if not target:
                continue
            internal_path = (target.lstrip("/") if target.startswith("/")
                             else posixpath.normpath(posixpath.join("xl", target)))
            if internal_path.startswith("../") or internal_path == "..":
                warnings.append(f"Worksheet '{sheet_name}' has an invalid internal relationship.")
                continue
            try:
                sheet_root = _read_xml(archive, internal_path)
            except ValueError:
                warnings.append(f"Worksheet '{sheet_name}' could not be extracted.")
                continue
            rows_out: list[str] = []
            row_nodes = sheet_root.findall(".//s:sheetData/s:row", _NS)
            for row in row_nodes[:2000]:
                cells = []
                for cell in row.findall("s:c", _NS)[:80]:
                    ref = cell.attrib.get("r", "")
                    cell_type = cell.attrib.get("t", "")
                    value_node = cell.find("s:v", _NS)
                    value = value_node.text if value_node is not None and value_node.text is not None else ""
                    if cell_type == "s" and value:
                        try:
                            value = shared[int(value)]
                        except (ValueError, IndexError):
                            value = ""
                    elif cell_type == "inlineStr":
                        value = "".join(node.text or "" for node in cell.findall(".//s:t", _NS))
                    formula = cell.find("s:f", _NS)
                    if formula is not None and formula.text:
                        formula_seen = True
                        value = f"{value} (formula: ={formula.text})" if value else f"(formula: ={formula.text})"
                    if value:
                        cells.append(f"{ref}={value}")
                if cells:
                    rows_out.append(" | ".join(cells))
            sections.append(f"## Sheet: {sheet_name}\n" + ("\n".join(rows_out) if rows_out else "[No populated cells in extraction range]"))
            if len(row_nodes) > 2000:
                warnings.append(f"Worksheet '{sheet_name}' was limited to the first 2,000 rows.")
        if len(sheet_nodes) > 30:
            warnings.append("Only the first 30 worksheets were extracted.")
        if formula_seen:
            warnings.append("Formula expressions are shown with cached values and are not recalculated by Spaceline, so cached results may be stale.")
    return "\n\n".join(sections), {"kind": "spreadsheet", "format": "XLSX", "sheet_count": min(len(sheet_nodes), 30)}, warnings


def _pptx(path: Path) -> tuple[str, dict[str, Any], list[str]]:
    sections: list[str] = []
    warnings: list[str] = []
    with _zip_members(path) as archive:
        slide_names = [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
        slide_names.sort(key=lambda name: int(re.search(r"slide(\d+)", name).group(1)))
        # Honour presentation order when the relationship graph is available
        # (users can reorder slides without renaming slideN.xml parts).
        try:
            presentation = _read_xml(archive, "ppt/presentation.xml")
            rels = _read_xml(archive, "ppt/_rels/presentation.xml.rels")
            targets = {item.attrib.get("Id"): item.attrib.get("Target", "") for item in rels.findall("rel:Relationship", _NS)}
            ordered = []
            for slide_id in presentation.findall(".//p:sldId", _NS):
                rid = slide_id.attrib.get(f"{{{_NS['r']}}}id")
                target = targets.get(rid, "")
                if target:
                    normalized = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("ppt", target))
                    if normalized in archive.namelist() and normalized.startswith("ppt/slides/"):
                        ordered.append(normalized)
            if ordered:
                slide_names = ordered
        except ValueError:
            pass
        slides_without_text = 0
        for index, name in enumerate(slide_names[:100], 1):
            root = _read_xml(archive, name)
            paragraphs = []
            for para in root.findall(".//a:p", _NS):
                value = "".join(node.text or "" for node in para.findall(".//a:t", _NS)).strip()
                if value:
                    paragraphs.append(value)
            if not paragraphs:
                paragraphs = [node.text or "" for node in root.findall(".//a:t", _NS) if (node.text or "").strip()]
            if not paragraphs:
                slides_without_text += 1
            sections.append(f"## Slide {index}\n" + ("\n".join(paragraphs) if paragraphs else "[No extractable text; may contain images/charts only]"))
        if slides_without_text:
            warnings.append(f"{slides_without_text} slide(s) contained no extractable text and may rely on images, charts or embedded objects.")
        if len(slide_names) > 100:
            warnings.append("Only the first 100 slides were extracted.")
        if not slide_names:
            warnings.append("No readable slides were found in this presentation.")
    return "\n\n".join(sections), {"kind": "presentation", "format": "PPTX", "slide_count": min(len(slide_names), 100)}, warnings


def _pdf(path: Path) -> tuple[str, dict[str, Any], list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF reading needs pypdf. Close Spaceline and run: python -m pip install pypdf") from None
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected. Unlock it before adding it to Spaceline.")
        pages = reader.pages
        count = len(pages)
        if count > MAX_PDF_PAGES:
            pages = pages[:MAX_PDF_PAGES]
        chunks = []
        pages_without_text = 0
        for index, page in enumerate(pages, 1):
            try:
                text = page.extract_text(extraction_mode="layout") or page.extract_text() or ""
            except Exception:
                text = page.extract_text() or ""
            if text.strip():
                chunks.append(f"## Page {index}\n{text.strip()}")
            else:
                pages_without_text += 1
    except ValueError:
        raise
    except Exception:
        raise ValueError("This PDF could not be read. It may be damaged or use unsupported encryption.") from None
    warnings = []
    if count > MAX_PDF_PAGES:
        warnings.append(f"Only the first {MAX_PDF_PAGES} pages were extracted.")
    if not chunks:
        warnings.append("No selectable text was found. This may be a scanned/image-only PDF; OCR is not included in this build.")
    elif pages_without_text:
        warnings.append(f"{pages_without_text} page(s) contained no selectable text and may be scanned or image-only.")
    return "\n\n".join(chunks), {"kind": "document", "format": "PDF", "page_count": count}, warnings


def _delimited(path: Path, delimiter: str) -> tuple[str, dict[str, Any], list[str]]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        raise ValueError("This CSV/TSV file is not valid UTF-8 text. Save it as UTF-8 and retry.") from None
    if delimiter == "\0":
        try:
            dialect = csv.Sniffer().sniff(raw[:8000], delimiters=",\t;|")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","
    rows = []
    row_limited = False
    column_limited = False
    try:
        for index, row in enumerate(csv.reader(io.StringIO(raw), delimiter=delimiter)):
            if index >= 5000:
                row_limited = True
                break
            if len(row) > 100:
                column_limited = True
            rows.append(" | ".join(cell.replace("\n", " ") for cell in row[:100]))
    except csv.Error:
        raise ValueError("This CSV/TSV contains a malformed or oversized field and could not be parsed safely.") from None
    warnings = []
    if row_limited:
        warnings.append("Only the first 5,000 rows were extracted.")
    if column_limited:
        warnings.append("Only the first 100 columns per row were extracted.")
    return "\n".join(rows), {"kind": "spreadsheet", "format": "CSV/TSV", "row_count": len(rows)}, warnings


def extract_document(path: Path, *, max_bytes: int = MAX_DOCUMENT_BYTES) -> dict[str, Any]:
    """Extract text from safe text, PDF, DOCX, XLSX, PPTX, CSV and TSV files.

    This is a text extraction layer, not OCR or a spreadsheet recalculation engine.
    It never executes macros, embedded scripts, hyperlinks, or document relationships.
    """
    target = Path(path).expanduser().resolve()
    if _is_protected_path(target):
        raise ValueError("This path is protected because it may contain credentials or private data.")
    extension = path_extension(target)
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"File type '{extension or '(no extension)'}' is not supported for content extraction.")
    if not target.is_file():
        raise FileNotFoundError("File not found.")
    size = target.stat().st_size
    if size > max_bytes:
        raise ValueError(f"Files larger than {max_bytes // (1024 * 1024)} MB cannot be extracted.")
    if extension == ".pdf":
        content, metadata, warnings = _pdf(target)
    elif extension == ".docx":
        content, metadata, warnings = _docx(target)
    elif extension == ".xlsx":
        content, metadata, warnings = _xlsx(target)
    elif extension == ".pptx":
        content, metadata, warnings = _pptx(target)
    elif extension in {".csv", ".tsv"}:
        content, metadata, warnings = _delimited(target, "\t" if extension == ".tsv" else "\0")
    else:
        try:
            content = target.read_text(encoding="utf-8-sig")
        except UnicodeError:
            raise ValueError("This file is not valid UTF-8 text and cannot be extracted safely.") from None
        if "\x00" in content:
            raise ValueError("This file appears to contain binary data and cannot be opened as text.")
        metadata, warnings = {"kind": "text", "format": extension.lstrip(".").upper() or "TEXT"}, []
    content, truncated = _clip(content)
    if truncated:
        warnings.append(f"Extracted text was capped at {MAX_EXTRACTED_CHARS:,} characters.")
    return {
        "filename": target.name,
        **metadata,
        "content": content,
        "characters": len(content),
        "source_bytes": size,
        "truncated": truncated,
        "warnings": warnings,
    }
