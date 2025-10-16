# headlineGPT

A minimal, nanoGPT-style language model trained on **short headline-like text**.  
The goal is to keep the code small and readable while making it easy to train and sample concise, punchy outputs.

---

## Features
- **Tiny, hackable codebase** (Transformer + LM head).
- **Short-sequence friendly dataloader** (many short snippets per batch).
- **Config-driven hyperparameters** (edit `config.py`).
- **Simple training & sampling scripts** (`run_train.py`, `run_pretrained.py`).
- **Basic logging/artifacts** (`loss_plot.png`, `generated.txt`).

---

## Repository Structure
```

config.py          # model & training hyperparameters
data_utils.py      # dataset building, tokenization, batching
model.py           # GPT model (Transformer + LM head)
train.py           # core training loop
run_train.py       # CLI to start training
run_pretrained.py  # CLI to load a checkpoint and generate text
generated.txt      # sample generations (for reference)
loss_plot.png      # training loss curve (for reference)
LICENSE
README.md

````

---

## Setup
```bash
# (optional) create a venv
python -m venv .venv && source .venv/bin/activate

# install dependencies (adjust as needed)
pip install torch numpy tqdm
````

---

## Data

Use a plain-text file of **short lines** (e.g., headlines or titles).
One example per line is the simplest starting point.

Example (toy):

```
Apple unveils new chip
Markets rally on jobs data
Researchers question room-temp superconductor claim
```

If you use a custom delimiter or multiple files, adjust paths/options in `data_utils.py` and/or `config.py`.

---

## Training

Edit `config.py` for model size, context length, batch size, steps, etc., then:

```bash
python run_train.py
```

This will:

* build/tokenize the dataset,
* train the model,
* save checkpoints and a loss log (see `loss_plot.png`).

---

## Generation

Load a trained checkpoint and generate headline-style text:

```bash
python run_pretrained.py --prompt "Quantum materials breakthrough:"
```

Common sampling knobs (if exposed): `--max_new_tokens`, `--temperature`, `--top_p`.

---

## Tips

* Headlines are short → prefer **short context** (e.g., 64–128) and **larger batch** if memory allows.
* Clean the corpus: dedupe, strip boilerplate, keep lines concise.
* For variety, try **temperature ~0.8–1.0** and **nucleus (top-p) sampling** at inference.

---

## License

MIT. Inspired by the simplicity and style of nanoGPT.

