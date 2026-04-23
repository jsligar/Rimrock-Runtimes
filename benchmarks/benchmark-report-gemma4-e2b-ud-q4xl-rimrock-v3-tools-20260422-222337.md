# Gemma 4 E2B UD-Q4_K_XL — Benchmark v3 Results

Run: `2026-04-22 22:23:37`
Model: `gemma-4-e2b-it-q4_k_m.gguf`
Machine: `rimrock`
Runtime: `llama-server-turbo4-64k`
Host: `http://172.16.0.248:8424`
Thinking: `off`
Harness system prompt style: `none`
Harness system prompt: `True`
Harness tools enabled: `False`
Tools: `disabled`
Raw average: `5.42/10`
Weighted average: `5.04/10`
Output tokens: `1011`
Average tok/s: `27.87`
Failure modes: `confident_wrong:Q1, confident_wrong:Q2, format_drift:Q3, confident_wrong:Q7, confident_wrong:Q8, confident_wrong:Q9, format_drift:Q11, confident_wrong:Q12`

| ID | Score | Weight | Tok/s | Tokens | Failure Mode |
|----|-------|--------|-------|--------|--------------|
| Q1 | 1 | 1.0 | 25.83 | 64 | confident_wrong |
| Q2 | 1 | 1.0 | 44.44 | 2 | confident_wrong |
| Q3 | 7 | 1.0 | 25.8 | 115 | format_drift |
| Q4 | 10 | 1.0 | 26.24 | 51 | none |
| Q5 | 10 | 1.5 | 27.27 | 14 | none |
| Q6 | 10 | 1.0 | 26.5 | 27 | none |
| Q7 | 1 | 1.5 | 27.25 | 14 | confident_wrong |
| Q8 | 5 | 1.0 | None | 104 | confident_wrong |
| Q9 | 4 | 1.5 | 25.75 | 149 | confident_wrong |
| Q10 | 10 | 0.5 | 25.81 | 190 | none |
| Q11 | 5.0 | 1.25 | 25.56 | 239 | format_drift |
| Q12 | 1 | 1.5 | 26.17 | 42 | confident_wrong |

## Responses

### Q1 — Time Arithmetic

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `3.024s`  
Tokens: `64`  

```text
Here is the step-by-step calculation:

**1. Start Time:**
The job starts at 09:35.

**2. Task 1:**
* Start time: 09:35
* Duration: 17 minutes
* End time for Task 1
```

### Q2 — Constraint Logic

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `0.305s`  
Tokens: `2`  

```text
Cara
```

### Q3 — Code Writing

Score: `7/10`  
Failure mode: `format_drift`  
Elapsed: `4.755s`  
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
Elapsed: `2.237s`  
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
Elapsed: `0.766s`  
Tokens: `14`  

```text
{"red":3,"blue":1,"green":1}
```

### Q6 — Technical Compression

Score: `10/10`  
Failure mode: `none`  
Elapsed: `1.216s`  
Tokens: `27`  

```text
* TCP is connection-oriented, ensuring reliable data delivery.
* UDP is connectionless, offering faster but less reliable transmission.
```

### Q7 — Uncertainty Calibration

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `0.727s`  
Tokens: `14`  

```text
estimate: 2107.9
confidence: high
```

### Q8 — Fixed-Date Context Retention

Score: `5/10`  
Failure mode: `confident_wrong`  
Elapsed: `4.569s`  
Tokens: `104`  

```text
Turn2: You work in **marine biology**.
Turn3: I need a little more information to tell you the local date and time for you. I need to know **your current time zone**.

Could you tell me what time zone you are in (e.g., New Zealand Standard Time, or a specific city/time zone)?
```

### Q9 — Diagnostic Triage

Score: `4/10`  
Failure mode: `confident_wrong`  
Elapsed: `6.123s`  
Tokens: `149`  

```text
[
  {
    "rank": 1,
    "cause": "Fuel Delivery/Sensor Issue on Bank 2",
    "confidence": "high",
    "urgency": "soon"
  },
  {
    "rank": 2,
    "cause": "Ignition/Spark Issue on Cylinder Bank 2",
    "confidence": "high",
    "urgency": "soon"
  },
  {
    "rank": 3,
    "cause": "Fuel Pressure/Delivery System Issue (related to crank/lean)",
    "confidence": "medium",
    "urgency": "monitor"
  }
]
```

### Q10 — Semantic Nuance

Score: `10/10`  
Failure mode: `none`  
Elapsed: `7.577s`  
Tokens: `190`  

```text
Here are the translations:

**1. "I never said she stole my money."**

* **Je n'ai jamais dit qu'elle a volé mon argent.** (Most natural and common)
* *Alternatively, slightly more formal:* Je n'ai jamais dit qu'elle a volé mon argent.

**2. Emphasizing the word "she":**

* **Je n'ai jamais dit qu'elle a volé mon argent.** (The emphasis is naturally placed on "elle" by the structure of the sentence.)

If you wanted to force a stronger emphasis on "she" (perhaps in a more emphatic or accusatory tone), you might use:

* **Je n'ai jamais dit, c'est elle qui a volé mon argent.** (I never said, it was she who stole my money.) - *This shifts the focus heavily onto "she."*
```

### Q11 — PlatformIO ESP32-S3

Score: `5.0/10`  
Failure mode: `format_drift`  
Elapsed: `9.631s`  
Tokens: `239`  

```text
```ini
; =============================================================================
; PlatformIO Configuration for LILYGO T-Beam Supreme (ESP32-S3 with SX1262 LoRa)
; =============================================================================

[env:esp32-s3-beam-supreme]
platform = espressif32
board = esp32-s3-beam-supreme ; Adjust this if a specific board package exists, otherwise use a generic ESP32-S3 board
framework = arduino
upload_protocol = esptify
monitor_speed = 115200

; Build flags for SX1262 LoRa Radio Interface
build_flags = 
    -D SX1262_NSS=D18  ; Example pin mapping (adjust based on actual wiring)
    -D SX1262_RST=D17  ; Example pin mapping
    -D SX1262_BUSY=D16 ; Example pin mapping
    -D SX1262_DIO1=D15 ; Example pin mapping
```
```

### Q12 — SX1262 Hardware Register

Score: `1/10`  
Failure mode: `confident_wrong`  
Elapsed: `1.858s`  
Tokens: `42`  

```text
LoRa sync word configuration register address: 0x00
Public LoRa network sync word: 0x0000
Private network sync word: 0x0000
```
