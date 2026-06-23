import json, uuid, os

def cid():
    return uuid.uuid4().hex[:8]

cells = []

# --- Cell 0: title ---
cells.append({
    "cell_type": "markdown", "id": cid(), "metadata": {},
    "source": [
        "# Deepfake Xception Fine-Tune — FF++ + manjilkarki\n",
        "Trains binary deepfake classifier. Target: fake_recall >= 0.60, real_spec >= 0.70.\n",
        "Add both datasets via **+ Add Input** then enable **GPU T4 x2** in Notebook settings."
    ]
})

# --- Cell 1: install + GPU check ---
cells.append({
    "cell_type": "code", "id": cid(), "metadata": {}, "outputs": [],
    "source": [
        "!pip -q install timm efficientnet_pytorch facenet-pytorch opencv-python-headless 2>/dev/null\n",
        "import os, torch, random\n",
        "ON_KAGGLE = os.path.exists('/kaggle')\n",
        "ON_COLAB  = 'COLAB_GPU' in os.environ or os.path.exists('/content')\n",
        "DEV = 'cuda' if torch.cuda.is_available() else 'cpu'\n",
        "print('Platform:', 'Kaggle' if ON_KAGGLE else 'Colab' if ON_COLAB else 'local')\n",
        "print('Device  :', DEV, torch.cuda.get_device_name(0) if DEV=='cuda' else '')\n",
        "if DEV != 'cuda':\n",
        "    print('NO GPU — Kaggle: ... menu -> Accelerator -> GPU T4 x2 -> Save')\n",
        "    raise SystemExit('GPU required. Enable it then re-run all.')\n"
    ]
})

# --- Cell 2: data markdown ---
cells.append({
    "cell_type": "markdown", "id": cid(), "metadata": {},
    "source": [
        "## Data\n",
        "Add these two datasets via **+ Add Input** on right panel:\n",
        "1. `gradientvoyager/faceforensics-c23-extracted-faces-100k` (FF++ C23, 100k faces)\n",
        "2. `manjilkarki/deepfake-and-real-images` (190k face crops)\n",
        "\n",
        "Either one alone is enough to start."
    ]
})

# --- Cell 3: collect samples ---
cells.append({
    "cell_type": "code", "id": cid(), "metadata": {}, "outputs": [],
    "source": [
        "import glob\n",
        "from PIL import Image\n",
        "\n",
        "_IMG = ('.jpg','.jpeg','.png','.bmp','.webp')\n",
        "REAL_NAMES = {'real','original','pristine','0_real','genuine'}\n",
        "FAKE_NAMES = {'fake','deepfakes','face2face','faceswap','neuraltextures',\n",
        "              'faceshifter','1_fake','manipulated','altered','generated','ai'}\n",
        "\n",
        "def scan_dir(root, cap=30000):\n",
        "    found = []\n",
        "    for dp, dn, fns in os.walk(root):\n",
        "        name = os.path.basename(dp).lower()\n",
        "        if name in REAL_NAMES: lab = 0\n",
        "        elif name in FAKE_NAMES: lab = 1\n",
        "        else: continue\n",
        "        imgs = [os.path.join(dp,f) for f in fns if f.lower().endswith(_IMG)]\n",
        "        if len(imgs) > cap: imgs = random.sample(imgs, cap)\n",
        "        found += [(p, lab) for p in imgs]\n",
        "    return found\n",
        "\n",
        "samples = []\n",
        "\n",
        "# FF++ C23 extracted faces\n",
        "ff_root = '/kaggle/input/faceforensics-c23-extracted-faces-100k'\n",
        "if os.path.isdir(ff_root):\n",
        "    s = scan_dir(ff_root, cap=25000)\n",
        "    print(f'FF++: {len(s)} (fake={sum(1 for _,l in s if l==1)} real={sum(1 for _,l in s if l==0)})')\n",
        "    samples += s\n",
        "else:\n",
        "    print('FF++ not attached — add: gradientvoyager/faceforensics-c23-extracted-faces-100k')\n",
        "\n",
        "# manjilkarki deepfake-and-real-images\n",
        "for mj in ['/kaggle/input/deepfake-and-real-images/Dataset',\n",
        "           '/kaggle/input/deepfake-and-real-images']:\n",
        "    if os.path.isdir(mj):\n",
        "        s = scan_dir(mj, cap=20000)\n",
        "        print(f'manjilkarki: {len(s)} (fake={sum(1 for _,l in s if l==1)} real={sum(1 for _,l in s if l==0)})')\n",
        "        samples += s; break\n",
        "else:\n",
        "    print('manjilkarki not attached — add: manjilkarki/deepfake-and-real-images')\n",
        "\n",
        "random.seed(42); random.shuffle(samples)\n",
        "n_fake = sum(1 for _,l in samples if l==1)\n",
        "n_real = sum(1 for _,l in samples if l==0)\n",
        "print(f'\\nTotal {len(samples)} | fake {n_fake} | real {n_real}')\n",
        "assert len(samples) >= 200, 'Too few samples. Attach at least one dataset.'\n"
    ]
})

