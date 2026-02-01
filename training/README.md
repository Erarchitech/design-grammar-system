# LoRA Training (Docker + GPU)

This folder contains a minimal LoRA fine-tuning setup for translating natural language rules to SWRL-based Cypher.

## Dataset
- Schema reference: `training/dataset_schema.json`
- Current training set: `training/training_dataset.json`
  - Format: JSON Lines (one JSON object per line)
  - Required fields: `prompt`, `cypher`

## Quick start (PowerShell)
1) Set your Hugging Face token (required for gated LLaMA weights):
```
$env:HF_TOKEN = "<your_hf_token>"
```

2) Build the training image:
```
docker compose -f training/docker-compose.train.yml build
```

3) Run training:
```
docker compose -f training/docker-compose.train.yml run --rm trainer
```

The adapter will be written to:
```
training/output/adapter
```

## Next steps (after training)
Run the commands below from the repo root (`c:\Users\Admin\source\repos\design-grammar-system`) in PowerShell unless noted.

### 1) Ensure the core Docker services are running (host)
```
docker compose up -d
docker compose ps
```
You should see `ollama` running. The container is exposed on `http://localhost:11435`.

### 2) Make sure the base Ollama model exists (host -> container)
The base model must match what you trained against.
```
docker exec -it ollama ollama pull llama3.1
```
If you use a different base model, pull that name instead.

### 3) Create a new Ollama model from the adapter (host)
This uploads the adapter to the Ollama container using the REST API.
```
$env:HF_TOKEN = "<your_hf_token>"
.\training\scripts\create_ollama_model.ps1 `
  -AdapterDir .\training\output\adapter `
  -BaseModel llama3.1 `
  -ModelName llama3.1-dg
```
Notes:
- `-BaseModel` should match the model you pulled in step 2 (and what your app expects).
- `-ModelName` is the new model name you will use in n8n/webhook payloads.

### 4) Verify the model exists (host -> container)
```
docker exec -it ollama ollama list
```

### 5) Point your workflow/app at the new model (host)
Option A: Update the default in `docker-compose.yml` (repo root):
- set `OLLAMA_MODEL` to your new model name (e.g., `llama3.1-dg`)
- then restart n8n:
```
docker compose up -d n8n
```
Option B: Override per request using `ollama_model` in the webhook payload.

### 6) Quick smoke test (host)
```
$body = @{
  model = "llama3.1-dg"
  prompt = "Each elevator must serve at least 2 floors (violation if served floor count < 2)."
  stream = $false
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:11435/api/generate" -ContentType "application/json" -Body $body
```

## Common adjustments
- Use a different model id:
```
docker compose -f training/docker-compose.train.yml run --rm trainer python /workspace/training/train_lora.py --dataset /workspace/training/training_dataset.json --output-dir /workspace/training/output/adapter --model-id meta-llama/Llama-3.1-8B
```

- Low VRAM (quantized base + LoRA):
```
docker compose -f training/docker-compose.train.yml run --rm trainer python /workspace/training/train_lora.py --dataset /workspace/training/training_dataset.json --output-dir /workspace/training/output/adapter --model-id meta-llama/Llama-3.1-8B-Instruct --use-4bit
```

- Limit samples for a fast smoke test:
```
docker compose -f training/docker-compose.train.yml run --rm trainer python /workspace/training/train_lora.py --dataset /workspace/training/training_dataset.json --output-dir /workspace/training/output/adapter --model-id meta-llama/Llama-3.1-8B-Instruct --max-samples 8 --epochs 1
```

- Quick test prompt (runs after training):
```
docker compose -f training/docker-compose.train.yml run --rm trainer python /workspace/training/train_lora.py --dataset /workspace/training/training_dataset.json --output-dir /workspace/training/output/adapter --model-id meta-llama/Llama-3.1-8B-Instruct --test-prompt "Each elevator must serve at least 2 floors (violation if served floor count < 2)."
```

## Notes
- The base model used for training should match the base you intend to use in Ollama.
- If you see CUDA out-of-memory, reduce `--max-seq-len`, increase `--grad-accum`, or enable `--use-4bit`.
- The training script masks the prompt tokens so loss is computed only on the Cypher output.
- RTX 50‑series GPUs (sm_120) require a newer PyTorch CUDA build; rebuild the image after changes:
```
docker compose -f training/docker-compose.train.yml build --no-cache
```
