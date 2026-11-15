import unittest

import app.main as main


class ToolRoutingTests(unittest.TestCase):
    def test_read_document_request_activates_project_tools_without_code_mode(self):
        self.assertTrue(main._is_file_task("Read and summarize the PDF in my project", "cowork", "Demo"))
        self.assertTrue(main._uses_tool_chat("Read and summarize the PDF in my project", "cowork", "chat", "Demo"))

    def test_search_project_files_request_activates_project_tools(self):
        self.assertTrue(main._is_file_task("Search project files for the API endpoint", "cowork", "Demo"))

    def test_unrelated_chat_does_not_activate_project_file_tools(self):
        self.assertFalse(main._is_file_task("Explain gradient descent simply", "cowork", "Demo"))
        self.assertFalse(main._uses_tool_chat("Explain gradient descent simply", "cowork", "chat", "Demo"))

    def test_read_only_file_tools_are_available_in_cowork_with_project(self):
        tools = main._tool_schemas("cowork", "Demo", False)
        names = {item["function"]["name"] for item in tools}
        self.assertTrue({"project_list_files", "project_read_file", "project_analyze_file", "project_search_files"}.issubset(names))
        self.assertNotIn("project_write_file", names)
        self.assertNotIn("project_run_check", names)

    def test_write_and_run_tools_remain_code_mode_only(self):
        tools = main._tool_schemas("code", "Demo", False)
        names = {item["function"]["name"] for item in tools}
        self.assertTrue({"project_write_file", "project_run_check"}.issubset(names))

    def test_no_project_means_no_project_tools(self):
        self.assertEqual(main._tool_schemas("cowork", None, False), [])
