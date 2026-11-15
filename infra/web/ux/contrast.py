# ruff: noqa: E701, E702, E731
"""WCAG 2.x contrast ratios for ART FARM colour pairs (alpha-composited). Prints a markdown table (docs/UX-AUDIT.md 3.6)."""


def h(c):
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def blend(fg, a, bg):
    return tuple(round(f * a + b * (1 - a)) for f, b in zip(fg, bg))


def L(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = map(ch, c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def cr(a, b):
    la, lb = sorted([L(a), L(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


W = h("ffffff")
F = h("173a2b")
S = h("f3f5ee")
rows = [
    ("slate-500 #64748b on white (captions, P10–P90 small text)", h("64748b"), W, "small"),
    ("slate-500 on #f3f5ee results bg (tier1 tiles)", h("64748b"), S, "small"),
    ("slate-400 #94a3b8 on white ('information gap', '(assumption)', units)", h("94a3b8"), W, "small"),
    ("slate-600 #475569 on white", h("475569"), W, "small"),
    ("amber-700 #b45309 on white ('screening estimate')", h("b45309"), W, "small"),
    ("#5a9e2e on white ('TIER 1 · QUICK SCREEN')", h("5a9e2e"), W, "small"),
    ("#2f6b1d on #82c341@20% over white ('matches your crops')", h("2f6b1d"), blend(h("82c341"), 0.2, W), "small"),
    ("amber-900 #78350f on amber-100 #fef3c7 (SCREENING ESTIMATE pill)", h("78350f"), h("fef3c7"), "small"),
    ("#0f291e on #82c341 (primary CTA)", h("0f291e"), h("82c341"), "large"),
    ("white on #173a2b (dark buttons, toast)", W, F, "small"),
    ("amber-300 #fcd34d on #173a2b", h("fcd34d"), F, "small"),
    ("emerald-100/80 on #173a2b (Tier 2 run line)", blend(h("d1fae5"), 0.8, F), F, "small"),
    (
        "emerald-100/60 on white/10 over #173a2b (model id, disclaimer)",
        blend(h("d1fae5"), 0.6, blend(W, 0.1, F)),
        blend(W, 0.1, F),
        "small",
    ),
    ("emerald-100/75 on #173a2b (preset note)", blend(h("d1fae5"), 0.75, F), F, "small"),
    ("white on white/12 over #173a2b (preset buttons)", W, blend(W, 0.12, F), "small"),
    ("white on emerald-950/20 over #74b93d (story badge)", W, blend(h("022c22"), 0.2, h("74b93d")), "small"),
    ("#102a1b on white/25 over #74b93d (story badge)", h("102a1b"), blend(W, 0.25, h("74b93d")), "small"),
    ("emerald-200/70 on #183829 (endpoint mono 11px)", blend(h("a7f3d0"), 0.7, h("183829")), h("183829"), "small"),
    ("slate-500 on amber-50 #fffbeb (S7 note)", h("64748b"), h("fffbeb"), "small"),
    ("amber-800 #92400e on white (Trade-offs)", h("92400e"), W, "small"),
    ("emerald-800 #065f46 on white (Benefits)", h("065f46"), W, "small"),
    ("slate-700 on white", h("334155"), W, "small"),
    ("non-text: P10–P90 bar rgba(36,84,62,.25) on white", blend(h("24543e"), 0.25, W), W, "ui"),
    ("non-text: matched bar rgba(130,195,65,.55) on white", blend(h("82c341"), 0.55, W), W, "ui"),
    ("non-text: bar border #24543e on white", h("24543e"), W, "ui"),
    (
        "non-text: user polygon fill #7dd3a8@.38 vs dark field #2c3a24 (approx.)",
        blend(h("7dd3a8"), 0.38, h("2c3a24")),
        h("2c3a24"),
        "ui",
    ),
    ("non-text: user polygon stroke #f7f6f0 vs dark field #2c3a24", h("f7f6f0"), h("2c3a24"), "ui"),
    ("non-text: pilot outline #f2c46d vs dark field #2c3a24", h("f2c46d"), h("2c3a24"), "ui"),
    # after phase-2 fixes
    ("AFTER slate-600 #475569 on white ('information gap', ranges)", h("475569"), W, "small"),
    ("AFTER slate-600 on #f3f5ee (Tier 1 tiles, footer)", h("475569"), S, "small"),
    ("AFTER slate-500 on white ('(assumption)', units)", h("64748b"), W, "small"),
    ("AFTER #3d7a1f on white ('TIER 1 · QUICK SCREEN')", h("3d7a1f"), W, "small"),
    ("AFTER emerald-100/80 on white/10 over #173a2b (model id)", blend(h("d1fae5"), 0.8, blend(W, 0.1, F)), blend(W, 0.1, F), "small"),
    ("AFTER #102a1b on white/25 over #74b93d (story badge)", h("102a1b"), blend(W, 0.25, h("74b93d")), "small"),
    ("AFTER #0f291e on #82c341 (hero CTA)", h("0f291e"), h("82c341"), "small"),
    ("AFTER amber-950 #451a03 on amber-100 (static banner)", h("451a03"), h("fef3c7"), "small"),
    ("disabled CTA (opacity .4) — exempt", h("0f291e"), blend(h("82c341"), 0.4, h("f7f6f0")), "exempt"),
]
need = {"small": 4.5, "large": 3.0, "ui": 3.0, "exempt": 0}
print("| Pair | Ratio | Need | Result |\n| --- | ---: | ---: | --- |")
for n, a, b, k in rows:
    r = cr(a, b)
    print(f"| {n} | {r:.2f}:1 | {need[k]} | {'PASS' if r >= need[k] else 'FAIL'} |")
