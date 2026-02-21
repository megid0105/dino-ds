# Prompt Files Operators Can Edit

This package exposes two prompt layers:

1. System prompt (training/inference system message)
- File: `prompts/system/dino_system_prompt.txt`
- Lane YAML field: `system_prompt_path`

2. Teacher prompt (used only when teacher runtime is active)
- Lane-specific files: `prompts/teacher/lane_XX_teacher_system_prompt.txt`
- Lane YAML field: `teacher_runtime.system_prompt_path`
- Optional shared teacher files may also exist under `prompts/teacher/`.

Quick checks:

```bash
./dino-ds help prompts
./dino-ds help spec lane_03
```

After editing prompt files, re-run lane generation:

```bash
./dino-ds lane_03_en --limit 20
# or
./dino-ds lane_03_en --teacher --limit 20
```
