# Data prep for GPT-style training on short text with variable lengths
# Strategy: concatenate all texts into a single token stream, separated by
# '<|endoftext|>'. GPT can learn to ignore attention from a previous work. 
# Then sample fixed-length windows that always *start* at a text boundary.
# Windows are padded with '<|endoftext|>' so every sample has the same length. 
# As time complexity of an attention head is O(T^2), we don't want the
# context window to be too large, in our case, no bigger than the longest text. 
# This name boundary alignment is a good practice when window length is 
# comparable to word length: the model does not waste time on learning
# how to complete text without the beginning. 

# Run this file to generate a histogram of text length. 

import random, torch
from torch.utils.data import Dataset, DataLoader
from collections import defaultdict, Counter
import math
from config import split, epoch_steps
import csv
import tiktoken
import matplotlib.pyplot as plt

tok = tiktoken.get_encoding("cl100k_base")

def csv_to_tensor(csv_path: str, tok, text_col: str = "Joke",
                  eos_token: str = "<|endoftext|>"):
    """
    Read jokes from a CSV, tokenize each, append EOS after every joke,
    then compact token IDs to a contiguous range [0..V_used-1].

    Returns:
        ids_c:        1D LongTensor of compacted token IDs for the whole corpus
        comp2orig:    1D LongTensor mapping compact_id -> original_token_id
        joke_len:     list[int], tokenized length of each joke (before EOS)
    """
    all_ids = []
    joke_len = []

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            j = row.get(text_col)
            if not j:
                continue
            # tokenize the joke
            ids = tok.encode(j, allowed_special={eos_token})
            joke_len.append(len(ids))
            all_ids.extend(ids)
            # append EOS between jokes
            all_ids.extend(tok.encode(eos_token, allowed_special={eos_token}))

    ids = torch.tensor(all_ids, dtype=torch.long)

    # compactify: map original token IDs -> [0..V_used-1]
    comp2orig, ids_c = torch.unique(ids, sorted=True, return_inverse=True)
    # ids_c is the corpus with compact IDs
    return ids_c, comp2orig, joke_len

# Enter the file path here
jokes, comp2orig, joke_len = csv_to_tensor(
    "Dataset/examiner-date-text-shuffled.csv",
    tok, 
    text_col = "headline_text"
)
orig2comp = {int(o): i for i, o in enumerate(comp2orig.tolist())}
vocab_size = len(comp2orig)

def stot(s: str) -> torch.Tensor:
    ids = tok.encode(s, allowed_special={"<|endoftext|>"})
    return torch.tensor([orig2comp[x] for x in ids], dtype=torch.long)

def ttos(t: torch.Tensor, for_output: bool = False) -> str:
    orig = comp2orig[t.to(torch.long).cpu()]
    out = tok.decode(orig.tolist())
    return out.replace("<|endoftext|>", "\n") if for_output else out

class BlockPairDataset(Dataset):
    """
    Dataset that samples fixed-length windows of token IDs from a name stream.

    - Takes a long tensor as input
    - Each sample starts at the beginning of a name (just after a '<|endoftext|>').
    - Each sample is exactly block_size long (x,y), padded with '<|endoftext|>' if needed.
    - x: [block_size] token IDs
    - y: [block_size] token IDs (x shifted by one position)
    """
    def __init__(self, data_u8: torch.Tensor, T: int, random=True):
        self.data = data_u8         # token-id stream (int tensor)
        self.T = T
        self.random = random

        # Locate all newline token indices; starts are 1 token after each newline
        nl_id = stot("<|endoftext|>")
        nl_positions = torch.where(self.data == nl_id)[0]
        self.starts = (nl_positions[:-1] + 1)   # skip last newline (no name after)

        # Define nominal dataset length for DataLoader
        self.N = epoch_steps if self.random else len(self.starts) 

    def __len__(self):
        # DataLoader will treat this as "samples per epoch"
        return self.N

    def __getitem__(self, i:int):
        if self.random:
            # Pick a random start position (aligned to a name boundary)
            s = self.starts[torch.randint(len(self.starts), (1,))].item()
        else:
            s = self.starts[i].item()        

        # Take T+1 tokens so we can form (x,y) with a one-step shift
        end = min(s + self.T + 1, len(self.data))
        seq = self.data[s:end]

        # If near end-of-stream, pad with '<|endoftext|>' token to fixed length
        if seq.numel() < self.T + 1:
            pad_len = self.T + 1 - seq.numel()
            pad = torch.full((pad_len,), stot("<|endoftext|>").item(), dtype=self.data.dtype)
            seq = torch.cat([seq, pad], dim=0)

        # Already token IDs; ensure proper dtype for embeddings
        x = seq[:-1].long()   # input sequence
        y = seq[1:].long()    # target sequence
        return x, y

def Construct_data_loaders(jokes:torch.Tensor, T, batch_size) -> DataLoader:
    # Train/val split into two tensors
    len_ = jokes.numel()
    len_tr = int(len_ * split)
    len_val = len_ - len_tr
    jokes_tr, jokes_val = jokes.split([len_tr, len_val])

    # Convert torch.Tensor to Dataset of proper context blocks
    ds_tr = BlockPairDataset(jokes_tr, T, random = True) 
    ds_va = BlockPairDataset(jokes_val, T, random = False)

    # Convert the Datasets to Dataloaders
    # train_loader = DataLoader(ds_tr, batch_size=batch_size, num_workers=0, pin_memory=False)
    # val_loader   = DataLoader(ds_va, batch_size=1, num_workers=0, pin_memory=False)
    train_loader = DataLoader(
        ds_tr,
        batch_size=batch_size,
        shuffle=True,
        num_workers=8,
        pin_memory=True,
        prefetch_factor=4,
        persistent_workers=True,
    )
    val_loader = DataLoader(
        ds_va,
        batch_size=8,
        num_workers=2,
        pin_memory=True,
    )
    
    print(f"Training data (one epoch) consist of {len(ds_tr)} batched blocks of text.", flush=True)
    print(f"Validation data consist of {len(ds_va)} batched blocks of text.\n", flush=True)
    return train_loader, val_loader

def main():
    plt.hist(joke_len, bins=30, edgecolor='black')
    plt.xlabel("Joke length (in tokens)")
    plt.ylabel("Frequency")
    plt.title("Histogram of Joke Lengths")
    plt.show()
    print(f"There are {len(joke_len)} jokes in total.")
    print(f"There are {vocab_size} distinct tokens.")
    
if __name__ == "__main__":
    main()
