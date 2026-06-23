"""
train_finetune.py — Fine-tune the Xception deepfake detector on YOUR labeled data.

This is the real path to >=75% fake / <=20% real on your own domain
(e.g. WhatsApp-compressed clips, your specific fake generator). Off-the-shelf
FF++ models do not separate compressed/out-of-domain video; training on your
data does.

USAGE (run on the GTX 1650 laptop for speed; works on CPU too, just slower):

    python train_finetune.py --data "C:/path/to/dataset" --epochs 15

`dataset/` must contain two folders: `real/` and `fake/`, each full of videos
(.mp4/.mov/...) or face images (.jpg/.png). Videos are auto-sampled to faces.

Output: overwrites `xception_deepfake.pt` with your fine-tuned weights, which
classifier.py loads automatically (native-timm format is supported).

DATA NEEDED: this works with anything, but for a reliable 75/20 you want
~200+ real and ~200+ fake clips of the target type. With <50 total it will
overfit — treat results as a smoke test, not production accuracy.
"""

import os, sys, glob, argparse, random, shutil
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from PIL import Image

_VID = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")
_IMG = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
_HERE = os.path.dirname(os.path.abspath(__file__))
_CKPT = os.path.join(_HERE, "xception_deepfake.pt")


def collect_faces(data_dir, cache_dir, max_frames_per_video=30):
    """Extract face crops from each class folder into cache_dir/{real,fake}."""
    from frame_extractor import extract_frames
    from face_detector import detect_faces_batch

    samples = []  # (face_path, label)  label: 0=real 1=fake
    for label_name, label in (("real", 0), ("fake", 1)):
        src = os.path.join(data_dir, label_name)
        dst = os.path.join(cache_dir, label_name)
        os.makedirs(dst, exist_ok=True)
        if not os.path.isdir(src):
            print(f"WARN: {src} missing"); continue

        # already-cached faces
        cached = [p for p in glob.glob(os.path.join(dst, "*")) if p.lower().endswith(_IMG)]
        if cached:
            print(f"[{label_name}] using {len(cached)} cached faces")
            samples += [(p, label) for p in cached]
            continue

        files = [p for p in glob.glob(os.path.join(src, "*")) if p.lower().endswith(_VID + _IMG)]
        print(f"[{label_name}] {len(files)} source files -> extracting faces...")
        idx = 0
        for f in files:
            if f.lower().endswith(_IMG):
                from face_detector import detect_face
                out = detect_face(f, dst)
                if out: samples.append((out, label)); idx += 1
                continue
            tmp = os.path.join(cache_dir, "_frames")
            if os.path.exists(tmp): shutil.rmtree(tmp)
            os.makedirs(tmp, exist_ok=True)
            extract_frames(f, tmp, max_frames=max_frames_per_video)
            frames = [os.path.join(tmp, x) for x in sorted(os.listdir(tmp))]
            saved = detect_faces_batch(frames, dst)
            for s in saved:
                if s:
                    # rename to unique to avoid collisions across videos
                    uniq = os.path.join(dst, f"f{idx:06d}.jpg")
                    try: os.replace(s, uniq); samples.append((uniq, label)); idx += 1
                    except OSError: pass
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"[{label_name}] -> {idx} faces")
    return samples


class RandomJPEG:
    """Randomly re-encode as JPEG at low quality — mimics WhatsApp/social
    recompression so the model learns to see through compression artifacts.
    This directly targets the false-positive-on-compressed-real problem."""
    def __init__(self, p=0.7, qmin=30, qmax=75):
        self.p, self.qmin, self.qmax = p, qmin, qmax
    def __call__(self, img):
        import io, random
        if random.random() > self.p:
            return img
        q = random.randint(self.qmin, self.qmax)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q)
        buf.seek(0)
        return Image.open(buf).convert("RGB")


class FaceDS(Dataset):
    def __init__(self, samples, train=True):
        self.samples = samples
        from torchvision import transforms
        aug = [transforms.Resize((299, 299))]
        if train:
            aug += [transforms.RandomHorizontalFlip(),
                    RandomJPEG(p=0.7),                       # compression augmentation
                    transforms.ColorJitter(0.1, 0.1, 0.1),
                    transforms.RandomRotation(5)]
        aug += [transforms.ToTensor(),
                transforms.Normalize([0.5]*3, [0.5]*3)]
        self.tf = transforms.Compose(aug)

    def __len__(self): return len(self.samples)

    def __getitem__(self, i):
        p, y = self.samples[i]
        img = Image.open(p).convert("RGB")
        return self.tf(img), y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=r"C:\Users\nbeni\OneDrive\Desktop\deepfake\dataset")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--cache", default=os.path.join(_HERE, "_face_cache"))
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {dev}  ({torch.cuda.get_device_name(0) if dev=='cuda' else 'CPU'})")

    samples = collect_faces(args.data, args.cache)
    if len(samples) < 8:
        print(f"ERROR: only {len(samples)} faces — need more labeled data."); return
    random.seed(42); random.shuffle(samples)
    n_val = max(2, int(len(samples) * 0.2))
    val, train = samples[:n_val], samples[n_val:]
    n_fake = sum(1 for _, y in train if y == 1)
    print(f"Train {len(train)} (fake {n_fake}/{len(train)-n_fake} real)  Val {len(val)}")

    tl = DataLoader(FaceDS(train, True),  batch_size=args.batch, shuffle=True, num_workers=0)
    vl = DataLoader(FaceDS(val, False),   batch_size=args.batch, shuffle=False, num_workers=0)

    import timm
    model = timm.create_model("xception", pretrained=True, num_classes=2).to(dev)

    # class weighting (handle imbalance)
    n_real = sum(1 for _, y in train if y == 0)
    w = torch.tensor([1.0, max(0.2, n_real / max(1, n_fake))]).to(dev)
    crit = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)

    best_acc = 0.0
    for ep in range(1, args.epochs + 1):
        model.train(); tot = 0; loss_sum = 0
        for x, y in tl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            out = model(x); loss = crit(out, y)
            loss.backward(); opt.step()
            loss_sum += loss.item() * len(y); tot += len(y)
        # val
        model.eval(); correct = 0; vt = 0
        with torch.no_grad():
            for x, y in vl:
                x, y = x.to(dev), y.to(dev)
                pred = model(x).argmax(1)
                correct += (pred == y).sum().item(); vt += len(y)
        acc = correct / max(1, vt)
        print(f"epoch {ep:2d}  train_loss {loss_sum/max(1,tot):.4f}  val_acc {acc:.3f}")
        if acc >= best_acc:
            best_acc = acc
            torch.save(model.state_dict(), _CKPT)   # native timm format (classifier.py loads it)
            print(f"   saved best -> {_CKPT} (val_acc {acc:.3f})")

    print(f"\nDone. Best val_acc {best_acc:.3f}. Restart the server to use new weights.")


if __name__ == "__main__":
    main()
