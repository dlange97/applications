#!/usr/bin/env python3
"""
static_analyzer_engine.py - Core Static Analysis Engine
Scans directories, performs regex and AST-based matching for vulnerability detection and metrics collection.
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional

# Severity definition
SEV_CRITICAL = "Critical"
SEV_HIGH = "High"
SEV_MEDIUM = "Medium"
SEV_LOW = "Low"
SEV_INFO = "Info"

@dataclass
class Finding:
    file_path: str
    line_number: int
    line_content: str
    severity: str
    category: str
    rule_id: str
    message: str
    remediation: str

@dataclass
class FileMetrics:
    file_path: str
    language: str
    loc: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    complexity: int = 1  # 1 is base complexity
    functions_count: int = 0
    classes_count: int = 0

class CodeAnalyzer:
    DEFAULT_IGNORED_DIRS = {
        "node_modules", "vendor", ".git", "bin", "obj", "dist", "build",
        "var", ".idea", ".vscode", ".expo", "venv", ".venv", "env", ".env",
        "__pycache__", "coverage", "test-output", "security-audit"
    }

    # Supported languages mapped to their extensions
    LANGUAGES = {
        "python": {".py"},
        "javascript_typescript": {".js", ".jsx", ".ts", ".tsx"},
        "php": {".php"},
        "java": {".java"},
        "go": {".go"},
        "cpp_c": {".c", ".cpp", ".h", ".hpp", ".cc"},
        "ruby": {".rb"},
        "html_css": {".html", ".htm", ".css"},
        "shell": {".sh", ".bash"}
    }

    # Reverse mapping for display names
    LANG_DISPLAY_NAMES = {
        "python": "Python",
        "javascript_typescript": "JavaScript / TypeScript",
        "php": "PHP",
        "java": "Java",
        "go": "Go",
        "cpp_c": "C / C++",
        "ruby": "Ruby",
        "html_css": "HTML / CSS",
        "shell": "Shell Script"
    }

    def __init__(self, target_dir: str, selected_languages: Optional[List[str]] = None):
        self.target_dir = Path(target_dir).resolve()
        self.selected_languages = selected_languages or list(self.LANGUAGES.keys())
        self.findings: List[Finding] = []
        self.metrics: Dict[str, FileMetrics] = {}
        self.scanned_files_count = 0
        self.ignored_files_count = 0

        # Compile general rules (e.g. hardcoded secrets)
        self.secret_patterns = [
            (
                r'(?i)(password|passwd|db_password|pg_password|mysql_pass|api_key|api_secret|apikey|client_secret|jwt_token|private_key|aws_access_key|aws_secret_key|ssh_key|auth_token)[a-zA-Z0-9_\-]*\s*[:=]\s*["\']([a-zA-Z0-9_\-\.\~\+\/\!\@\#\$\%\^\&\*\(\)]{10,})["\']',
                "Hardcoded credential/secret key found",
                "Store credentials securely in environment variables or external vaults (like AWS Secrets Manager, Vault) instead of hardcoding them in files.",
                SEV_CRITICAL,
                "A02:2021-Cryptographic Failures"
            ),
            (
                r'(?i)(mongodb\+srv|mysql|postgresql|postgres|redis|amqp|amqps|sqlite):\/\/[a-zA-Z0-9_\-\.\~]+:[a-zA-Z0-9_\-\.\~\+\%\/]+@[a-zA-Z0-9_\-\.\~]+',
                "Hardcoded connection string with password",
                "Remove raw credential connection strings from source code. Utilize environment variables and configuration files.",
                SEV_CRITICAL,
                "A02:2021-Cryptographic Failures"
            )
        ]

    def _determine_language(self, file_path: Path) -> Optional[str]:
        ext = file_path.suffix.lower()
        for s_lang, extensions in self.LANGUAGES.items():
            if ext in extensions:
                if s_lang in self.selected_languages:
                    return s_lang
        return None

    def scan(self) -> Tuple[List[Finding], Dict[str, FileMetrics], Dict[str, int]]:
        """Performs the full scan on target directory and returns results and summary metrics."""
        self.findings = []
        self.metrics = {}
        self.scanned_files_count = 0
        self.ignored_files_count = 0

        if not self.target_dir.exists() or not self.target_dir.is_dir():
            raise FileNotFoundError(f"Target directory {self.target_dir} does not exist.")

        for root, dirs, files in os.walk(self.target_dir):
            # Prune ignored directories in-place (os.walk permits this modification)
            dirs[:] = [d for d in dirs if d not in self.DEFAULT_IGNORED_DIRS]

            for file in files:
                file_path = Path(root) / file
                
                # Exclude excessively large files to avoid crashes (e.g. over 5MB)
                try:
                    if file_path.is_symlink() or file_path.stat().st_size > 5 * 1024 * 1024:
                        self.ignored_files_count += 1
                        continue
                except OSError:
                    self.ignored_files_count += 1
                    continue

                lang = self._determine_language(file_path)
                if not lang:
                    continue

                self._analyze_file(file_path, lang)
                self.scanned_files_count += 1

        summary = self._compile_summary()
        return self.findings, self.metrics, summary

    def _analyze_file(self, file_path: Path, language: str):
        rel_path = str(file_path.relative_to(self.target_dir))
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return

        file_metric = FileMetrics(file_path=rel_path, language=language)
        
        # Determine language specific rules
        lang_specific_rules = self._get_rules_for_language(language)
        
        # State tracking for some multi-line contexts if needed
        for idx, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # --- Code Metrics ---
            if not stripped_line:
                file_metric.blank_lines += 1
                continue
                
            is_comment = False
            # Check standard comment syntax
            if language in {"python", "shell", "ruby"}:
                if stripped_line.startswith("#"):
                    file_metric.comment_lines += 1
                    is_comment = True
            elif language in {"javascript_typescript", "php", "java", "go", "cpp_c"}:
                if stripped_line.startswith("//") or stripped_line.startswith("/*") or stripped_line.startswith("*"):
                    file_metric.comment_lines += 1
                    is_comment = True
            elif language == "html_css":
                if stripped_line.startswith("<!--") or stripped_line.startswith("/*") or stripped_line.startswith("*"):
                    file_metric.comment_lines += 1
                    is_comment = True

            if not is_comment:
                file_metric.loc += 1
                
                # Check for functions / classes (naive estimation with regex)
                self._update_structure_metrics(stripped_line, language, file_metric)
                
                # Calculate complexity additions based on controls
                self._calculate_complexity(stripped_line, language, file_metric)

            # --- Rule Scan ---
            # Check general credentials patterns
            for pattern, msg, rem, sev, cat in self.secret_patterns:
                match = re.search(pattern, line)
                if match:
                    # Filter out helper environment keys or variable definitions that aren't text literals
                    if not line.count('getenv') and not line.count('$_ENV') and not line.count('env.'):
                        self.findings.append(Finding(
                            file_path=rel_path,
                            line_number=idx,
                            line_content=line.strip(),
                            severity=sev,
                            category=cat,
                            rule_id="SEC-SECRET",
                            message=msg,
                            remediation=rem
                        ))

            # Scan language-specific rules
            for pattern, msg, rem, sev, cat, rule_id in lang_specific_rules:
                if re.search(pattern, line):
                    self.findings.append(Finding(
                        file_path=rel_path,
                        line_number=idx,
                        line_content=line.strip(),
                        severity=sev,
                        category=cat,
                        rule_id=rule_id,
                        message=msg,
                        remediation=rem
                    ))

            # Common issues (TODOs, excessively long lines)
            if "TODO" in line or "FIXME" in line:
                self.findings.append(Finding(
                    file_path=rel_path,
                    line_number=idx,
                    line_content=line.strip(),
                    severity=SEV_INFO,
                    category="Code Quality",
                    rule_id="QLT-TODO",
                    message="TODO or FIXME tag found in comments",
                    remediation="Resolve pending tasks to avoid leaving uncompleted issues or technical debt in production."
                ))

            if len(line) > 160:
                self.findings.append(Finding(
                    file_path=rel_path,
                    line_number=idx,
                    line_content=line.strip()[:60] + "...",
                    severity=SEV_LOW,
                    category="Style/Quality",
                    rule_id="QLT-LONG-LINE",
                    message="Extremely long codebase line (>160 chars)",
                    remediation="Split the code statement or wrap it properly into multiple lines to improve readability."
                ))

        # Check file-level quality issues
        if file_metric.loc > 500:
            self.findings.append(Finding(
                file_path=rel_path,
                line_number=1,
                line_content=f"File LOC: {file_metric.loc}",
                severity=SEV_MEDIUM,
                category="Code Quality",
                rule_id="QLT-LARGE-FILE",
                message=f"Large file size ({file_metric.loc} lines of code)",
                remediation="Consider separating this file into smaller, granular modules or micro-utilities (Single Responsibility Principle)."
            ))
            
        if file_metric.complexity > 20:
            self.findings.append(Finding(
                file_path=rel_path,
                line_number=1,
                line_content=f"Estimated complexity: {file_metric.complexity}",
                severity=SEV_MEDIUM,
                category="Code Quality",
                rule_id="QLT-HIGH-COMPLEXITY",
                message=f"High estimated cyclomatic complexity ({file_metric.complexity})",
                remediation="Refactor branching paths (ifs, loops, switch statements). Split complex nested blocks into auxiliary helper routines."
            ))

        self.metrics[rel_path] = file_metric

    def _get_rules_for_language(self, language: str) -> List[Tuple[str, str, str, str, str, str]]:
        """Returns specific analysis rules for a given language.
        Format: (regex, message, remediation, severity, category, rule_id)
        """
        rules = []
        if language == "python":
            rules = [
                (
                    r'\beval\s*\(',
                    "Insecure standard evaluation `eval()` in use",
                    "Avoid using `eval()`. Use abstract syntax tree modules `ast.literal_eval()` or structured formatting libraries if parsing data.",
                    SEV_HIGH, "A03:2021-Injection", "PY-EVAL"
                ),
                (
                    r'\bexec\s*\(',
                    "Dynamic code statement execution `exec()` is in use",
                    "Do not use `exec()` dynamically as it can execute arbitrary Python statements under client influence.",
                    SEV_HIGH, "A03:2021-Injection", "PY-EXEC"
                ),
                (
                    r'subprocess\.(Popen|run|call|check_output|check_call)\s*\(.*shell\s*=\s*(True|1)',
                    "Process executed with system shell access (`shell=True`)",
                    "Set `shell=False` inside subprocess routines and pass the executable args as a list instead of a raw concatenated command string.",
                    SEV_HIGH, "A03:2021-Injection", "PY-SHELL"
                ),
                (
                    r'\bos\.system\s*\(',
                    "Dangerous legacy system execution command `os.system()`",
                    "Prefer standard subprocess package module `subprocess.run(..., shell=False)` over legacy platform command systems.",
                    SEV_HIGH, "A03:2021-Injection", "PY-OS-SYSTEM"
                ),
                (
                    r'\bpickle\.(loads|load|dumps)\b',
                    "Unsafe representation serializer deserialization risk (`pickle`)",
                    "Use secured serializers like `json` or protobuf schemes rather than pickle, which supports arbitrary code executing upon load.",
                    SEV_HIGH, "A08:2021-Software and Data Integrity Failures", "PY-PICKLE"
                ),
                (
                    r'\byaml\.load\s*\(.*(?!Loader\s*=\s*safe_loader)',
                    "Potential unsafe YAML parsing method trigger",
                    "Always employ security-checked loaders: `yaml.safe_load()` or specify `Loader=yaml.SafeLoader` explicitly inside the call statement.",
                    SEV_MEDIUM, "A08:2021-Software and Data Integrity Failures", "PY-YAML"
                ),
                (
                    r'except\s*(Exception)?\s*:\s*(pass|continue)\b',
                    "Generic exception pattern caught and silently ignored",
                    "Avoid catching generic types without logging or action. Log error parameters or match specific logical exceptions.",
                    SEV_MEDIUM, "A09:2021-Security Logging and Monitoring Failures", "PY-SILENT-EXCEPT"
                ),
                (
                    r'\bprint\s*\(',
                    "Leftover runtime troubleshooting statement (`print()`)",
                    "Replace raw print statement debuggers with standard `logging` levels (debug, info, warning) for production builds.",
                    SEV_LOW, "Code Quality", "PY-PRINT"
                ),
                (
                    r'\bassert\s+',
                    "Usage of standard asserts outside test suites",
                    "Ensure assertions are not utilized for client inputs, as standard Python optimizes assertions (`-O` flag), stripping them out.",
                    SEV_LOW, "Code Quality", "PY-ASSERT"
                )
            ]
        elif language == "javascript_typescript":
            rules = [
                (
                    r'\beval\s*\(',
                    "Insecure dynamic evaluation executor `eval()` is used",
                    "Perform data conversions by utilizing JSON schema validation or explicit structured maps instead of eval statement execution.",
                    SEV_HIGH, "A03:2021-Injection", "JS-EVAL"
                ),
                (
                    r'\.innerHTML\s*=',
                    "Assignment of value utilizing innerHTML without scrubbing context",
                    "Prevent DOM-based Cross-Site Scripting (XSS). Use `textContext` or an established sanitizer API package like DOMPurify.",
                    SEV_HIGH, "A03:2021-Injection", "JS-INNER-HTML"
                ),
                (
                    r'document\.write(ln)?\s*\(',
                    "Obsolete insecure renderer trigger `document.write` in use",
                    "Avoid loading page structures directly via script templates, prefer modern structured DOM updates (`appendChild`, `createElement`).",
                    SEV_HIGH, "A03:2021-Injection", "JS-DOC-WRITE"
                ),
                (
                    r'localStorage\.setItem\s*\(.*(password|passwd|token|api_key|jwt|secret|auth|session)',
                    "Sensitive storage data keys cached inside browser `localStorage`",
                    "Secure cookies configured with HTTPOnly and Secure flag criteria are recommended rather than local storage flags for secrets.",
                    SEV_MEDIUM, "A04:2021-Insecure Design", "JS-LOCALSTORAGE"
                ),
                (
                    r'\bconsole\.(log|debug|trace|dir)\b',
                    "Debug tracing wrapper left inside production layout scripts",
                    "Configure automated transpiler packages to clean log footprints or replace console flags with enterprise logger solutions.",
                    SEV_LOW, "Code Quality", "JS-CONSOLE-LOG"
                ),
                (
                    r'\bvar\s+[a-zA-Z0-9_]+',
                    "Legacy lexical variable scope flag `var` is declared",
                    "Enforce ES6 standard specifications. Standardize codebase variables with modern immutable scoping attributes: `const` and `let`.",
                    SEV_LOW, "Code Quality", "JS-VAR-USAGE"
                ),
                (
                    r'==\s*(?!"")(?!\d)(?!(true|false|null|undefined))',
                    "Usage of loose condition matching operators (`==`)",
                    "Leverage precise evaluation practices by migrating elements over to strict criteria statements: exact matching flags (`===`).",
                    SEV_LOW, "Code Quality", "JS-LOOSE-EQUALITY"
                ),
                (
                    r'catch\s*\(\w*\)\s*\{\s*\}',
                    "Silent JS catch block discarding system logical breakdowns",
                    "Introduce proper error mitigation flows inside catches. Write output errors to logs or present user notifications safely.",
                    SEV_MEDIUM, "A09:2021-Security Logging and Monitoring Failures", "JS-SILENT-CATCH"
                )
            ]
        elif language == "php":
            rules = [
                (
                    r'\beval\s*\(',
                    "Dynamic executor `eval()` is triggering system security threats",
                    "Do not allow raw PHP parsing from strings, since it can enable dangerous remote code execution commands.",
                    SEV_HIGH, "A03:2021-Injection", "PHP-EVAL"
                ),
                (
                    r'\b(shell_exec|exec|system|passthru|popen|proc_open)\s*\(',
                    "Vulnerable platform execution shell pipeline `shell_exec/exec`",
                    "Mitigate command injection bugs. Try using built-in SDK parameters or scrub arguments with shell safety utils: `escapeshellarg()`.",
                    SEV_HIGH, "A03:2021-Injection", "PHP-EXEC"
                ),
                (
                    r'unserialize\s*\(',
                    "Unsafe custom object deserialization is executed",
                    "Convert applications to run secure transfer payload schemes such as JS Object standards (using `json_decode`, `json_encode`).",
                    SEV_HIGH, "A08:2021-Software and Data Integrity Failures", "PHP-UNSERIALIZE"
                ),
                (
                    r'(["\'].*SELECT.*FROM.*WHERE.*\$_(GET|POST|REQUEST|COOKIE|SERVER))|(\$sql\s*=\s*["\'].*WHERE.*\s*\.\s*\$)',
                    "Insecure inline SQL composition using HTTP global parameters",
                    "Switch database operations to use prepared statement arrays and positional attributes through standard ORM adapters or PDO bindings.",
                    SEV_CRITICAL, "A03:2021-Injection", "PHP-SQL-INJECT"
                ),
                (
                    r'\b(md5|sha1)\s*\(',
                    "Outdated insecure signature algorithms detected (`md5` or `sha1`)",
                    "Upgrade data storage signatures to use modern cryptographically secure hashing functions: `password_hash()` (Bcrypt).",
                    SEV_MEDIUM, "A02:2021-Cryptographic Failures", "PHP-WEAK-HASH"
                ),
                (
                    r'\b(var_dump|print_r)\s*\(',
                    "Development-level debug variables prints left inside files",
                    "Strip debug elements before continuous delivery pipeline pushes. Switch logical flags to logging files.",
                    SEV_LOW, "Code Quality", "PHP-DEBUG-PRINTS"
                ),
                (
                    r'\b(echo|print)\s+.*\$_(GET|POST|REQUEST)',
                    "Raw unfiltered echo output of global parameter arrays (XSS)",
                    "Sanitize dynamic context layers before returning HTML nodes. Render elements securely inside helper filters: `htmlspecialchars()`.",
                    SEV_HIGH, "A03:2021-Injection", "PHP-XSS-ECHO"
                ),
                (
                    r'(include|require)(_once)?\s*\(?\s*\$_(GET|POST|REQUEST)',
                    "Dynamic relative files inclusion parameter in raw variables (LFI)",
                    "Do not evaluate inputs inside structural require patterns. Strictly map keys to safe server-side file structures.",
                    SEV_CRITICAL, "A03:2021-Injection", "PHP-LFI-INCLUSION"
                )
            ]
        elif language == "java":
            rules = [
                (
                    r'Runtime\.getRuntime\(\)\.exec\s*\(',
                    "Unsafe execution of dynamic base commands via system process",
                    "Reroute structures away from shell processes. Use API routines, or clean variables passing parameter structures as lists.",
                    SEV_HIGH, "A03:2021-Injection", "JAVA-SHELL-EXEC"
                ),
                (
                    r'ProcessBuilder\s*\(',
                    "Custom runtime system builder process instantiated",
                    "Ensure execution sequences do not build shell runs from raw concatenated string parameters that can be manipulated.",
                    SEV_MEDIUM, "A03:2021-Injection", "JAVA-PROCESS-BUILDER"
                ),
                (
                    r'System\.(out|err)\.print(ln)?\s*\(',
                    "Standard outputs target debugger declared in context (`System.out.println`)",
                    "Port raw standard outputs to framework-level modern handlers such as logging configurations (SLF4J, Logback).",
                    SEV_LOW, "Code Quality", "JAVA-STDOUT-LOGGER"
                ),
                (
                    r'Cipher\.getInstance\s*\(\s*["\'](DES|ARC4|Blowfish|RC4)',
                    "Weak symmetric decryption hashing configured",
                    "Transition core cryptosystems to modern strong security standard mechanisms (e.g. `AES/GCM/NoPadding`).",
                    SEV_HIGH, "A02:2021-Cryptographic Failures", "JAVA-WEAK-CIPHER"
                ),
                (
                    r'MessageDigest\.getInstance\s*\(\s*["\'](MD5|SHA-1)',
                    "Weak security hash instance activated",
                    "Migrate weak algorithms over to standard modern structures (using SHA-256 or SHA-512 values).",
                    SEV_MEDIUM, "A02:2021-Cryptographic Failures", "JAVA-WEAK-HASH"
                ),
                (
                    r'\.printStackTrace\s*\(\s*\)',
                    "Standard stack trace display dump printed to output stream",
                    "Log internal execution stack variables directly into centralized server system logs instead of dumping traces to standard output.",
                    SEV_MEDIUM, "A09:2021-Security Logging and Monitoring Failures", "JAVA-PRINT-STACK-TRACE"
                )
            ]
        elif language == "go":
            rules = [
                (
                    r'\bunsafe\.Pointer\b',
                    "Unsafe memory interface utilized (`unsafe.Pointer`)",
                    "Limit compilation structures requiring unsafe pointers, exception-checked only because they bypass standard system type checks.",
                    SEV_MEDIUM, "Code Quality", "GO-UNSAFE"
                ),
                (
                    r'\bos/exec\.Command\b',
                    "Exec library processing initialized to system environment commands",
                    "Verify shell elements pass array criteria explicitly. Block concatenating strings to prevent terminal escapes.",
                    SEV_MEDIUM, "A03:2021-Injection", "GO-EXEC-COMMAND"
                ),
                (
                    r'db\.Query\s*\(.*fmt\.Sprintf\b',
                    "Dynamic raw context embedded within execution queries (SQL Injection)",
                    "Replace raw SQL string rendering with argument arrays directly passed through query arrays like `db.Query(\"SELECT... WHERE id = ?\", id)`.",
                    SEV_CRITICAL, "A03:2021-Injection", "GO-SQL-INJECT"
                ),
                (
                    r'\bpanic\s*\(',
                    "Application panic state called during flows",
                    "In production systems, panic halts processing. Use Go standard multiple return patterns, responding through standard error interface types.",
                    SEV_LOW, "Code Quality", "GO-PANIC"
                )
            ]
        elif language == "cpp_c":
            rules = [
                (
                    r'\b(strcpy|strcat)\s*\(',
                    "Highly vulnerable base string function in use",
                    "Avoid buffer overflow liabilities. Switch standard pointers to bounded alternative operations: `strncpy()` or `strncat()`.",
                    SEV_HIGH, "A06:2021-Vulnerable and Outdated Components", "C-BUFFER-OVERFLOW"
                ),
                (
                    r'\bgets\s*\(',
                    "Obsolete, high-vulnerability standard reading trigger `gets()`",
                    "Using `gets` is dangerous since buffer lines are unbounded. Replace executions immediately with safe alternatives: `fgets()`.",
                    SEV_CRITICAL, "A06:2021-Vulnerable and Outdated Components", "C-GETS"
                ),
                (
                    r'\b(sprintf|vsprintf)\s*\(',
                    "Vulnerable standard buffer translation execution",
                    "Ensure buffers do not overflow. Protect output arrays by using safe arguments: `snprintf` or alternative safe wrappers.",
                    SEV_HIGH, "A06:2021-Vulnerable and Outdated Components", "C-SPRINTF"
                ),
                (
                    r'\bsystem\s*\(',
                    "Base platform system subshell utility launched",
                    "Avoid command injections by replacing system queries with system APIs like `execve()` or dedicated platform-native features.",
                    SEV_HIGH, "A03:2021-Injection", "C-SYSTEM-EXEC"
                )
            ]
        elif language == "ruby":
            rules = [
                (
                    r'\beval\s*\(',
                    "Insecure statement interpreter evaluation executed",
                    "Replace runtime evaluation flows by utilizing structured helper classes and explicit parsing blocks.",
                    SEV_HIGH, "A03:2021-Injection", "RUBY-EVAL"
                ),
                (
                    r'\b(system|exec)\s*\(|`.*`|%\x',
                    "OS dynamic shell executor instantiated",
                    "Utilize target executions where separate parameters are structured inside arrays rather than raw string structures to prevent shell escape sequences.",
                    SEV_HIGH, "A03:2021-Injection", "RUBY-EXEC"
                ),
                (
                    r'\.execute\s*\(.*#\{',
                    "Dynamically interpolated string statement constructed for database execution",
                    "Avert SQL injection vulnerabilities. Standardize queries under model scopes by utilizing secure bind values: `where(\"id = ?\", id)`.",
                    SEV_CRITICAL, "A03:2021-Injection", "RUBY-SQL-INJECT"
                )
            ]
        elif language == "html_css":
            rules = [
                (
                    r'<script>(?!.*Content-Security-Policy)',
                    "Inline HTML script container elements compiled without CSP configuration",
                    "Ensure standard script items are isolated. Try referencing script codes strictly through source URLs combined with strict SHA hashes.",
                    SEV_MEDIUM, "A05:2021-Security Misconfiguration", "HTML-INLINE-SCRIPT"
                ),
                (
                    r'<iframe\s+.*src\s*=\s*["\']http://',
                    "Iframe loads resources with obsolete unsecure protocols (`http://`)",
                    "Convert references over to HTTPS to ensure modern browser standards protect frames against mixed content security blocks.",
                    SEV_LOW, "A05:2021-Security Misconfiguration", "HTML-HTTP-IFRAME"
                ),
                (
                    r'autocomplete\s*=\s*["\']off["\']',
                    "Credential input auto-complete attribute disabled",
                    "Modern specifications suggest allowing autocompleting forms to utilize password management managers.",
                    SEV_LOW, "Code Quality", "HTML-AUTOCOMPLETE"
                ),
                (
                    r'url\(\s*["\']?http://',
                    "CSS module loads web properties with vulnerable standard protocols",
                    "Migrate asset referencing schemes to standard secure layers: SSL URL elements (`https://`).",
                    SEV_LOW, "A05:2021-Security Misconfiguration", "CSS-HTTP-RESOURCE"
                )
            ]
        elif language == "shell":
            rules = [
                (
                    r'\beval\s+\$',
                    "Evaluating variables directly within standard shell script loops",
                    "Evaluating dynamic inputs with `eval` is dangerous and command Injection vulnerabilities can easily occur. Verify inputs strictly.",
                    SEV_HIGH, "A03:2021-Injection", "SHELL-EVAL"
                ),
                (
                    r'(curl|wget)\s+.*\|\s*(bash|sh)\b',
                    "Unsecured remote installation trigger (piping fetched codes to subshell)",
                    "Never direct dynamic fetch code layers directly into interpreter pipes. Instruct clients to fetch resource contents and review them prior to running.",
                    SEV_HIGH, "A08:2021-Software and Data Integrity Failures", "SHELL-CURL-PIPE"
                ),
                (
                    r'\bset\s*\-\s*e\b',
                    "Missing basic error safety triggers inside script sequences",
                    "Consider utilizing global configuration flags: `set -e` ensures structural issues halt executions rather than carrying errors forward.",
                    SEV_INFO, "Code Quality", "SHELL-SET-E"
                )
            ]
        return rules

    def _update_structure_metrics(self, line: str, language: str, metric: FileMetrics):
        """Naive estimation of functions and classes count using typical language keywords."""
        if language == "python":
            if line.startswith("def "):
                metric.functions_count += 1
            elif line.startswith("class "):
                metric.classes_count += 1
        elif language in {"javascript_typescript", "go"}:
            if "function " in line or "const " in line and "=>" in line:
                metric.functions_count += 1
            elif "class " in line or "interface " in line:
                metric.classes_count += 1
        elif language == "php":
            if "function " in line:
                metric.functions_count += 1
            elif "class " in line or "trait " in line:
                metric.classes_count += 1
        elif language == "java":
            # Very loose estimate for functions (methods)
            if re.search(r'\b(public|private|protected|static)\s+[\w<>]+\s+\w+\s*\(', line):
                metric.functions_count += 1
            elif "class " in line or "interface " in line:
                metric.classes_count += 1
        elif language == "cpp_c":
            if re.search(r'\b(int|void|char|double|float|bool|string)\s+\w+\s*\(', line) and ";" not in line:
                metric.functions_count += 1
            elif "class " in line or "struct " in line:
                metric.classes_count += 1
        elif language == "ruby":
            if line.startswith("def "):
                metric.functions_count += 1
            elif line.startswith("class ") or line.startswith("module "):
                metric.classes_count += 1

    def _calculate_complexity(self, line: str, language: str, metric: FileMetrics):
        """McCabe Complexity estimation logic based on decision points."""
        keywords = {"if", "elif", "else if", "for", "while", "catch", "case", "&&", "||", "and", "or"}
        
        # Adjust indicators depending on language syntax
        for keyword in keywords:
            # Match word bounds or special logical symbol sequences
            if keyword in {"&&", "||"}:
                metric.complexity += line.count(keyword)
            else:
                pattern = r'\b' + keyword + r'\b'
                matches = re.findall(pattern, line)
                metric.complexity += len(matches)

    def _compile_summary(self) -> Dict[str, int]:
        total_loc = sum(f.loc for f in self.metrics.values())
        total_comments = sum(f.comment_lines for f in self.metrics.values())
        total_blanks = sum(f.blank_lines for f in self.metrics.values())
        
        severity_counts = {
            SEV_CRITICAL: 0,
            SEV_HIGH: 0,
            SEV_MEDIUM: 0,
            SEV_LOW: 0,
            SEV_INFO: 0
        }
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        lang_counts = {}
        for f in self.metrics.values():
            lang_name = self.LANG_DISPLAY_NAMES.get(f.language, f.language)
            lang_counts[lang_name] = lang_counts.get(lang_name, 0) + 1

        return {
            "total_files": self.scanned_files_count,
            "ignored_files": self.ignored_files_count,
            "total_loc": total_loc,
            "total_comments": total_comments,
            "total_blanks": total_blanks,
            "critical_findings": severity_counts[SEV_CRITICAL],
            "high_findings": severity_counts[SEV_HIGH],
            "medium_findings": severity_counts[SEV_MEDIUM],
            "low_findings": severity_counts[SEV_LOW],
            "info_findings": severity_counts[SEV_INFO],
            "total_findings": len(self.findings),
            "languages_scanned": len(lang_counts)
        }
