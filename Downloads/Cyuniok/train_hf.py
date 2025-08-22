from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from datasets import Dataset, load_metric
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding,
)
import numpy as np
import csv
import json

DATA_PATH = Path("data/case_data.csv")
OUT_DIR = Path("models/hf")
MODEL_NAME = os.getenv("HF_BASE_MODEL", "nlpaueb/legal-bert-base-uncased")
MAX_LEN = int(os.getenv("HF_MAX_LEN", "512"))


def load_rows(path: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        assert {'summary','outcome'}.issubset(reader.fieldnames or [])
        for r in reader:
            s = (r.get('summary') or '').strip()
            o = (r.get('outcome') or '').strip()
            if s and o:
                rows.append((s,o))
    if not rows:
        raise RuntimeError('No rows found in CSV')
    return rows


def make_splits(rows: List[Tuple[str,str]], test_size=0.2, seed=42):
    # Simple stratified split
    from collections import defaultdict
    import random
    by_label = defaultdict(list)
    for s,o in rows:
        by_label[o].append(s)
    rng = random.Random(seed)
    train_texts, train_labels, val_texts, val_labels = [], [], [], []
    for label, texts in by_label.items():
        rng.shuffle(texts)
        n_val = max(1, int(len(texts)*test_size)) if len(texts) > 4 else 1
        val = texts[:n_val]
        train = texts[n_val:]
        if not train:
            # fallback: move one to train
            train, val = val[:1], val[1:]
        train_texts += train
        train_labels += [label]*len(train)
        val_texts += val
        val_labels += [label]*len(val)
    return (train_texts, train_labels), (val_texts, val_labels)


def encode_dataset(tokenizer, texts, labels, label2id):
    enc = tokenizer(texts, truncation=True, max_length=MAX_LEN)
    enc['labels'] = [label2id[l] for l in labels]
    return Dataset.from_dict(enc)


def main():
    rows = load_rows(DATA_PATH)
    labels = sorted(list({o for _,o in rows}))
    label2id = {l:i for i,l in enumerate(labels)}
    id2label = {i:l for l,i in label2id.items()}

    (tr_texts, tr_labels), (va_texts, va_labels) = make_splits(rows)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(labels), id2label=id2label, label2id=label2id
    )

    train_ds = encode_dataset(tokenizer, tr_texts, tr_labels, label2id)
    val_ds = encode_dataset(tokenizer, va_texts, va_labels, label2id)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(OUT_DIR / 'runs'),
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        learning_rate=5e-5,
        num_train_epochs=3,
        weight_decay=0.01,
        evaluation_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='f1',
        logging_steps=50,
        report_to=[],
    )

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        from sklearn.metrics import accuracy_score, f1_score
        return {
            'accuracy': accuracy_score(labels, preds),
            'f1': f1_score(labels, preds, average='macro'),
        }

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    # Save model and tokenizer
    model.save_pretrained(OUT_DIR)
    tokenizer.save_pretrained(OUT_DIR)

    meta = {
        'base_model': MODEL_NAME,
        'labels': labels,
        'max_len': MAX_LEN,
    }
    with (OUT_DIR / 'hf_metadata.json').open('w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    print(f"Saved HF model to {OUT_DIR}")


if __name__ == '__main__':
    main()
