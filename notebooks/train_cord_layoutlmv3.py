#!/usr/bin/env python3
"""
LayoutLMv3 token classification on CORD-v1 — mirrors notebooks/CORD.ipynb (clean, no Colab magics).

Usage:
  pip install -r requirements-train.txt
  python train_cord_layoutlmv3.py --output_dir ./cord-layoutlmv3-final
  python train_cord_layoutlmv3.py --export_onnx --model_dir ./cord-layoutlmv3-final --onnx_dir ./cord-layoutlmv3-onnx

ONNX export uses `optimum-cli` (same as the notebook). Point backend HF_MODEL_ID to the ONNX folder or Hub repo.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Some weights of LayoutLMv3ForTokenClassification")

import numpy as np
import torch
from datasets import load_dataset
from seqeval.metrics import f1_score, precision_score, recall_score
from transformers import (
    LayoutLMv3ForTokenClassification,
    LayoutLMv3Processor,
    Trainer,
    TrainingArguments,
)


def safe_split(text):
    return text.strip().split() if isinstance(text, str) and text.strip() else []


def extract_data(example, label2id):
    image = example["image"]
    try:
        gt = json.loads(example["ground_truth"])
        parse = gt.get("gt_parse", {})
    except Exception:
        parse = {}

    words, ner_tags, bboxes = [], [], []

    for item in parse.get("menu", []):
        if isinstance(item, dict):
            for key, tag in [("nm", "MENU"), ("price", "PRICE")]:
                val = item.get(key)
                if isinstance(val, str) and val.strip():
                    for i, w in enumerate(safe_split(val)):
                        words.append(w)
                        ner_tags.append(label2id[f"B-{tag}"] if i == 0 else label2id[f"I-{tag}"])
                        bboxes.append([0, 0, 999, 999])

    for key, tag in [("vendor", "VENDOR"), ("date", "DATE"), ("total", "TOTAL")]:
        val = parse.get(key)
        if isinstance(val, str) and val.strip():
            for i, w in enumerate(safe_split(val)):
                words.append(w)
                ner_tags.append(label2id[f"B-{tag}"] if i == 0 else label2id[f"I-{tag}"])
                bboxes.append([0, 0, 999, 999])

    if not words:
        words = ["receipt"]
        ner_tags = [label2id["O"]]
        bboxes = [[0, 0, 999, 999]]

    return {"words": words, "ner_tags": ner_tags, "bboxes": bboxes, "image": image}


def build_preprocess(processor, label2id):
    def preprocess(example):
        data = extract_data(example, label2id)
        encoding = processor(
            data["image"],
            data["words"],
            boxes=data["bboxes"],
            word_labels=data["ner_tags"],
            truncation=True,
            padding="max_length",
            max_length=512,
            return_tensors="pt",
        )
        return {k: v.squeeze(0) for k, v in encoding.items()}

    return preprocess


class LayoutLMv3Collator:
    def __call__(self, features):
        batch = {}
        for k in features[0].keys():
            batch[k] = torch.stack([f[k] for f in features])
        return batch


def run_training(args: argparse.Namespace) -> None:
    labels = [
        "O",
        "B-TOTAL",
        "I-TOTAL",
        "B-DATE",
        "I-DATE",
        "B-VENDOR",
        "I-VENDOR",
        "B-RECEIPT_ID",
        "I-RECEIPT_ID",
        "B-MENU",
        "I-MENU",
        "B-PRICE",
        "I-PRICE",
    ]
    label2id = {label: idx for idx, label in enumerate(labels)}
    id2label = {idx: label for label, idx in label2id.items()}

    dataset = load_dataset("naver-clova-ix/cord-v1", split=f"train[:{args.subset}]")
    processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base", apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(
        "microsoft/layoutlmv3-base",
        num_labels=len(labels),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
    )

    tokenized_dataset = dataset.map(
        build_preprocess(processor, label2id),
        remove_columns=dataset.column_names,
        desc="Processing LayoutLMv3 data",
    )
    tokenized_dataset.set_format(
        type="torch",
        columns=["input_ids", "attention_mask", "bbox", "labels", "pixel_values"],
    )

    split = tokenized_dataset.train_test_split(test_size=args.test_size, seed=args.seed)
    train_dataset, eval_dataset = split["train"], split["test"]

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=2)
        true_preds = [
            [id2label[p] for p, l in zip(pred, lab) if l != -100] for pred, lab in zip(preds, labels)
        ]
        true_labs = [[id2label[l] for l in lab if l != -100] for lab in labels]
        return {
            "precision": precision_score(true_labs, true_preds, zero_division=0),
            "recall": recall_score(true_labs, true_preds, zero_division=0),
            "f1": f1_score(true_labs, true_preds, zero_division=0),
        }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        fp16=args.fp16 and torch.cuda.is_available(),
        weight_decay=0.01,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        report_to="none",
        logging_steps=10,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=LayoutLMv3Collator(),
        compute_metrics=compute_metrics,
    )

    print("Starting training…", flush=True)
    trainer.train()
    metrics = trainer.evaluate()
    print("Evaluation:", metrics)

    trainer.save_model(str(out_dir))
    processor.save_pretrained(str(out_dir))
    print(f"Saved model and processor to {out_dir.resolve()}")


def run_onnx_export(model_dir: Path, onnx_dir: Path, opset: int) -> None:
    """Same as notebook: `optimum-cli export onnx ...` (requires `optimum` on PATH)."""
    import shutil

    onnx_dir.mkdir(parents=True, exist_ok=True)
    cli = shutil.which("optimum-cli")
    if not cli:
        raise RuntimeError(
            "optimum-cli not found. Activate your venv and ensure `optimum` is installed, "
            "then run manually:\n"
            f"  optimum-cli export onnx --model {model_dir} --task token-classification "
            f"--opset {opset} --device cpu {onnx_dir}"
        )
    cmd = [
        cli,
        "export",
        "onnx",
        "--model",
        str(model_dir),
        "--task",
        "token-classification",
        "--opset",
        str(opset),
        "--device",
        "cpu",
        str(onnx_dir),
    ]
    subprocess.run(cmd, check=True)

    processor = LayoutLMv3Processor.from_pretrained(str(model_dir), apply_ocr=False)
    processor.save_pretrained(str(onnx_dir))
    print(f"ONNX + processor saved under {onnx_dir.resolve()}")


def main() -> None:
    p = argparse.ArgumentParser(description="Train LayoutLMv3 on CORD-v1 (subset) and optionally export ONNX.")
    p.add_argument("--output_dir", type=str, default="./cord-layoutlmv3-final")
    p.add_argument("--subset", type=int, default=200, help="Number of CORD train examples to use.")
    p.add_argument("--test_size", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch_size", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--fp16", action="store_true", help="Use fp16 on CUDA only.")
    p.add_argument("--export_onnx", action="store_true")
    p.add_argument("--model_dir", type=str, default=None, help="For export-only: trained checkpoint dir.")
    p.add_argument("--onnx_dir", type=str, default="./cord-layoutlmv3-onnx")
    p.add_argument("--opset", type=int, default=14)
    p.add_argument(
        "--export_only",
        action="store_true",
        help="Only run ONNX export from an existing --model_dir (no training).",
    )
    args = p.parse_args()

    if args.export_only:
        if not args.model_dir:
            p.error("--export_only requires --model_dir pointing to a trained checkpoint folder.")
        run_onnx_export(Path(args.model_dir), Path(args.onnx_dir), args.opset)
        return

    run_training(args)
    if args.export_onnx:
        run_onnx_export(Path(args.output_dir), Path(args.onnx_dir), args.opset)


if __name__ == "__main__":
    main()
