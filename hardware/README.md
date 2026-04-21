# Hardware & System Configuration

## Device

**Jetson Orin Nano Super 8GB** ("Rimrock")  
Engineering Reference Developer Kit Super  
`jsligar@172.16.0.248`

## Specs

| Component | Detail |
|---|---|
| SoC | Tegra234 (SM87, Ampere) |
| GPU | 1024-core Ampere, 32 Tensor Core |
| Active GPU TPCs | 4 |
| RAM | 8GB LPDDR5 unified (CPU+GPU shared) |
| Usable CUDA RAM | 7.43GB |
| Theoretical bandwidth | 102 GB/s |
| Storage | 915GB NVMe (`/dev/nvme0n1p1`) |
| CPU | 6× Cortex-A78AE @ up to 1728 MHz |
| OS | Ubuntu 22.04 (L4T) |
| JetPack | 6.2.2 |
| CUDA | 12.6 |
| cuDNN | 9.3 |
| TensorRT | 10.3 |

## Memory Layout

Unified memory means CPU and GPU share the same physical RAM pool. This has important inference implications:

- CPU-mapped model tensors don't require explicit GPU transfer — they're directly accessible on the CUDA side
- KV cache and compute buffers consume from the same 7.43GB pool as the OS and all processes
- Docker container CUDA contexts consume memory visible to the host (`nvidia-smi` / `tegrastats`)
- vLLM V1 engine subprocess forks after parent CUDA context allocation, leaving child with ~3.45GB visible

## Storage

```
/dev/nvme0n1p1   915GB total   508GB used   360GB free   (as of 2026-04-21)
```

Models directory: `/opt/models/` (~100GB used)

## ZRAM / Swap

- 8GB swapfile active at `/swapfile`
- ZRAM baseline: 4:1 ratio, ~7% utilization under normal load
- Swap used during heavy inference: ~290MB (normal, not a concern)

## Thermal

- Thermal ceiling under sustained benchmark load: low 60s°C
- No throttling observed during any tested workload
- Fan: dynamic speed control via `nvfancontrol`
- Performance limits are runtime/model behavior, not thermals

## Running Services

| Service | Port | Notes |
|---|---:|---|
| `llama-server` (systemd) | 8424 | Primary inference endpoint |
| `memory-mcp` (Docker) | 8001 | CPU only, no GPU impact |
| `ollama` | 11434 | Inactive — stopped to free RAM |

OpenWebUI was migrated to WORKHORSE (separate Linux server) to recover ~1GB RAM on Rimrock.

## Network

| Host | IP |
|---|---|
| Rimrock | 172.16.0.248 |
| WORKHORSE (Linux server) | 172.16.0.x |
| Claude NAS | 172.16.0.1 |
| MyCloud NAS | 172.16.0.107 |

Claude NAS mounted at `/mnt/claude-nas/` — benchmark results and session notes live here.

## Bandwidth Observations

llama-server baseline at ~26.3 tok/s on Gemma 4 E2B Q4_K_M represents ~32% of the 102 GB/s theoretical bandwidth ceiling. Runtime overhead (kernel launch, scheduling, KV cache management) accounts for the gap, not memory bandwidth saturation.
