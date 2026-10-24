import sys, json
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from collections import deque
cutA, cutB, boxesjson, names_csv, export_csv, checkpng = sys.argv[1:7]
A_img=Image.open(cutA).convert('RGBA'); W,H=A_img.size
A=A_img.getchannel('A')
B=Image.open(cutB).convert('RGBA').getchannel('A').filter(ImageFilter.MinFilter(5))
alpha=ImageChops.lighter(A,B)
boxes=json.load(open(boxesjson)); names=names_csv.split(','); export=set(export_csv.split(','))
S=2; a=alpha.resize((W//S,H//S),Image.BOX); w,h=a.size; ap=a.load(); TH=20
lab=[[0]*w for _ in range(h)]; comps=[]
for y in range(h):
    for x in range(w):
        if ap[x,y]>TH and not lab[y][x]:
            cid=len(comps)+1; q=deque([(x,y)]); lab[y][x]=cid; b=[x,y,x,y]
            while q:
                cx,cy=q.popleft(); b=[min(b[0],cx),min(b[1],cy),max(b[2],cx),max(b[3],cy)]
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<w and 0<=ny<h and not lab[ny][nx] and ap[nx,ny]>TH: lab[ny][nx]=cid; q.append((nx,ny))
            comps.append(b)
def overlap(p,q): return max(0,min(p[2],q[2])-max(p[0],q[0]))*max(0,min(p[3],q[3])-max(p[1],q[1]))
owner={}
for cid,b in enumerate(comps,1):
    fb=[v*S for v in b]; best=max(range(len(boxes)),key=lambda i:overlap(fb,boxes[i]))
    if overlap(fb,boxes[best])>0: owner[cid]=best
def hull(pts):
    pts=sorted(set(pts))
    if len(pts)<3: return pts
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[]
    for p in pts:
        while len(lo)>=2 and cross(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    up=[]
    for p in reversed(pts):
        while len(up)>=2 and cross(up[-2],up[-1],p)<=0: up.pop()
        up.append(p)
    return lo[:-1]+up[:-1]
done=[]
for i,n in enumerate(names):
    if n not in export: continue
    # icon component mask at half scale
    pts=[]
    m=Image.new('L',(w,h),0); mp=m.load()
    for y in range(h):
        row=lab[y]; xs=[x for x in range(w) if row[x] and owner.get(row[x])==i and ap[x,y]>60]
        if xs: pts.append((xs[0],y)); pts.append((xs[-1],y))
        for x in xs: mp[x,y]=255
    hp=hull(pts)
    hm=Image.new('L',(w,h),0); ImageDraw.Draw(hm).polygon(hp,fill=255)
    hm=hm.resize((W,H),Image.BILINEAR).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(1.4))
    iso=A_img.copy(); iso.putalpha(hm)
    bb=hm.point(lambda v:255 if v>20 else 0).getbbox(); sub=iso.crop(bb)
    s=int(max(sub.size)*1.10); sq=Image.new('RGBA',(s,s),(0,0,0,0)); sq.paste(sub,((s-sub.width)//2,(s-sub.height)//2))
    sq.resize((512,512),Image.LANCZOS).save(f'icons/master/{n}.png',optimize=True)
    sq.resize((256,256),Image.LANCZOS).save(f'icons/site/{n}.png',optimize=True); done.append(n)
sheet=Image.new('RGBA',(len(done)*280,280),(255,255,255,255))
for i,k in enumerate(done): sheet.alpha_composite(Image.open(f'icons/site/{k}.png'),(i*280+12,12))
sheet.save(checkpng); print('exported',done)
