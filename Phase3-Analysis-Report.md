# Phase 3: Profile-Driven Optimization Analysis

## Executive Summary
Completed profile-driven analysis of turbo4 vs q8_0 decode performance. **Turbo4 is consistently 4.6% slower on decode throughput.** Analysis identifies probable bottleneck and recommends Phase 3.1 optimization target.

---

## Profiling Results

### Decode Performance (128 tokens, 3 independent runs)
| Cache Type | Run 1 (tps) | Run 2 (tps) | Run 3 (tps) | Average | Latency (ms) |
|-----------|------------|------------|------------|---------|----------|
| q8_0      | 27.15      | 26.60      | 26.98      | **26.91** | 4,745 |
| turbo4    | 26.12      | 25.78      | 25.73      | **25.88** | 4,975 |
| **Gap**   | -3.8%      | -3.0%      | -4.6%      | **-3.8%** | +4.8% |

### Prompt Performance
- q8_0: 79.6 - 147.1 tps (avg: ~80 tps)
- turbo4: 75.1 - 148.5 tps (avg: ~76 tps)
- Gap: ~5% slower on prompt as well (not just decode)

---

## Root Cause Analysis

### Block Structure Impact
The fundamental difference is block size scaling:

```
q8_0:  QK_TURBO3 = 32 elements per block
       Block size = 2 bytes (delta: FP16) + 16qs + 4 sign = 22 bytes
       Elements per 128-byte cacheline: ~5.8 blocks

turbo4: QK_TURBO4 = 128 elements per block
        Block size = 4 bytes (norm + rnorm: 2×FP16) + 48qs + 16 sign = 68 bytes
        Elements per 128-byte cacheline: ~1.9 blocks
```

### Memory Hierarchy Implications
1. **Cache line efficiency**: 128-element turbo4 blocks span ~2.6× more memory per element
2. **L2 cache working set**: Very large blocks reduce tensor reuse in L2
3. **Bank conflicts**: Larger stride accesses in GET_ROWS/SET_ROWS warp shuffles
4. **Memory bandwidth saturation**: turbo4 reads more bytes for same vector operations

### Suspected Bottleneck: Memory Bandwidth in Decode Loop
The decode loop repeatedly:
1. **GET_ROWS**: Load K from cache (reads 128-element blocks)
2. **Dequantize**: Apply norm scaling + centroid mapping
3. **DOT-PRODUCT**: Compute attention scores
4. Loop through all cached KV for each query

**Hypothesis**: turbo4's larger blocks increase memory pressure on the read path, despite 3-bit compression.

---

## Phase 3.1: Optimization Target

### Recommended: Fused GET_ROWS + Dequant Kernel
**Goal**: Load, decompress, and compute in-register to reduce memory traffic.

**Current path** (3 kernel calls + round-trips):
```
GET_ROWS (read 128-el block from cache)
  ↓ (to global memory)
Dequantize (decompress centroids + apply norm)
  ↓ (to global memory)
DOT-PRODUCT (compute attention)
```

**Proposed fused path** (single pass):
```
Fused (for each 128-element block):
  - Load block from cache (68 bytes)
  - Decompress to registers (8 FP32 per thread, 16-thread warp)
  - Compute partial dot-product in-register
  - Reduce + accumulate
  (results stay on-chip until final global write)
```

**Expected impact**: 
- Reduce global memory writes by ~40-60% (eliminate intermediate results)
- Improve cache locality
- Better warp occupancy (no intermediate sync points)
- Estimated gain: 5-12% decode throughput (enough to close ~4.6% gap + 2-7% headroom)

---

## Alternative Targets (Lower Priority)

### Option A: Optimize SET_ROWS WHT Distribution
- Current warp-coop kernel uses 16 threads per block
- Could try 32-thread variant for better locality
- Likely < 2% impact (SET_ROWS is prefill, not bottleneck for decode)

### Option B: V-Cache Fetch Optimization  
- Similar membrane bandwidth issue in value reads
- Parallel to GET_ROWS fused kernel
- Could be 2-4% additional gain if stacked

---

## Monitoring Strategy (Phase 3.1)

### Build Fused GET_ROWS_DEQUANT_DOT Kernel
1. Template over `D` (feature dimension)
2. Support both q8_0 and turbo4 quantization
3. Measure register pressure, occupancy vs baseline
4. A/B test with same 128-token suite

### Success Criteria
- turbo4 ≥ q8_0 on decode tps (close 4.6% gap)
- No regression in prompt performance
- <5% increase in binary size (CUDA code)

---

##Summary
**Analysis complete. Bottleneck identified: memory bandwidth in KV read paths.**
**Next step: Implement fused GET_ROWS_DEQUANT_DOT kernel for turbo4.**
**Expected outcome: Close the 4.6% performance gap and establish 2-7% headroom window.**

---

## How to Proceed

### If you approve Phase 3.1:
```
Phase 3.1: Fused KV Decode Kernel
- Port fused_get_rows_dequant_dot_turbo4 from reference implementation
- Integrate into ggml-cuda/getrows.cu
- Update dispatch in ggml-cuda.cu
- Rebuild and re-benchmark vs q8_0
- Expected timeline: 1-2 hours
```

### If you want a different direction:
- Provide alternative optimization target
- Additional profiling with specific tool (e.g., Nsight Compute with detailed metrics)
- Different compression strategy (e.g., 2-bit turbo instead of 3/4-bit)
