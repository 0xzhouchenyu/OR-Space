# OR-Space Public Release Checklist

Use this checklist before publishing a new GitHub and Hugging Face snapshot.

## 1. GitHub Project Page

- Confirm the public repository URL is `https://github.com/0xzhouchenyu/OR-Space`.
- Add or confirm a root `LICENSE` file. The current dataset terms are
  CC BY-NC 4.0-compatible, which is a non-commercial research release rather
  than an OSI open-source license.
- Check that `README.md` renders with the images in `supporting_files/assets/`.
- Set repository topics: `operations-research`, `optimization`, `benchmark`,
  `llm-agents`, `agent-evaluation`, `mathematical-optimization`.
- Add a repository social preview image using
  `supporting_files/assets/or_space_overview.png` or a cropped
  project banner.
- Replace the "Paper coming soon" line once the arXiv URL is live.
- Create a GitHub release or tag that matches the Hugging Face dataset snapshot.

## 2. Hugging Face Dataset Page

- Confirm the dataset repo exists:

```bash
hf repos create Chenyu-Zhou/OR-Space --type dataset --exist-ok
```

- Upload the staged dataset directory:

```bash
hf upload Chenyu-Zhou/OR-Space hf_dataset --repo-type dataset \
  --commit-message "Prepare OR-Space public release"
```

- Create an immutable tag for the paper snapshot after validation:

```bash
hf repos tag create Chenyu-Zhou/OR-Space neurips2026-submission \
  --type dataset \
  --message "OR-Space NeurIPS 2026 submission snapshot"
```

- Verify on the Hub that:
  - The dataset card renders without YAML metadata warnings.
  - The license displays as `cc-by-nc-4.0`.
  - `assets/or_space_logo.png`, `assets/or_space_overview.png`, and
    `assets/task_visibility.png` render correctly.
  - The dataset viewer loads `metadata/workspace_index.csv`.
  - `build-revise-explain_workspaces.zip` is tracked with LFS.
  - `explain_rubrics/rubrics.jsonl` contains 100 complete rubrics.
  - `oracle/build_revise_objectives.csv` contains 200 references.

## 3. Package Hygiene and Visibility

- Regenerate the participant archive from the authoring archive:

```bash
python tools/stage_participant_workspaces.py \
  --source EXTRACTED_AUTHORING_ROOT \
  --output STAGED_PARTICIPANT_ROOT \
  --source-id IMMUTABLE_SOURCE_ID
```

- Confirm Build has no reference source, Revise exposes only the correct
  original heuristic/utility/runtime code, revised reference source is absent,
  and Explain participant metadata has no checklist or reference answer.

- Confirm the zip archive has no macOS metadata:

```bash
python - <<'PY'
import zipfile

with zipfile.ZipFile("hf_dataset/build-revise-explain_workspaces.zip") as zf:
    names = zf.namelist()
bad = [n for n in names if n.startswith("__MACOSX/") or n.endswith(".DS_Store")]
print(f"bad entries: {len(bad)}")
assert not bad
PY
```

- Run the release validator and evaluator tests:

```bash
python -m unittest discover -s tests -v
python tools/validate_public_release.py \
  --rubrics HF_REPO/explain_rubrics/rubrics.jsonl \
  --participant-root STAGED_PARTICIPANT_ROOT
```

- Recompute checksums after any file change:

```bash
shasum -a 256 \
  hf_dataset/build-revise-explain_workspaces.zip \
  hf_dataset/metadata/workspace_index.csv \
  hf_dataset/croissant.json \
  hf_dataset/README.md
```

- Update `hf_dataset/metadata/release_manifest.json` if any byte size or hash
  changes.

## 4. Paper Synchronization

- Confirm `arxiv.tex` links to:
  - `https://huggingface.co/datasets/Chenyu-Zhou/OR-Space`
  - `https://github.com/0xzhouchenyu/OR-Space`
- Replace the placeholder BibTeX in both README files with the final arXiv or
  proceedings citation.
- Cite the immutable Hugging Face tag or commit SHA in the camera-ready version.

## 5. Final Smoke Test

- Download the public Hub snapshot into a fresh directory.
- Unzip `build-revise-explain_workspaces.zip`.
- Read `metadata/workspace_index.csv` and confirm 100 Build, 100 Revise, and
  100 Explain rows.
- Open one workspace from each task and confirm the paths in the metadata index
  resolve after extraction.
- Run the one-item examples in both evaluator READMEs.