# --- Cell 4: dataset + loaders ---
cells.append({
    "cell_type": "code", "id": cid(), "metadata": {}, "outputs": [],
    "source": [
        "import io\n",
        "from torch.utils.data import Dataset, DataLoader\n",
        "from torchvision import transforms\n",
        "\n",
        "class RandomJPEG:\n",
        "    def __init__(self,p=0.6,qmin=25,qmax=80): self.p,self.qmin,self.qmax=p,qmin,qmax\n",
        "    def __call__(self,img):\n",
        "        if random.random()>self.p: return img\n",
        "        b=io.BytesIO(); img.save(b,'JPEG',quality=random.randint(self.qmin,self.qmax))\n",
        "        b.seek(0); return Image.open(b).convert('RGB')\n",
        "\n",
        "class FaceDS(Dataset):\n",
        "    def __init__(self,items,train=True):\n",
        "        self.items=items\n",
        "        aug=[transforms.Resize((299,299))]\n",
        "        if train:\n",
        "            aug+=[transforms.RandomHorizontalFlip(),\n",
        "                  RandomJPEG(0.6),\n",
        "                  transforms.ColorJitter(0.15,0.15,0.1,0.05),\n",
        "                  transforms.RandomRotation(10),\n",
        "                  transforms.RandomGrayscale(p=0.02)]\n",
        "        aug+=[transforms.ToTensor(),transforms.Normalize([0.5]*3,[0.5]*3)]\n",
        "        self.tf=transforms.Compose(aug)\n",
        "    def __len__(self): return len(self.items)\n",
        "    def __getitem__(self,i):\n",
        "        p,y=self.items[i]\n",
        "        try: img=Image.open(p).convert('RGB')\n",
        "        except: img=Image.new('RGB',(299,299))\n",
        "        return self.tf(img),y\n",
        "\n",
        "nval=max(100,int(len(samples)*0.15))\n",
        "val_s,train_s=samples[:nval],samples[nval:]\n",
        "print(f'Train {len(train_s)} | Val {len(val_s)}')\n",
        "tl=DataLoader(FaceDS(train_s,True), batch_size=64,shuffle=True, num_workers=4,pin_memory=True)\n",
        "vl=DataLoader(FaceDS(val_s,  False),batch_size=64,shuffle=False,num_workers=4,pin_memory=True)\n"
    ]
})

