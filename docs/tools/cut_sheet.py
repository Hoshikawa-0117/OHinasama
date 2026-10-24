import sys, json
from PIL import Image, ImageDraw, ImageFilter
from collections import deque
src, outprev, outjson, cutout = sys.argv[1:5]
im=Image.open(src).convert('RGB'); W,H=im.size; px=im.load()
def isbg(p):
    s=max(p)-min(p); l=sum(p)//3
    return s<40 and 100<=l<218
lab=bytearray(W*H); bg=bytearray(W*H)
for y0 in range(H):
    for x0 in range(W):
        i0=y0*W+x0
        if lab[i0] or not isbg(px[x0,y0]): continue
        q=deque([(x0,y0)]); lab[i0]=1; pts=[]; touch=False
        while q:
            x,y=q.popleft(); pts.append(y*W+x)
            if x==0 or y==0 or x==W-1 or y==H-1: touch=True
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if 0<=nx<W and 0<=ny<H:
                    j=ny*W+nx
                    if not lab[j] and isbg(px[nx,ny]): lab[j]=1; q.append((nx,ny))
        if not touch and len(pts)>300:
            light=sum(1 for j in pts if sum(px[j%W,j//W])//3>165)/len(pts)
            if not (0.2<light<0.8): continue
        if touch or len(pts)>300:
            for j in pts: bg[j]=1
mask=Image.frombytes('L',(W,H),bytes(255-255*b for b in bg))
mask=mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
rgba=im.convert('RGBA'); rgba.putalpha(mask); rgba.save(cutout)
S=4; m=mask.resize((W//S,H//S),Image.BOX); w,h=m.size; mp=m.load()
lb=[[0]*w for _ in range(h)]; comps=[]
for y in range(h):
    for x in range(w):
        if mp[x,y]>100 and not lb[y][x]:
            cid=len(comps)+1; qq=deque([(x,y)]); lb[y][x]=cid; a=[x,y,x,y]; n=0
            while qq:
                cx,cy=qq.popleft(); n+=1
                a=[min(a[0],cx),min(a[1],cy),max(a[2],cx),max(a[3],cy)]
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx,ny=cx+dx,cy+dy
                    if 0<=nx<w and 0<=ny<h and not lb[ny][nx] and mp[nx,ny]>100: lb[ny][nx]=cid; qq.append((nx,ny))
            if n>=4: comps.append((n,a))
comps.sort(key=lambda c:-c[0])
big=[c for c in comps if c[0]>=500]; small=[c for c in comps if c[0]<500]
def dist(a,b):
    dx=max(b[0]-a[2],a[0]-b[2],0); dy=max(b[1]-a[3],a[1]-b[3],0); return (dx*dx+dy*dy)**0.5
boxes=[list(c[1]) for c in big]
for n,a in small:
    j=min(range(len(boxes)),key=lambda i:dist(a,boxes[i]))
    if dist(a,boxes[j])<30:
        b=boxes[j]; boxes[j]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
# rows by y-center gaps
boxes.sort(key=lambda b:(b[1]+b[3])/2)
rows=[[boxes[0]]]
for b in boxes[1:]:
    pc=(rows[-1][-1][1]+rows[-1][-1][3])/2; c=(b[1]+b[3])/2
    if c-pc>25: rows.append([b])
    else: rows[-1].append(b)
boxes=[b for r in rows for b in sorted(r,key=lambda b:b[0])]
boxes=[[v*S for v in b] for b in boxes]
json.dump(boxes,open(outjson,'w'))
prev=Image.new('RGBA',(W,H),(243,240,255,255)); prev.alpha_composite(rgba); d=ImageDraw.Draw(prev)
for i,b in enumerate(boxes): d.rectangle(b,outline=(255,0,0,255),width=2); d.text((b[0]+4,b[1]+2),str(i),fill=(200,0,0,255))
prev.resize((W//2,H//2)).save(outprev)
print(len(boxes),'icons; rows:',[len(r) for r in rows])
