import tempfile
import unittest
from pathlib import Path

from app.skills import discover_skills, import_skill, select_skills


class SkillRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_builtin_skills_auto_match_user_intent(self):
        skills = discover_skills(self.root)
        selected = select_skills("Fix this Python traceback and debug the failing test", skills)
        self.assertTrue(any(item["id"] == "debugging" for item in selected))

    def test_imported_claude_skill_is_discovered_and_auto_selected(self):
        content = """---\nname: database-migrations\ndescription: Safely design and run database migrations.\ntriggers: migration, sqlite schema, database migration\n---\nAlways create a backup before a migration.\n"""
        imported = import_skill(self.root, "Database migrations", content)
        self.assertEqual(imported["name"], "database-migrations")
        selected = select_skills("Help me write a SQLite schema migration", discover_skills(self.root))
        self.assertTrue(any(item["id"] == "database-migrations" for item in selected))

    def test_import_rejects_empty_or_oversized_skill(self):
        with self.assertRaises(ValueError):
            import_skill(self.root, "Empty", "   ")


if __name__ == "__main__":
    unittest.main()

class SkillTriggerPrecisionTests(unittest.TestCase):
    def test_explicit_triggers_are_authoritative_not_generic_description_words(self):
        from app.skills import select_skills
        skills = [
            {"name":"Spreadsheet Analysis", "description":"Inspect spreadsheet files and analyze data", "triggers":"spreadsheet, xlsx, excel file"},
            {"name":"Document Analysis", "description":"Read and analyze documents", "triggers":"pdf, docx, document analysis"},
        ]
        selected = select_skills("Help me review the code in this Python project", skills)
        self.assertEqual(selected, [])
        selected = select_skills("Please analyze this xlsx spreadsheet", skills)
        self.assertEqual([item['name'] for item in selected], ["Spreadsheet Analysis"])

    def test_multiple_relevant_skills_can_be_combined_but_are_bounded(self):
        from app.skills import select_skills
        skills = [{"name":f"Skill {i}", "description":"", "triggers":f"trigger{i}"} for i in range(10)]
        selected = select_skills(" ".join(f"trigger{i}" for i in range(10)), skills)
        self.assertEqual(len(selected), 5)


class BroadSkillCoverageTests(unittest.TestCase):
    def test_registry_contains_many_non_provider_specific_skill_domains(self):
        skills = discover_skills(Path(tempfile.gettempdir()))
        ids = {item["id"] for item in skills}
        self.assertGreaterEqual(len(skills), 28)
        self.assertTrue({"project-planning", "math-tutor", "interview-coach", "test-engineering", "backend-architecture", "devops-and-deployment", "data-visualization", "technical-writing", "cloud-computing-tutor", "accessibility-review"}.issubset(ids))

    def test_skill_triggers_select_spreadsheet_and_accessibility_workflows(self):
        skills = discover_skills(Path(tempfile.gettempdir()))
        spreadsheet = select_skills("Analyze the formulas in this Excel workbook", skills)
        self.assertTrue(any(item["id"] == "spreadsheet-analysis" for item in spreadsheet))
        accessibility = select_skills("Run a WCAG accessibility and contrast review", skills)
        self.assertTrue(any(item["id"] == "accessibility-review" for item in accessibility))
