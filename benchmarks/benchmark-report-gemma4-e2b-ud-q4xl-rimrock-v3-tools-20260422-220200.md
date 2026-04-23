# Gemma 4 E2B UD-Q4_K_XL — Benchmark v3 Results

Run: `2026-04-22 22:02:00`
Model: `gemma-4-e2b-it-q4_k_m.gguf`
Machine: `rimrock`
Runtime: `llama-server-q8`
Host: `http://172.16.0.248:8424`
Thinking: `off`
Harness system prompt style: `none`
Harness system prompt: `True`
Harness tools enabled: `False`
Tools: `disabled`
Raw average: `5.54/10`
Weighted average: `5.23/10`
Output tokens: `1049`
Average tok/s: `29.42`
Failure modes: `confident_wrong:Q1, confident_wrong:Q2, format_drift:Q3, confident_wrong:Q7, confident_wrong:Q8, confident_wrong:Q11, confident_wrong:Q12`

| ID | Score | Weight | Tok/s | Tokens | Failure Mode |
|----|-------|--------|-------|--------|--------------|
| Q1 | 1 | 1.0 | 26.81 | 64 | confident_wrong |
| Q2 | 1 | 1.0 | 49.0 | 2 | confident_wrong |
| Q3 | 7 | 1.0 | 27.07 | 115 | format_drift |
| Q4 | 10 | 1.0 | 27.46 | 51 | none |
| Q5 | 10 | 1.5 | 28.31 | 14 | none |
| Q6 | 10 | 1.0 | 27.73 | 27 | none |
| Q7 | 1 | 1.5 | 28.47 | 14 | confident_wrong |
| Q8 | 5 | 1.0 | None | 177 | confident_wrong |
| Q9 | 7 | 1.5 | 26.94 | 193 | none |
| Q10 | 10 | 0.5 | 26.92 | 256 | none |
| Q11 | 3.5 | 1.25 | 27.05 | 115 | confident_wrong |
| Q12 | 1 | 1.5 | 27.83 | 21 | confident_wrong |

## Responses

### Q1 — Time Arithmetic

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `3.002s`  
Tokens: `64`  

```text
Here is the step-by-step calculation:

1. **Start Time:** 09:35

2. **Task 1:**
   * Starts at 09:35.
   * Duration: 17 minutes.
   * End time of Task 1:
```

### Q2 — Constraint Logic

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `0.265s`  
Tokens: `2`  

```text
Cara
```

### Q3 — Code Writing

Score: `7/10`  
Failure mode: `format_drift`  
Elapsed: `4.489s`  
Tokens: `115`  

```text
```python
def group_even_runs(nums: list[int]) -> list[list[int]]:
    result = []
    current_run = []
    for num in nums:
        if num % 2 == 0:
            current_run.append(num)
        else:
            if current_run:
                result.append(current_run)
            current_run = []
    if current_run:
        result.append(current_run)
    return result
```
```

### Q4 — Code Debugging

Score: `10/10`  
Failure mode: `none`  
Elapsed: `2.104s`  
Tokens: `51`  

```text
def word_counts(items):
    counts = {}
    for item in items:
        key = item.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts
```

### Q5 — Format Fidelity

Score: `10/10`  
Failure mode: `none`  
Elapsed: `0.73s`  
Tokens: `14`  

```text
{"red":3,"blue":1,"green":1}
```

### Q6 — Technical Compression

Score: `10/10`  
Failure mode: `none`  
Elapsed: `1.153s`  
Tokens: `27`  

```text
* TCP is connection-oriented, ensuring reliable data delivery.
* UDP is connectionless, offering faster but less reliable transmission.
```

### Q7 — Uncertainty Calibration

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `0.703s`  
Tokens: `14`  

```text
estimate: 301.02
confidence: high
```

### Q8 — Fixed-Date Context Retention

Score: `5/10`  
Failure mode: `confident_wrong`  
Elapsed: `7.069s`  
Tokens: `177`  

```text
Turn2: You work in **marine biology**.
Turn3: I need to know your current time zone to tell you what the local date and time is for you.

Since you mentioned you live in **Auckland**, I will assume you are in the **New Zealand time zone (NZST/NZDT)**.

**Please confirm if you are in the Auckland time zone.**

If you are in the Auckland time zone, then 2026-07-01 15:00 UTC is:

**2026-07-01 22:00 NZST** (New Zealand Standard Time)
```

### Q9 — Diagnostic Triage

Score: `7/10`  
Failure mode: `none`  
Elapsed: `7.448s`  
Tokens: `193`  

```text
[
  {
    "rank": 1,
    "cause": "Fuel injector issue on Bank 2 (e.g., clogged injector, faulty injector, or related wiring/sensor issue)",
    "confidence": "high",
    "urgency": "soon"
  },
  {
    "rank": 2,
    "cause": "Ignition system issue affecting Bank 2 (e.g., faulty coil pack, ignition module, or wiring harness issue)",
    "confidence": "high",
    "urgency": "soon"
  },
  {
    "rank": 3,
    "cause": "Fuel delivery/pressure issue affecting Bank 2 (e.g., weak fuel pump, clogged fuel filter, or faulty fuel pressure regulator)",
    "confidence": "medium",
    "urgency": "monitor"
  }
]
```

### Q10 — Semantic Nuance

Score: `10/10`  
Failure mode: `none`  
Elapsed: `9.74s`  
Tokens: `256`  

```text
Here are the translations:

**1. Standard Translation:**

> "I never said she stole my money."
> **"Je n'ai jamais dit qu'elle a volé mon argent."** (or "qu'elle a dérobé mon argent")

**2. Translation Emphasizing "She":**

To emphasize "she" in French, you often use specific grammatical structures, such as cleft sentences or by placing the pronoun in a position that draws attention to the action performed by her.

> **"Je n'ai jamais dit que c'est elle qui a volé mon argent."** (I never said that it was she who stole my money.)
> *or, more directly emphasizing the subject:*
> **"Je n'ai jamais dit qu'elle a volé mon argent."** (While grammatically the same, the emphasis shifts in context, often implying the focus is on *her* action.)

**The most natural way to emphasize "she" in this context is often by using the structure above, or by focusing the sentence on her guilt:**

> **"Je n'ai jamais dit qu'elle a volé mon argent."** (This remains the most direct translation,
```

### Q11 — PlatformIO ESP32-S3

Score: `3.5/10`  
Failure mode: `confident_wrong`  
Elapsed: `4.501s`  
Tokens: `115`  

```text
[env:esp32-s3-tbeam-supreme]
platform = espressif32
board = tbeam-supreme
framework = arduino
upload_protocol = esptify
monitor_speed = 115200

build_flags =
    -D SX1262_NSS=1
    -D SX1262_RST=1
    -D SX1262_BUSY=1
    -D SX1262_DIO1=1
```

### Q12 — SX1262 Hardware Register

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `0.965s`  
Tokens: `21`  

```text
0x00
Public: 0x00
Private: 0x01
```
