import argparse
import os
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
    set_seed,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for NL->SWRL Cypher")
    parser.add_argument("--model-id", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--dataset", default="/workspace/training/training_dataset.json")
    parser.add_argument("--prompt-field", default="prompt")
    parser.add_argument("--response-field", default="cypher")
    parser.add_argument("--output-dir", default="/workspace/training/output/adapter")
    parser.add_argument("--max-seq-len", type=int, default=2048)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--use-4bit", action="store_true")
    parser.add_argument("--use-8bit", action="store_true")
    parser.add_argument("--gradient-checkpointing", action="store_true", default=True)
    parser.add_argument("--no-gradient-checkpointing", action="store_false", dest="gradient_checkpointing")
    parser.add_argument("--test-prompt", default="")
    parser.add_argument("--test-max-new-tokens", type=int, default=256)
    parser.add_argument("--hf-token", default=os.getenv("HF_TOKEN", ""))
    return parser.parse_args()


def bf16_supported() -> bool:
    if not torch.cuda.is_available():
        return False
    major, _minor = torch.cuda.get_device_capability(0)
    return major >= 8


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    use_cuda = torch.cuda.is_available()
    use_bf16 = use_cuda and bf16_supported()
    if use_bf16:
        compute_dtype = torch.bfloat16
    elif use_cuda:
        compute_dtype = torch.float16
    else:
        compute_dtype = torch.float32

    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id,
        token=args.hf_token or None,
        use_fast=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
    tokenizer.padding_side = "right"

    if (args.use_4bit or args.use_8bit) and not use_cuda:
        raise RuntimeError("4-bit/8-bit loading requires a CUDA GPU.")

    quantization_config = None
    if args.use_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
        )
    elif args.use_8bit:
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        token=args.hf_token or None,
        device_map="auto",
        torch_dtype=compute_dtype,
        quantization_config=quantization_config,
    )

    if quantization_config is not None:
        model = prepare_model_for_kbit_training(model)

    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()

    model.config.use_cache = False
    model.config.pad_token_id = tokenizer.pad_token_id

    lora_config = LoraConfig(
        r=16,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=args.dataset, split="train")
    if args.max_samples and args.max_samples > 0:
        dataset = dataset.select(range(min(args.max_samples, len(dataset))))

    prompt_field = args.prompt_field
    response_field = args.response_field
    max_len = args.max_seq_len

    def tokenize_example(example):
        prompt = example[prompt_field]
        response = example[response_field]

        if tokenizer.chat_template:
            full_text = tokenizer.apply_chat_template(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response},
                ],
                tokenize=False,
                add_generation_prompt=False,
            )
            prompt_text = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            full_ids = tokenizer(full_text, add_special_tokens=True).input_ids
            prompt_ids = tokenizer(prompt_text, add_special_tokens=True).input_ids
        else:
            prompt_text = f"### Instruction:\n{prompt}\n\n### Response:\n"
            full_text = f"{prompt_text}{response}"
            full_ids = tokenizer(
                full_text,
                add_special_tokens=True,
            ).input_ids
            prompt_ids = tokenizer(
                prompt_text,
                add_special_tokens=True,
            ).input_ids

        if max_len:
            full_ids = full_ids[:max_len]
            prompt_ids = prompt_ids[:max_len]

        prompt_len = min(len(prompt_ids), len(full_ids))
        labels = [-100] * prompt_len + full_ids[prompt_len:]
        return {"input_ids": full_ids, "labels": labels}

    dataset = dataset.map(
        tokenize_example,
        remove_columns=dataset.column_names,
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        padding=True,
        label_pad_token_id=-100,
        return_tensors="pt",
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        logging_steps=5,
        save_strategy="no",
        report_to="none",
        bf16=use_bf16,
        fp16=use_cuda and not use_bf16,
        optim="adamw_torch",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
    )

    trainer.train()

    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    if args.test_prompt:
        model.eval()
        with torch.no_grad():
            if tokenizer.chat_template:
                input_ids = tokenizer.apply_chat_template(
                    [{"role": "user", "content": args.test_prompt}],
                    tokenize=True,
                    add_generation_prompt=True,
                    return_tensors="pt",
                ).to(model.device)
            else:
                prompt_text = f"### Instruction:\n{args.test_prompt}\n\n### Response:\n"
                input_ids = tokenizer(
                    prompt_text,
                    return_tensors="pt",
                    add_special_tokens=True,
                ).input_ids.to(model.device)

            generated = model.generate(
                input_ids=input_ids,
                max_new_tokens=args.test_max_new_tokens,
                do_sample=False,
            )
            output_text = tokenizer.decode(generated[0], skip_special_tokens=True)
            print("\n=== Test Output ===\n")
            print(output_text)


if __name__ == "__main__":
    main()
