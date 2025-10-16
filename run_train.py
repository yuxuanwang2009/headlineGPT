import argparse
import torch
from config import *
from model import GPTLanguageModel
from train import Train, unique_params
from data_utils import jokes, Construct_data_loaders, vocab_size
from run_pretrained import load_pretrained
import os
import logging


# silence Inductor autotune logs 
os.environ["TORCHINDUCTOR_VERBOSE"] = "0"
logging.getLogger("torch._inductor").setLevel(logging.CRITICAL)

# Add global TF32 + matmul precision flags
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.set_float32_matmul_precision("high")

def main():
    # CLI options
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", "-r",  action="store_true", help="Resume training from checkpoint.pt")
    args = parser.parse_args()

    # 1. Construct the model
    if not args.resume:
        model = GPTLanguageModel(
            vocab_size=vocab_size,
            n_emb=n_emb,
            n_heads=n_heads,
            n_ffd_hidden = n_ffd_hidden,
            n_layers=n_layers,
            T=T,
            dropout=dropout,
            device = device
        ).to(device)
        # Compile
        model = torch.compile(model, mode="max-autotune")

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    
    # 2. Optionally resume from checkpoint
    else:
        model, optimizer = load_pretrained("checkpoint.pt", training=True)
    print(f"\nThe model has {sum(p.numel() for p in model.parameters())/1e6}M parameters.\n", flush=True)

    # 3. Build dataloaders
    train_loader, val_loader = Construct_data_loaders(jokes, T, batch_size=batch_size)

    # 4. Train and save weights
    Train(model, train_loader, val_loader, optimizer, eval_interval, minimal_lr=1e-6, device=device)

if __name__ == "__main__":
    main()
