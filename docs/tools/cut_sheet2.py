import sys, json
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from collections import deque
src, outprev, cutout, outjson = sys.argv[1:5]
im=Image.open(src).convert('RGB'); W,H=im.size; px=im.load()
# luminance + local std (texture) via integral images, window R
R=7
lum=[[ (px[x,y][0]*299+px[x,y][1]*587+px[x,y][2]*114)//1000 for x in range(W)] for y in range(H)]
I=[[0]*(W+1) for _ in range(H+1)]; I2=[[0]*(W+1) for _ in range(H+1)]
for y in range(H):
    rs=0; rs2=0; row=lum[y]; Iy=I[y+1]; Iy0=I[y]; I2y=I2[y+1]; I2y0=I2[y]
    for x in range(W):
        v=row[x]; rs+=v; rs2+=v*v
        Iy[x+1]=Iy0[x+1]+rs; I2y[x+1]=I2y0[x+1]+rs2
def std(x,y):
    x0=max(0,x-R); y0=max(0,y-R); x1=min(W,x+R+1); y1=min(H,y+R+1); n=(x1-x0)*(y1-y0)
    s=I[y1][x1]-I[y0][x1]-I[y1][x0]+I[y0][x0]; s2=I2[y1][x1]-I2[y0][x1]-I2[y1][x0]+I2[y0][x0]
    v=s2/n-(s/n)**2; return v**0.5 if v>0 else 0
# checker-like: low saturation, mid luminance, textured
def isbg(x,y):
    r,g,b=px[x,y]; s=max(r,g,b)-min(r,g,b); l=lum[y][x]
    return s<45 and 95<=l<222 and std(x,y)>14
lab=bytearray(W*H); bg=bytearray(W*H)
cache={}
for y0 in range(H):
    for x0 in range(W):
        i0=y0*W+x0
        if lab[i0]: continue
        if not isbg(x0,y0): lab[i0]=1; continue
        q=deque([(x0,y0)]); lab[i0]=1; pts=[]; touch=False
        while q:
            x,y=q.popleft(); pts.append(y*W+x)
            if x==0 or y==0 or x==W-1 or y==H-1: touch=True
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if 0<=nx<W and 0<=ny<H:
                    j=ny*W+nx
                    if not lab[j]:
                        lab[j]=1
                        if isbg(nx,ny): q.append((nx,ny))
        if touch or len(pts)>250:
            for j in pts: bg[j]=1
mask=Image.frombytes('L',(W,H),bytes(255-255*b for b in bg))
# the texture test leaves a ~R px ring of checker around each icon (std falls near smooth areas) -> shrink mask
mask=mask.filter(ImageFilter.MinFilter(2*R+1))
mask=mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
rgba=im.convert('RGBA'); rgba.putalpha(mask); rgba.save(cutout)
# boxes
S=4; m=mask.resize((W//S,H//S),Image.BOX); w,h=m.size; mp=m.load()
lb=[[0]*w for _ in range(h)]; comps=[]
for y in range(h):
    for x in range(w):
        if mp[x,y]>100 and not lb[y][x]:
            cid=len(comps)+1; qq=deque([(x,y)]); lb[y][x]=cid; a=[x,y,x,y]; n=0
            while qq:
                cx,cy=qq.popleft(); n+=1; a=[min(a[0],cx),min(a[1],cy),max(a[2],cx),max(a[3],cy)]
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<w and 0<=ny<h and not lb[ny][nx] and mp[nx,ny]>100: lb[ny][nx]=cid; qq.append((nx,ny))
            if n>=4: comps.append((n,a))
comps.sort(key=lambda c:-c[0]); big=[c for c in comps if c[0]>=500]; small=[c for c in comps if c[0]<500]
def dist(a,b):
    dx=max(b[0]-a[2],a[0]-b[2],0); dy=max(b[1]-a[3],a[1]-b[3],0); return (dx*dx+dy*dy)**0.5
boxes=[list(c[1]) for c in big]
for n,a in small:
    j=min(range(len(boxes)),key=lambda i:dist(a,boxes[i]))
    if dist(a,boxes[j])<30: b=boxes[j]; boxes[j]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
boxes.sort(key=lambda b:(b[1]+b[3])/2); rows=[[boxes[0]]]
for b in boxes[1:]:
    pc=(rows[-1][-1][1]+rows[-1][-1][3])/2; c=(b[1]+b[3])/2
    if c-pc>25: rows.append([b])
    else: rows[-1].append(b)
boxes=[[v*S for v in b] for r in rows for b in sorted(r,key=lambda b:b[0])]
json.dump(boxes,open(outjson,'w'))
prev=Image.new('RGBA',(W,H),(60,60,90,255)); prev.alpha_composite(rgba); d=ImageDraw.Draw(prev)
for i,b in enumerate(boxes): d.rectangle(b,outline=(255,0,0,255),width=2); d.text((b[0]+4,b[1]+2),str(i),fill=(255,80,80,255))
prev.resize((W//2,H//2)).save(outprev); print(len(boxes),'icons; rows:',[len(r) for r in rows])
