# Tools — paper lane

Cloned shallowly (`--depth 1`) into `/srv/hackathon/paper/tools/` (outside the repo). Nothing was installed from them, no GPU or paid keys were used, and **no code from any of them was copied into this repo**.

| Repo | Licence | Used? | How |
| --- | --- | --- | --- |
| K-Dense-AI/claude-scientific-writer | MIT | **Yes (guidance only)** | `skills/citation-management/references/citation_validation.md` checklist (DOI resolves; title/authors/year match the record) was the acceptance rule for the OpenAlex verification. `skills/peer-review/SKILL.md` "no fabricated citations/analyses" rule applied to the evidence policy. |
| google-research/paper-orchestra | Apache-2.0 | No | Structure inspected (autoraters). Not run. |
| SakanaAI/AI-Scientist-v3 | Apache-2.0 | No | Licence and layout inspected only. |
| aiming-lab/AutoResearchClaw | MIT | No | Licence inspected only. |
| federicodeponte/opendraft | MIT | No | Licence inspected only. |
| htlin222/meta-pipe | Academic & Non-Commercial licence | No | NC licence — deliberately not used. |

## Actually used for production

- **Claude Code** (drafting the LaTeX text from repo artifacts).
- **Tectonic 0.15.0** (XeTeX-based, static musl binary downloaded to `/srv/hackathon/paper/bin/`, no install). No `pdflatex`, `pandoc` or `tectonic` was on PATH. First attempt with `kotex` failed (`failed to create linebreak iterator`); fixed by using `fontspec` + system font *WenQuanYi Zen Hei* for the Korean team name only. Bibliography: BibTeX with `plainnat` (run by Tectonic).
- **OpenAlex API** via a small stdlib Python script (`/srv/hackathon/paper/scripts/verify.py`, not committed); key read from the secrets file at runtime only and never logged. DataCite fallback was coded but not needed (all 40 DOIs resolved in OpenAlex).
- `pdfinfo` (page count).

## Build

```
cd docs/paper && tectonic artfarm_paper.tex
```