# --- Cell 5: train ---
cells.append({
    "cell_type": "code", "id": cid(), "metadata": {}, "outputs": [],
    "source": [
        "import timm, torch\n",
        "import torch.nn as nn\n",
        "from torch.cuda.amp import GradScaler, autocast\n",
        "\n",
        "model=timm.create_model('xception',pretrained=True,num_classes=2).to(DEV)\n",
        "\n",
        "nf=sum(1 for _,l in train_s if l==1)\n",
        "nr=sum(1 for _,l in train_s if l==0)\n",
        "# up-weight minority class\n",
        "if nr >= nf:\n",
        "    w=torch.tensor([1.0, nr/max(1,nf)]).to(DEV)\n",
        "else:\n",
        "    w=torch.tensor([nf/max(1,nr), 1.0]).to(DEV)\n",
        "print(f'Class weights: real={w[0]:.3f} fake={w[1]:.3f}  (train real={nr} fake={nf})')\n",
        "\n",
        "crit =nn.CrossEntropyLoss(weight=w)\n",
        "opt  =torch.optim.AdamW(model.parameters(),lr=1e-4,weight_decay=1e-4)\n",
        "sched=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=15)\n",
        "scaler=GradScaler()\n",
        "\n",
        "EPOCHS=15; best_acc=0.0; best_ep=0\n",
        "for ep in range(1,EPOCHS+1):\n",
        "    model.train(); ls=0; n=0\n",
        "    for x,y in tl:\n",
        "        x,y=x.to(DEV),y.to(DEV); opt.zero_grad()\n",
        "        with autocast(): loss=crit(model(x),y)\n",
        "        scaler.scale(loss).backward(); scaler.step(opt); scaler.update()\n",
        "        ls+=loss.item()*len(y); n+=len(y)\n",
        "    sched.step()\n",
        "    model.eval(); tp=fp=fn=tn=0\n",
        "    with torch.no_grad():\n",
        "        for x,y in vl:\n",
        "            x,y=x.to(DEV),y.to(DEV); pr=model(x).argmax(1)\n",
        "            tp+=((pr==1)&(y==1)).sum().item()\n",
        "            fp+=((pr==1)&(y==0)).sum().item()\n",
        "            fn+=((pr==0)&(y==1)).sum().item()\n",
        "            tn+=((pr==0)&(y==0)).sum().item()\n",
        "    acc=(tp+tn)/max(1,tp+fp+fn+tn)\n",
        "    fake_r=tp/max(1,tp+fn)   # want >=0.60\n",
        "    real_s=tn/max(1,tn+fp)   # want >=0.70 (FP<=0.30)\n",
        "    lr_=sched.get_last_lr()[0]\n",
        "    print(f'ep{ep:2d} loss {ls/max(1,n):.4f} acc {acc:.3f}  '\n",
        "          f'fake_recall {fake_r:.3f}  real_spec {real_s:.3f}  lr {lr_:.2e}')\n",
        "    if acc>=best_acc:\n",
        "        best_acc=acc; best_ep=ep\n",
        "        torch.save(model.state_dict(),'xception_deepfake.pt')\n",
        "        print(f'   -> saved ep{ep} (acc={acc:.3f})')\n",
        "\n",
        "print(f'\\nBest ep{best_ep} acc={best_acc:.3f}')\n",
        "print(f'Final: fake_recall={fake_r:.3f} (target>=0.60) | real_spec={real_s:.3f} (target>=0.70)')\n",
        "ok = 'PASS' if fake_r>=0.60 and real_s>=0.70 else 'NEEDS MORE DATA/EPOCHS'\n",
        "print('Target check:', ok)\n"
    ]
})

# --- Cell 6: download ---
cells.append({
    "cell_type": "code", "id": cid(), "metadata": {}, "outputs": [],
    "source": [
        "sz=os.path.getsize('xception_deepfake.pt')>>20\n",
        "print(f'xception_deepfake.pt — {sz} MB')\n",
        "if ON_COLAB:\n",
        "    from google.colab import files; files.download('xception_deepfake.pt')\n",
        "else:\n",
        "    print('Kaggle: Output panel -> download xception_deepfake.pt')\n",
        "    print('Then: copy to deepfake_detector/ and restart server.')\n"
    ]
})

nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"}
    },
    "cells": cells
}

out = r'C:/Users/nbeni/OneDrive/Desktop/deepfake/deepfake/Deepfake/deepfake_detector/train_colab_kaggle.ipynb'
with open(out, 'w') as f:
    json.dump(nb, f, indent=1)
print('Done:', out, '|', len(cells), 'cells')
