"""Static checks for the team MATLAB scripts (MATLAB/Octave cannot run on this server).

Checks: balanced block/`end` keywords (indexing `end` ignored), no interactive
calls, script name != local function name, local functions only after script
code, IDs read as text, container (/data) paths only, no archive-less overwrite.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MATLAB_DIR = Path(__file__).resolve().parents[2] / "matlab"
SCRIPTS = sorted(MATLAB_DIR.glob("*.m"))
MAT2_OUTPUTS = {
    "yoonsung_nldas_2012.m": ("nldas_vs_engine_2012.png", "nldas_vs_engine_2012.csv"),
    "yoonsung_season_anomaly.m": ("season_anomaly_1995_2025.png", "season_anomaly_1995_2025.csv"),
    "yoonsung_s2s_box.m": ("s2s_vs_history_box.png", "s2s_vs_history_box.csv"),
    "jimin_growing_season.m": ("growing_season_20fields.csv", "jimin_supported_daily.csv"),
    "jimin_ndvi_anomaly.m": ("jimin_ndvi_anomaly.csv", "ndvi_anomaly.png"),
    "jimin_bare_vs_rye.m": ("bare_vs_strategyB.csv", "jimin_strategyB_assumptions_used.csv"),
}
OPENERS = {"function", "if", "for", "parfor", "while", "switch", "try", "spmd"}
INTERACTIVE = re.compile(
    r"\b(ginput|input|keyboard|waitforbuttonpress|uiwait|inputdlg|questdlg|"
    r"uigetfile|uiputfile|listdlg|msgbox|pause\s*\(\s*\))\s*\("
)


def _strip(line: str) -> str:
    """Remove comments and string literals (handles transpose vs quote)."""
    out, i, prev = [], 0, ""
    while i < len(line):
        c = line[i]
        if c == "%":
            break
        if line.startswith("...", i):
            break
        if c == '"' or (c == "'" and not re.match(r"[\w\)\]\}'.]", prev or " ")):
            j = i + 1
            while j < len(line):
                if line[j] == c:
                    if j + 1 < len(line) and line[j + 1] == c:
                        j += 2
                        continue
                    break
                j += 1
            out.append(" S ")
            i, prev = j + 1, "S"
            continue
        out.append(c)
        if not c.isspace():
            prev = c
        i += 1
    return "".join(out)


def _code_lines(path: Path) -> list[str]:
    lines, in_block = [], False
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s == "%{":
            in_block = True
            continue
        if s == "%}":
            in_block = False
            continue
        lines.append("" if in_block else _strip(raw))
    return lines


def _top_level_tokens(line: str, depth: list[int]) -> list[str]:
    """Keywords outside ()/{}/[] (where `end` means last index)."""
    toks = []
    for m in re.finditer(r"[A-Za-z_]\w*|[()\[\]{}]", line):
        t = m.group()
        if t in "([{":
            depth[0] += 1
        elif t in ")]}":
            depth[0] = max(0, depth[0] - 1)
        elif depth[0] == 0:
            prev = line[: m.start()].rstrip()
            if prev.endswith("."):  # struct field such as s.end / s.if
                continue
            toks.append(t)
    return toks


def _analyse(path: Path) -> dict:
    stack: list[str] = []
    functions: list[str] = []
    code_after_function = []
    first_code_is_function = None
    paren = [0]
    for no, line in enumerate(_code_lines(path), 1):
        if not line.strip():
            continue
        toks = _top_level_tokens(line, paren)
        if first_code_is_function is None and toks:
            first_code_is_function = toks[0] == "function"
        if toks and toks[0] != "function" and not stack and functions:
            code_after_function.append(no)
        for t in toks:
            if t in OPENERS:
                if t == "function":
                    m = re.search(r"function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?(\w+)", line)
                    functions.append(m.group(1) if m else "?")
                stack.append(t)
            elif t == "end":
                assert stack, f"{path.name}:{no}: unmatched end"
                stack.pop()
    return {
        "unclosed": stack,
        "functions": functions,
        "is_script": not first_code_is_function,
        "code_after_function": code_after_function,
        "paren": paren[0],
    }


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_blocks_balanced(path: Path) -> None:
    a = _analyse(path)
    assert not a["unclosed"], f"unclosed blocks: {a['unclosed']}"
    assert a["paren"] == 0, "unbalanced brackets"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_no_name_clash_and_function_order(path: Path) -> None:
    a = _analyse(path)
    stem = path.stem
    if a["is_script"]:
        assert stem not in a["functions"], f"script name clashes with local function {stem}"
        assert not a["code_after_function"], f"script code after local functions: {a['code_after_function']}"
    else:
        assert a["functions"][0] == stem, "function file: first function must match file name"
    assert len(a["functions"]) == len(set(a["functions"])), "duplicate local function names"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_no_interactive_calls(path: Path) -> None:
    code = "\n".join(_code_lines(path))
    assert not INTERACTIVE.search(code), INTERACTIVE.search(code)
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    for m in re.finditer(r"\bfigure\s*\(", code):
        line = code[: m.start()].count("\n")
        # Read continued property lists too; merely mentioning Visible or
        # setting it to 'on' must not satisfy the headless execution contract.
        call = "\n".join(raw_lines[line:]).split(")", 1)[0]
        assert re.search(r"['\"]Visible['\"]\s*,\s*['\"]off['\"]", call, re.I), (
            "figure() must be created with 'Visible','off'"
        )


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_ids_as_text_and_container_paths(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "readtable(" in text:
        assert re.search(r"setvartype\([^\n]*field_id[^\n]*'string'", text) or re.search(
            r"setvartype\(opts, idCols, 'string'\)", text
        ), "field_id must be read as string"
    for lit in re.findall(r"'(/[^']*)'", text):
        if lit.startswith("/"):
            assert lit.startswith("/data/"), f"non-container path {lit}"
    assert "/srv/" not in text, "server path leaked into MATLAB script"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_overwrite_policy_archives(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "Refusing to overwrite" not in text
    assert "createNewFile" not in text
    if re.search(r"\b(writetable|exportgraphics)\(", text):
        assert "archive_existing_outputs(" in text


@pytest.mark.parametrize("name,outputs", MAT2_OUTPUTS.items(), ids=MAT2_OUTPUTS)
def test_mat2_required_outputs_and_archive_before_write(name: str, outputs: tuple[str, ...]) -> None:
    path = MATLAB_DIR / name
    assert path.is_file(), f"Missing required MAT2 script: {name}"
    text = path.read_text(encoding="utf-8")
    code = "\n".join(_code_lines(path))
    for output in outputs:
        assert re.search(r"['\"]" + re.escape(output) + r"['\"]", text), output
    writes = list(re.finditer(r"\b(writetable|exportgraphics)\s*\(", code))
    assert writes, "script must emit its deliverables"
    archive = re.search(r"(?m)^\s*archive_existing_outputs\s*\(", code)
    assert archive and archive.start() < writes[0].start(), "archive before first output write"
    helper = re.search(r"(?m)^\s*function\s+archive_existing_outputs\s*\(", code)
    assert helper, "archive helper is required"
    helper_code = code[helper.start():]
    assert re.search(r"\bmovefile\s*\(", helper_code), "archive must move previous outputs"
    assert re.search(r"\bisfile\b", helper_code), "only archive existing files"
    assert re.search(r"fullfile\(outputDir,\s*['\"]old['\"],\s*stamp\)", text), (
        "archive outputs under old/<timestamp>"
    )
