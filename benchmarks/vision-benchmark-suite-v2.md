# Vision Benchmark Suite v2

Purpose: a harder synthetic vision suite that still has deterministic ground truth.

Last updated: 2026-04-03

Script: [vision_benchmark_v2.py](/C:/Users/justi/Scripts/vision_benchmark_v2.py)

## Why This Rewrite Is Better

- Selective counting instead of plain counting
- Exact OCR tokens instead of simple signage only
- Table lookup and labeled color matching
- Spatial reasoning with distractors
- More tests that combine seeing with choosing the right attribute

## How To Run

```powershell
python C:\Users\justi\Scripts\vision_benchmark_v2.py --model gemma4:e2b
python C:\Users\justi\Scripts\vision_benchmark_v2.py --model gemma4:e4b --host http://172.16.0.156:11434
```

Optional:

```powershell
python C:\Users\justi\Scripts\vision_benchmark_v2.py --model gemma4:e2b --save-dir C:\Users\justi\Desktop\vision-benchmark-images
```

## Tests

| ID | Category | What it measures | Expected |
|----|----------|------------------|----------|
| V1 | Selective Count | Count red circles only, ignore red squares and blue circles | `6` |
| V2 | Ordered Colors | Read color sequence left to right | `blue yellow red green` |
| V3 | Exact OCR | Read a short alphanumeric token | `B7LQ-105` |
| V4 | Table Lookup | Find row/column intersection in a rendered grid | `17` |
| V5 | Spatial Relation | Identify the shape directly above a target object | `circle` |
| V6 | Count By Attribute | Count hollow triangles only | `3` |
| V7 | Chart Reading | Pick the tallest labeled bar | `B` |
| V8 | Math From Image | Solve rendered arithmetic expression | `35` |
| V9 | Label Match | Match box label to color | `B` |
| V10 | Short OCR Phrase | Read a time string with punctuation | `6:45 PM` |

## Scoring

- `5`: exact answer
- `3`: answer contains the right token but adds noise or misses formatting
- `1`: wrong answer

## What To Record

- `tok/s`
- `elapsed`
- per-test score
- notes on failure type:
  - OCR confusion
  - counting drift
  - wrong attribute selection
  - label lookup failure
  - extra-text formatting noise

## Suggested Summary Table

| Model | Machine | V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 | V9 | V10 | Avg | Notes |
|-------|---------|----|----|----|----|----|----|----|----|----|-----|-----|-------|
|       |         |    |    |    |    |    |    |    |    |    |     |     |       |
