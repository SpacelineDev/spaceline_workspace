import tempfile
import unittest
import zipfile
from pathlib import Path

from app.document_reader import extract_document


class DocumentReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_plain_text_and_csv_are_extracted(self):
        text = self.root / 'notes.md'
        text.write_text('# hello\nworld', encoding='utf-8')
        result = extract_document(text)
        self.assertIn('# hello', result['content'])
        self.assertEqual(result['kind'], 'text')
        csv = self.root / 'marks.csv'
        csv.write_text('name,score\nAsha,95\n', encoding='utf-8')
        result = extract_document(csv)
        self.assertIn('Asha', result['content'])
        self.assertIn('95', result['content'])

    def test_docx_extracts_paragraphs_and_table_cells(self):
        path = self.root / 'report.docx'
        xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
        <w:p><w:r><w:t>Quarterly report</w:t></w:r></w:p>
        <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Revenue</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>100</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
        </w:body></w:document>'''
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('word/document.xml', xml)
        result = extract_document(path)
        self.assertIn('Quarterly report', result['content'])
        self.assertIn('Revenue', result['content'])
        self.assertIn('100', result['content'])
        self.assertEqual(result['kind'], 'document')

    def test_xlsx_extracts_sheets_and_cached_values(self):
        path = self.root / 'budget.xlsx'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('xl/workbook.xml', '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Budget" sheetId="1" r:id="rId1"/></sheets></workbook>''')
            z.writestr('xl/_rels/workbook.xml.rels', '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="worksheet"/></Relationships>''')
            z.writestr('xl/sharedStrings.xml', '''<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Rent</t></si></sst>''')
            z.writestr('xl/worksheets/sheet1.xml', '''<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>15000</v></c></row></sheetData></worksheet>''')
        result = extract_document(path)
        self.assertIn('Budget', result['content'])
        self.assertIn('Rent', result['content'])
        self.assertIn('15000', result['content'])
        self.assertEqual(result['kind'], 'spreadsheet')

    def test_pptx_extracts_slides_in_order(self):
        path = self.root / 'deck.pptx'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('ppt/slides/slide1.xml', '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>First slide</a:t><a:t>Key point</a:t></p:sld>''')
        result = extract_document(path)
        self.assertIn('Slide 1', result['content'])
        self.assertIn('First slide', result['content'])
        self.assertEqual(result['kind'], 'presentation')


    def test_extensionless_project_files_are_supported_as_text(self):
        dockerfile = self.root / "Dockerfile"
        dockerfile.write_text("FROM python:3.13\nWORKDIR /app\n", encoding="utf-8")
        result = extract_document(dockerfile)
        self.assertIn("FROM python:3.13", result["content"])
        self.assertEqual(result["format"], "TXT")
        gitignore = self.root / ".gitignore"
        gitignore.write_text(".venv/\n__pycache__/\n", encoding="utf-8")
        self.assertIn(".venv/", extract_document(gitignore)["content"])

    def test_oversized_and_unsupported_files_are_rejected(self):
        path = self.root / 'large.bin'
        path.write_bytes(b'x' * 100)
        with self.assertRaisesRegex(ValueError, 'not supported'):
            extract_document(path, max_bytes=50)
        path = self.root / 'archive.zip'
        path.write_bytes(b'not a document')
        with self.assertRaisesRegex(ValueError, 'not supported'):
            extract_document(path)

    def test_secret_like_paths_are_not_read_by_document_tool(self):
        path = self.root / '.env.production'
        path.write_text('SECRET=abc', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'protected'):
            extract_document(path)


if __name__ == '__main__':
    unittest.main()

class SensitiveTextRedactionTests(unittest.TestCase):
    def test_redacts_assignment_values_and_common_provider_tokens(self):
        from app.document_reader import redact_sensitive_text
        content = '''{
  "OPENAI_API_KEY": "sk-proj-abcdefghijklmnop123456",
  "password": "my-private-password",
  "message": "keep this ordinary text",
  "github": "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
}'''
        redacted, count = redact_sensitive_text(content)
        self.assertGreaterEqual(count, 3)
        self.assertNotIn("sk-proj-abcdefghijklmnop123456", redacted)
        self.assertNotIn("my-private-password", redacted)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz1234567890", redacted)
        self.assertIn("keep this ordinary text", redacted)

    def test_redacts_bearer_tokens_and_private_key_blocks(self):
        from app.document_reader import redact_sensitive_text
        content = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n-----BEGIN PRIVATE KEY-----\nPRIVATEKEYDATA\n-----END PRIVATE KEY-----"
        redacted, count = redact_sensitive_text(content)
        self.assertGreaterEqual(count, 2)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", redacted)
        self.assertNotIn("PRIVATEKEYDATA", redacted)

class ExpandedProtectedPathTests(unittest.TestCase):
    def test_protects_kubernetes_credentials_and_service_account_files(self):
        from app.document_reader import _is_protected_path
        self.assertTrue(_is_protected_path(Path("project/.kube/config")))
        self.assertTrue(_is_protected_path(Path("project/serviceAccountKey.json")))
        self.assertTrue(_is_protected_path(Path("project/production.env")))

class DocumentExtractionEdgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_rejects_xml_dtd_even_when_declaration_is_past_the_initial_buffer(self):
        path = self.root / "late-doctype.docx"
        document_xml = " " * 9000 + '<!DOCTYPE w:document [<!ENTITY x "boom">]><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>&x;</w:t></w:r></w:p></w:body></w:document>'
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        with self.assertRaisesRegex(ValueError, "XML declarations"):
            extract_document(path)

    def test_xlsx_discloses_cached_formula_values_are_not_recalculated(self):
        path = self.root / "formula.xlsx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Calc" sheetId="1" r:id="rId1"/></sheets></workbook>')
            archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="worksheet"/></Relationships>')
            archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1"><f>SUM(B1:B2)</f><v>10</v></c></row></sheetData></worksheet>')
        result = extract_document(path)
        self.assertIn("formula: =SUM(B1:B2)", result["content"])
        self.assertTrue(any("not recalculated" in warning.lower() for warning in result["warnings"]))

    def test_csv_warns_when_row_or_column_limits_are_reached(self):
        path = self.root / "large.csv"
        path.write_text("\n".join(",".join(["x"] * 101) for _ in range(5001)), encoding="utf-8")
        result = extract_document(path)
        self.assertTrue(any("5,000 rows" in warning for warning in result["warnings"]))
        self.assertTrue(any("100 columns" in warning for warning in result["warnings"]))

    def test_blank_pdf_explains_that_scanned_text_was_not_extracted(self):
        from pypdf import PdfWriter
        path = self.root / "scanned.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with path.open("wb") as file:
            writer.write(file)
        result = extract_document(path)
        self.assertEqual(result["format"], "PDF")
        self.assertTrue(any("scanned/image-only" in warning.lower() for warning in result["warnings"]))
