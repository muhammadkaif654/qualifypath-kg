# Final report (LaTeX) — how to build it on Overleaf

The whole report is in this folder. `main.tex` pulls in one file per section (`sections/`), the figures
(`figures/`) and tables that are **generated from the real results** (`generated/`). Nothing in `generated/`
should be typed by hand.

## 1. Upload to Overleaf (first time)

1. Go to https://www.overleaf.com and sign in (a free account is enough).
2. Click **New Project → Upload Project** and choose **`Report/QualifyPath_Report_Overleaf.zip`**.
3. Overleaf opens the project and compiles it. If it does not, open **Menu** (top left) and check:
   - **Compiler:** `pdfLaTeX`
   - **Main document:** `main.tex`

   then click **Recompile**. The bibliography is built automatically.
4. The PDF appears on the right. Warnings (yellow) are normal; errors (red) are not — see section 5.

## 2. Fill in the missing values (only `config.tex`)

Open `config.tex` and replace:

| Placeholder | Replace with |
| --- | --- |
| `TALHA-GITHUB-USERNAME`, `HASEEB-GITHUB-USERNAME` | your teammates' GitHub usernames |
| `\commitsTalha`, `\commitsHaseeb` | links to 2–4 of their commits, e.g. `\href{https://github.com/muhammadkaif654/qualifypath-kg/commit/abc1234}{\texttt{abc1234}} ontology \newline ...` |
| `https://ADD-YOUR-DEMO-VIDEO-LINK` | the link to your 3–5 minute demo video (YouTube unlisted or Google Drive "anyone with the link") |

Keep URLs inside `\url{...}` or `\href{...}{...}`; in normal text write `\_` for `_` and `\&` for `&`.

## 3. Work on it with your teammates

Click **Share** (top right) → enter their emails → **Can edit**. Everyone edits the same project live.
Each person can check and improve the section about their own work:

| Member | Sections |
| --- | --- |
| Talha | `02_dataset.tex`, `06_multihop.tex`, the inference examples in `05_sparql_inference.tex` |
| Haseeb | `03_competency_questions.tex`, `04_ontology_kg.tex`, `08_evaluation.tex`, `09_explainability.tex` |
| Kaif | `01_introduction.tex`, `05_sparql_inference.tex`, `07_application.tex`, `10_limitations.tex`, `11_contributions.tex` |

## 4. After the final push to GitHub (update hash, commits, results)

The title page shows the final submission commit, and Appendix C lists every commit. These come from git, so
after the **last** push:

```bash
python Report/latex/make_assets.py
```

Then, in Overleaf, open the `generated` folder → **Upload** → select all files from
`Report/latex/generated/` (choose **overwrite**). Do the same for `figures/` if any screenshot changed.
Alternatively, upload the refreshed zip as a new project.

## 5. Download and submit

Click the **Download PDF** icon next to *Recompile*, rename it to
`AI3001_Iteration2_QualifyPath-KG.pdf`, and upload **only this PDF** to Google Classroom.

## Troubleshooting

| Error in the log | Fix |
| --- | --- |
| `File 'figures/....png' not found` | upload the missing image into `figures/` |
| `Misplaced alignment tab character &` | you typed `&` in text — write `\&` |
| `Missing $ inserted` | an `_` or `^` in normal text — write `\_` / `\^{}` |
| `Undefined control sequence \ghTalha` (or similar) | `config.tex` was not uploaded or a line was deleted |
| References show `[?]` | click Recompile once more (the bibliography needs two passes) |
