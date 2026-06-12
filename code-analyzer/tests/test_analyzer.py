#!/usr/bin/env python3
"""
test_analyzer.py - Unit tests for CodeAnalyzer
Tests finding detections, rules compliance and metrics calculation across various languages.
"""

from __future__ import annotations
import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Ensure we can import from parent directory
sys.path.append(str(Path(__file__).resolve().parent.parent))
from analyzer import CodeAnalyzer, Finding, FileMetrics

class TestCodeAnalyzer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for scanning tests
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def tearDown(self):
        # Clean up temporary directory after each test
        shutil.rmtree(self.test_dir)

    def test_determine_language(self):
        analyzer = CodeAnalyzer(self.test_dir)
        
        py_file = self.test_path / "test.py"
        js_file = self.test_path / "index.js"
        cpp_file = self.test_path / "main.cpp"
        unknown_file = self.test_path / "README.txt"

        self.assertEqual(analyzer._determine_language(py_file), "python")
        self.assertEqual(analyzer._determine_language(js_file), "javascript_typescript")
        self.assertEqual(analyzer._determine_language(cpp_file), "cpp_c")
        self.assertIsNone(analyzer._determine_language(unknown_file))

    def test_metrics_calculation(self):
        # Test LOC, comments, blanks, complexity
        code_content = """# Inicjalizacja skrócona
def calculate_sum(a, b):
    # Proste warunki rozgałęzienia
    if a > 0 and b > 0:
        return a + b
    elif a < 0 or b < 0:
        return abs(a) + abs(b)
    else:
        return 0

"""
        py_file = self.test_path / "math_helper.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(code_content)

        analyzer = CodeAnalyzer(self.test_dir, selected_languages=["python"])
        findings, metrics, summary = analyzer.scan()

        self.assertIn("math_helper.py", metrics)
        metric: FileMetrics = metrics["math_helper.py"]

        self.assertEqual(metric.language, "python")
        self.assertEqual(metric.loc, 7)  # Code lines excluding blanks and comments
        self.assertEqual(metric.comment_lines, 2)  # Comment lines starting with #
        self.assertEqual(metric.blank_lines, 1)  # Empty spacer line at bottom
        self.assertEqual(metric.functions_count, 1)  # Count of def keywords at start
        
        # Complexity: baseline starts at 1, +1 for "if", +1 for "and", +1 for "elif", +1 for "or" -> total estimation should be 5
        self.assertEqual(metric.complexity, 5)

    def test_python_security_vulnerabilities(self):
        vuln_content = """import os
import pickle

def unsafe_actions(payload):
    eval("print('hello')") # PY-EVAL
    os.system("some-command") # PY-OS-SYSTEM
    pickle.loads(payload) # PY-PICKLE
"""
        py_file = self.test_path / "vuln.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(vuln_content)

        analyzer = CodeAnalyzer(self.test_dir, selected_languages=["python"])
        findings, metrics, summary = analyzer.scan()

        # Extract rule IDs
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("PY-EVAL", rule_ids)
        self.assertIn("PY-OS-SYSTEM", rule_ids)
        self.assertIn("PY-PICKLE", rule_ids)

        # Check severity of eval
        eval_finding = next(f for f in findings if f.rule_id == "PY-EVAL")
        self.assertEqual(eval_finding.severity, "High")
        self.assertEqual(eval_finding.line_number, 5)

    def test_secret_credential_leak(self):
        config_content = """const API_SECRET_KEY = "mySuperSecretPassword123!!"; // CRITICAL leak
const URL = "mysql://root:superUnsafePassword@127.0.0.1:3306/db";
"""
        js_file = self.test_path / "config.js"
        with open(js_file, "w", encoding="utf-8") as f:
            f.write(config_content)

        analyzer = CodeAnalyzer(self.test_dir, selected_languages=["javascript_typescript"])
        findings, metrics, summary = analyzer.scan()

        secrets = [f for f in findings if f.rule_id == "SEC-SECRET"]
        self.assertEqual(len(secrets), 2)
        self.assertTrue(any("API_SECRET_KEY" in s.line_content for s in secrets))
        self.assertTrue(any("mysql://" in s.line_content for s in secrets))
        self.assertEqual(secrets[0].severity, "Critical")

    def test_js_specific_vulnerabilities(self):
        js_content = """const div = document.getElementById("main");
div.innerHTML = "<p>" + location.search + "</p>"; // JS-INNER-HTML
console.log("tracing input state"); // JS-CONSOLE-LOG
var testValue = 10; // JS-VAR-USAGE
"""
        js_file = self.test_path / "dom.js"
        with open(js_file, "w", encoding="utf-8") as f:
            f.write(js_content)

        analyzer = CodeAnalyzer(self.test_dir, selected_languages=["javascript_typescript"])
        findings, metrics, summary = analyzer.scan()

        rule_ids = [f.rule_id for f in findings]
        self.assertIn("JS-INNER-HTML", rule_ids)
        self.assertIn("JS-CONSOLE-LOG", rule_ids)
        self.assertIn("JS-VAR-USAGE", rule_ids)

    def test_php_specific_vulnerabilities(self):
        php_content = """<?php
$query = "SELECT * FROM users WHERE id = " . $_GET['id']; // PHP-SQL-INJECT
eval($some_string); // PHP-EVAL
shell_exec($command); // PHP-EXEC
echo $_GET['id']; // PHP-XSS-ECHO
$md5_hash = md5("password"); // PHP-WEAK-HASH
"""
        php_file = self.test_path / "action.php"
        with open(php_file, "w", encoding="utf-8") as f:
            f.write(php_content)

        analyzer = CodeAnalyzer(self.test_dir, selected_languages=["php"])
        findings, metrics, summary = analyzer.scan()

        rule_ids = [f.rule_id for f in findings]
        self.assertIn("PHP-SQL-INJECT", rule_ids)
        self.assertIn("PHP-EVAL", rule_ids)
        self.assertIn("PHP-EXEC", rule_ids)
        self.assertIn("PHP-XSS-ECHO", rule_ids)
        self.assertIn("PHP-WEAK-HASH", rule_ids)

    def test_file_level_warnings(self):
        # High complexity warning test
        complex_content = "def deeply_nested_helper(x):\n"
        for i in range(25):
            complex_content += f"{'    ' * (i+1)}if x == {i}:\n"
            complex_content += f"{'    ' * (i+2)}print(x)\n"

        py_file = self.test_path / "complex_code.py"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(complex_content)

        analyzer = CodeAnalyzer(self.test_dir, selected_languages=["python"])
        findings, metrics, summary = analyzer.scan()

        rule_ids = [f.rule_id for f in findings]
        self.assertIn("QLT-HIGH-COMPLEXITY", rule_ids)

if __name__ == "__main__":
    unittest.main()
