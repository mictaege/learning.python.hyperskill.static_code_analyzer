# write your code here
import ast
import os
import re
import sys
from _ast import Module, AST
from re import RegexFlag

CAMEL_CASE = '^[A-Z][a-zA-Z]*$'
SNAKE_CASE = '^(_*[a-z]+[a-z_0-9]*|[a-z]+(_[a-z0-9]+)*)$'


class Violation:
    def __init__(self, src_path, line_no, code, message):
        self.src_path = src_path
        self.line_no = line_no
        self.code = code
        self.message = message

    def __str__(self):
        return f"{self.src_path}: Line {self.line_no}: {self.code} {self.message}"


class LineCheck:

    def check(self, src_path, source) -> [Violation]:
        violations: [Violation] = []
        line_no = 1
        for line in source.splitlines():
            violation = self.check_line(src_path, line, line_no)
            if violation:
                violations.append(violation)
            line_no += 1
        return violations

    def check_line(self, src_path, line, line_no) -> Violation:
        pass


class AstCheck:

    def check(self, src_path, source) -> [Violation]:
        violations: [Violation] = []
        tree: Module | AST = ast.parse(source)
        for node in ast.walk(tree):
            violation = self.check_node(src_path, node)
            if violation:
                violations.append(violation)
        return violations

    def check_node(self, src_path, node) -> Violation:
        pass


class LengthCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        if len(line) > 79:
            return Violation(src_path, line_no, "S001", "Too Long")


class IndentCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        if (len(line) - len(line.lstrip(' '))) % 4 != 0:
            return Violation(src_path, line_no, "S002", "Indentation is not a multiple of four")


class SemicolonCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        if re.search(r'^[^#]*;\s*(?=#|$)', line):
            return Violation(src_path, line_no, "S003", "Unnecessary semicolon after a statement")


class SpacesBeforeCommentCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        if "#" in line and not line.strip().startswith("#"):
            code_part = line.split("#", maxsplit=1)[0]
            if not code_part.endswith("  "):
                return Violation(src_path, line_no, "S004", "Less than two spaces before inline comments")


class TodoCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        if re.search(r'#.*TODO', line, RegexFlag.IGNORECASE):
            return Violation(src_path, line_no, "S005", "TODO found")


class TwoManyBlankLinesCheck(LineCheck):

    def check(self, src_path, source) -> [Violation]:
        violations: [Violation] = []
        lines = source.splitlines()
        idx = 0
        for line in lines:
            if idx > 2 and line and not lines[idx - 1].strip() and not lines[idx - 2].strip() and not lines[
                idx - 3].strip():
                message = "More than two blank lines preceding a code line"
                violations.append(Violation(src_path, idx + 1, "S006", message))
            idx += 1
        return violations


class ConstructionSpaceCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        if line.strip().startswith("class"):
            if re.search(r'class\s\s+.*', line.strip()):
                return Violation(src_path, line_no, "S007", "Too many spaces after 'class'")
        if line.strip().startswith("def"):
            if re.search(r'def\s\s+.*', line.strip()):
                return Violation(src_path, line_no, "S007", "Too many spaces after 'def'")


class ClassNameCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        match = re.search(r'class\s+(\w+):', line)
        if match and not re.match(CAMEL_CASE, match.group(1)):
            return Violation(src_path, line_no, "S008", f"Class name '{match.group(1)}' should use CamelCase")


class FunctionNameCheck(LineCheck):

    def check_line(self, src_path, line, line_no) -> Violation:
        match = re.search(r'def\s+([\w_]+)\(', line)
        if match and not re.match(SNAKE_CASE, match.group(1)):
            return Violation(src_path, line_no, "S009", f"Function name '{match.group(1)}' should use snake_case")


class ArgumentNameCheck(AstCheck):

    def check_node(self, src_path, node) -> Violation:
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if not re.match(SNAKE_CASE, arg.arg):
                    return Violation(src_path, node.lineno, "S010", "Argument name should use snake_case")


class VariableNameCheck(AstCheck):

    def check_node(self, src_path, node) -> Violation:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if not re.match(SNAKE_CASE, target.id):
                        return Violation(src_path, node.lineno, "S011", "Variable should be written in snake_case")


class DefaultMutableCheck(AstCheck):

    def check_node(self, src_path, node) -> Violation:
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    return Violation(src_path, node.lineno, "S012", "Default argument value is mutable")


class Analyzer:
    def __init__(self, src_path):
        self.src_path = src_path
        self.checks = [LengthCheck(), IndentCheck(), SemicolonCheck(), SpacesBeforeCommentCheck(),
                       TodoCheck(), TwoManyBlankLinesCheck(), ConstructionSpaceCheck(),
                       ClassNameCheck(), FunctionNameCheck(), ArgumentNameCheck(),
                       VariableNameCheck(), DefaultMutableCheck()]

    def check(self):
        violations: [Violation] = []
        with open(self.src_path, 'r') as file:
            source = file.read()
            for check in self.checks:
                for violation in check.check(self.src_path, source):
                    violations.append(violation)
        sorted_sorted = sorted(violations, key=lambda v: v.line_no)
        for violation in sorted_sorted:
            print(violation)


args = sys.argv
path_arg = args[1]
if os.path.isdir(path_arg):
    for root, dirs, files in os.walk(path_arg):
        for name in files:
            path = os.path.join(root, name)
            analyzer = Analyzer(path)
            analyzer.check()
elif os.path.isfile(path_arg):
    analyzer = Analyzer(path_arg)
    analyzer.check()
