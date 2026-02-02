# AGENTS — DinoDS Handoff Pack

This file is the **single source of truth** for new threads. It links to the locked specs, schemas, and all core tool operations.

---

## Locked Specs (Do Not Drift)
- `PCT-perf_DINO_GLOBAL_SCHEMA_LABEL_STANDARD_MASTER_SPEC_01_13_2026.md`
- `Synthetic_Dataset_Lock_Spec_01_13_2026.md`
- `Full_Dataset_Spec.md`
- QC refs:
  - `DTA-Tool-B2-ModeShaping-QC_Report.md`
  - `DTA-Tool-B3-ExportProfiles-QC_Report.md`
  - `DTA-Tool-B4-LanguagePolicy-QC_Report.md`

---

## Schema Links
- Lane schema: `src/dino_ds/schemas/lane_schema.v1.json`
- System prompt registry: `system_prompt_registry.json` and `src/dino_ds/system_prompt_registry.json`

---

## Tool Entrypoints (Code Links)
- CLI: `src/dino_ds/cli.py`
- Build: `src/dino_ds/commands/build_cmd.py`
- Validate: `src/dino_ds/commands/validate_cmd.py`
- Lint: `src/dino_ds/commands/lint_cmd.py`
- Split: `src/dino_ds/commands/split_cmd.py`
- Pack + Export: `src/dino_ds/commands/pack_cmd.py`

---

## File ↔ Function Links (Operational)
- Lane configs: `lanes/**/lane.yaml` → `validate_cmd.py` (schema), `build_cmd.py` (generation), `split_cmd.py` (splits), `pack_cmd.py` (export).
- System prompt registry: `system_prompt_registry.json` → `cli.py` (gate/export injection), `pack_cmd.py` (offline registry lookup).
- System prompt text: `prompts/system/dino_system_prompt.txt` → referenced by the registry and loaded by the runtime.
- Teacher prompts: `prompts/teacher/lane_XX_teacher_system_prompt.txt` → `build_cmd.py` (teacher_runtime rewrite).

---

## Commands (Operational)
- Smoke gate run:
  ```bash
  ./scripts/run.sh gate lane --config lanes/<lane_id>/lane.yaml --limit 20
  ```
- Offline wrapper:
  ```bash
  ./dino-ds lane_02 run --limit 1000
  ```

---

## Tool Flow (Generate → Validate → Export)
1. **Validate schema**  
   `validate_cmd.py` loads `lane_schema.v1.json` and rejects invalid lane files.
2. **Build rows**  
   `build_cmd.py` runs either `template_expand` or `shuffle_cap` depending on `source_type`.
3. **Teacher rewrite (optional)**  
   `build_cmd.py` uses `teacher_runtime` to rewrite assistant responses.
4. **Post‑rewrite validation (2nd layer)**  
   If `validators` includes `mode_richness`, rewritten rows are checked; failures revert to original drafts.
5. **Split**  
   `split_cmd.py` creates train/val/test splits.
6. **Export**  
   `pack_cmd.py` writes TEF (`train.jsonl`, `val.jsonl`, `test.jsonl`).
7. **Pack**  
   `pack_cmd.py` creates `lane_gate_zip_*.zip` with checksum.

---

## Slot + Slot Bank Workflow (Template Expand)
- `template_expand.slot_banks` must include every placeholder used in `row_template`.
- Use `expand_dict_slots: ["case"]` for coupled fields (avoids semantic mismatch).
- `row_template` is rendered once from the sampled context.
- Avoid nested placeholders unless multi‑pass formatting is explicitly supported.

---

## Teacher Runtime Rules (High‑Level)
- Shared system prompt: `prompts/system/dino_system_prompt.txt` via `system_prompt_path`.
- Per‑lane teacher prompt: `prompts/teacher/lane_XX_teacher_system_prompt.txt`.
- Timeout behavior: if rewrite hangs, tool exports mixed rows (rewritten + original).

---

## Wrap + Zip (Offline Package)
- Full step‑by‑step instructions live in `WRAPPED_PACKAGE.md`.
- Expected output: `dist/dino_ds_offline_mac.zip`.
