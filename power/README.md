# Power & Performance Configuration

## Active Profile: RIMROCK_TOKENS

Custom nvpmodel profile (ID=3), set as default in `/etc/nvpmodel.conf`.

### Clock State (locked)

| Component | Frequency |
|---|---:|
| CPU (all 6 cores) | 1728 MHz (min=max, locked) |
| GPU | 1020 MHz (min=max, locked) |
| EMC | 3199 MHz (max, locked via bpmp) |
| CPU Governor | performance |

### nvpmodel Profile Definition

```
< POWER_MODEL ID=3 NAME=RIMROCK_TOKENS >
CPU_ONLINE CORE_0 1
CPU_ONLINE CORE_1 1
CPU_ONLINE CORE_2 1
CPU_ONLINE CORE_3 1
CPU_ONLINE CORE_4 1
CPU_ONLINE CORE_5 1
FBP_POWER_GATING FBP_PG_MASK 2
TPC_POWER_GATING TPC_PG_MASK 240
GPU_POWER_CONTROL_ENABLE GPU_PWR_CNTL_EN on
CPU_A78_0 MIN_FREQ 1728000
CPU_A78_0 MAX_FREQ 1728000
CPU_A78_1 MIN_FREQ 1728000
CPU_A78_1 MAX_FREQ 1728000
CPU_A78_2 MIN_FREQ 1728000
CPU_A78_2 MAX_FREQ 1728000
CPU_A78_3 MIN_FREQ 1728000
CPU_A78_3 MAX_FREQ 1728000
CPU_A78_4 MIN_FREQ 1728000
CPU_A78_4 MAX_FREQ 1728000
CPU_A78_5 MIN_FREQ 1728000
CPU_A78_5 MAX_FREQ 1728000
GPU MIN_FREQ 1020000000
GPU MAX_FREQ 1020000000
GPU_POWER_CONTROL_DISABLE GPU_PWR_CNTL_DIS auto
EMC MAX_FREQ -1

< PM_CONFIG DEFAULT=3 >
```

Config file: `/etc/nvpmodel.conf`

### EMC Lock (applied after boot)

nvpmodel sets `EMC MAX_FREQ -1` (uncapped) but the EMC lock to 3199 MHz must be applied manually via bpmp after boot:

```bash
sudo nvpmodel -m 3
sudo jetson_clocks
echo 1 | sudo tee /sys/kernel/debug/bpmp/debug/clk/emc/state
echo 1 | sudo tee /sys/kernel/debug/bpmp/debug/clk/emc/mrq_rate_locked
echo 1 | sudo tee /sys/kernel/debug/bpmp/debug/bwmgr/bwmgr_halt
echo 3199000000 | sudo tee /sys/kernel/debug/bpmp/debug/clk/emc/rate
```

### Verify Current State

```bash
sudo nvpmodel -q                          # should show RIMROCK_TOKENS
sudo jetson_clocks --show                 # CPU/GPU/EMC frequencies
cat /sys/kernel/debug/bpmp/debug/clk/emc/rate   # should show 3199000000
```

## Thermal Observations

- Peak during benchmarks: low 60s°C
- No throttling observed at sustained full load
- Fan: dynamic speed control active (`nvfancontrol`)
- Performance limits are runtime/model behavior, not thermals

## Systemd Service

The llama-server runs as a systemd service:

```
/etc/systemd/system/llama-server.service
```

Current ExecStart (as of 2026-04-21 — **note: this is outdated vs start_llama.sh**):

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /opt/models/gemma4-e2b-ud-q4xl-fresh/gemma-4-E2B-it-UD-Q4_K_XL.gguf \
  --mmproj /opt/models/gemma4-e2b-ud-q4xl-fresh/mmproj-F16.gguf \
  --host 0.0.0.0 --port 8424 \
  -ngl 99 -c 4096 -t 6 -tb 6 \
  --threads-http 1 -np 1 --no-cont-batching \
  -b 512 -ub 512 --flash-attn on \
  --prio 2 --prio-batch 2 \
  --reasoning off --reasoning-budget 0 --reasoning-format none
Restart=on-failure
RestartSec=5
```

The service file uses the older UD-Q4_K_XL model at ctx=4096. The current recommended config is in [`../runtimes/llama-cpp/start_llama.sh`](../runtimes/llama-cpp/start_llama.sh) (sowilow Q4_K_M, ctx=32768, mmproj).

To update the service to the current config:

```bash
sudo systemctl edit --force llama-server
# or edit /etc/systemd/system/llama-server.service directly
sudo systemctl daemon-reload && sudo systemctl restart llama-server
```
