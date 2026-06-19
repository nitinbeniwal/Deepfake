import cv2, numpy as np

def _g(p): return cv2.imread(p, cv2.IMREAD_GRAYSCALE)
def _c(p): return cv2.imread(p)

def freq_score(path):
    img = _g(path)
    if img is None: return 0
    img = cv2.resize(img,(256,256)).astype(np.float32)
    mag = 20*np.log(np.abs(np.fft.fftshift(np.fft.fft2(img)))+1)
    mag = (mag-mag.min())/(mag.max()-mag.min()+1e-8)
    h,w = mag.shape; mask = np.ones_like(mag)
    mask[h//2-h//10:h//2+h//10, w//2-w//10:w//2+w//10] = 0
    flat = (mag*mask).flatten()
    ratio = np.percentile(flat,99)/(np.mean(flat[flat>0])+1e-8)
    return round(float(min(100,max(0,(ratio-2)*15))),1)

def compress_score(path):
    img = _g(path)
    if img is None: return 0
    f = img.astype(float); h,_ = img.shape
    b = [np.mean(np.abs(f[i]-f[i-1])) for i in range(1,h) if i%8==0]
    n = [np.mean(np.abs(f[i]-f[i-1])) for i in range(1,h) if i%8!=0]
    if not b or not n: return 0
    r = np.mean(b)/(np.mean(n)+1e-8)
    if r>4:   return round(float(min(100,(r-4)*10+30)),1)
    if r<0.5: return round(float(min(100,(0.5-r)*60+20)),1)
    return 0

def noise_score(path):
    img = _g(path)
    if img is None: return 0
    f = img.astype(np.float32); noise = f - cv2.GaussianBlur(f,(5,5),0)
    std = float(np.std(noise))
    if std < 1.5: s = min(100,(1.5-std)*40+20)
    elif std > 25: s = min(100,(std-25)*2+15)
    else: s = 0
    h,w = img.shape
    qs = [float(np.std(noise[r*h//2:(r+1)*h//2, c*w//2:(c+1)*w//2])) for r in range(2) for c in range(2)]
    if qs and np.std(qs) > std*0.8: s = min(100,s+15)
    return round(float(s),1)

def boundary_score(path):
    img = _g(path)
    if img is None or img.shape[0]<32: return 0
    h,w = img.shape; bh,bw = max(4,int(h*0.15)), max(4,int(w*0.15))
    mask = np.zeros((h,w),dtype=bool)
    mask[:bh,:]=mask[-bh:,:]=mask[:,:bw]=mask[:,-bw:]=True
    lap = np.abs(cv2.Laplacian(img,cv2.CV_64F))
    bv,iv = float(np.mean(lap[mask])), float(np.mean(lap[~mask]))
    r = bv/(iv+1e-8)
    if r>3:   return round(float(min(100,(r-3)*20+20)),1)
    if r<0.3: return round(float(min(100,(0.3-r)*100+15)),1)
    return 0

def color_score(paths):
    cb,cr = [],[]
    for p in paths[:20]:
        img = _c(p)
        if img is None: continue
        y = cv2.cvtColor(img,cv2.COLOR_BGR2YCrCb).astype(float)
        cb.append(float(np.mean(y[:,:,1]))); cr.append(float(np.mean(y[:,:,2])))
    if len(cb)<2: return 0
    var = (float(np.std(cb))+float(np.std(cr)))/2
    if var>8:  return round(float(min(100,(var-8)*5+30)),1)
    if var>4:  return round(float(min(100,(var-4)*5+10)),1)
    return 0

def temporal_score(paths):
    imgs = [cv2.resize(_g(p),(64,64)).astype(np.float32) for p in paths[:15] if _g(p) is not None]
    if len(imgs)<3: return 0
    diffs = [float(np.mean(np.abs(imgs[i]-imgs[i-1]))) for i in range(1,len(imgs))]
    mean_d = float(np.mean(diffs)); cv = float(np.std(diffs))/(mean_d+1e-8)
    s = 0
    if cv>1.5:                     s += min(50,(cv-1.5)*20+10)
    if max(diffs)/(mean_d+1e-8)>5: s += min(50,((max(diffs)/(mean_d+1e-8))-5)*5+10)
    return round(float(min(100,s)),1)

def run_all_forensic_rules(face_paths, **_):
    if not face_paths: return {"score":0,"details":{},"anomalies":[]}
    s = [p for p in face_paths[:10] if cv2.imread(p) is not None]
    if not s: return {"score":0,"details":{},"anomalies":[]}
    n = len(s)
    scores = {
        "frequency":   sum(freq_score(p)    for p in s)/n,
        "compression": sum(compress_score(p) for p in s)/n,
        "noise":       sum(noise_score(p)   for p in s)/n,
        "boundary":    sum(boundary_score(p) for p in s)/n,
        "color":       color_score(face_paths),
        "temporal":    temporal_score(face_paths),
    }
    W = {"frequency":.20,"compression":.15,"noise":.20,"boundary":.20,"color":.15,"temporal":.10}
    combined = sum(scores[k]*W[k] for k in W)
    return {
        "score":    round(combined,1),
        "details":  {k:round(v,1) for k,v in scores.items()},
        "anomalies":[f"{k.capitalize()} anomaly: {v:.0f}%" for k,v in scores.items() if v>30],
    }
