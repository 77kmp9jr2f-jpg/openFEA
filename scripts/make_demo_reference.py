"""Render a known CAD solid as a labelled synthetic image-input fixture."""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def main():
    model=json.loads(Path(sys.argv[1]).read_text())
    image=Image.new('RGB',(1200,900),'#f6f5ef');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',24)
    small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
    draw.text((55,40),'FEA-R / DEMONSTRATION REFERENCE',fill='#55644b',font=font)
    draw.text((55,80),'Synthetic CAD render. Dimensions and scale intentionally omitted.',fill='#8a9680',font=small)
    points=np.array(model['nodes']);eye=np.array([1.6,-2.2,1.6]);eye/=np.linalg.norm(eye)
    right=np.cross([0,0,1],eye);right/=np.linalg.norm(right);up=np.cross(eye,right)
    uv=points@np.stack([right,-up],axis=1);span=np.ptp(uv,axis=0);scale=min(850/span[0],650/span[1]);center=(uv.min(axis=0)+uv.max(axis=0))/2;xy=(uv-center)*scale+[600,485]
    faces=[(tri,face) for face in model['faces'] for tri in face['triangles']]
    faces.sort(key=lambda pair:float((points[pair[0]]@eye).mean()))
    for tri,face in faces:
        normal=np.cross(points[tri[1]]-points[tri[0]],points[tri[2]]-points[tri[0]])
        normal/=max(np.linalg.norm(normal),1e-20)
        light=.6+.4*abs(float(normal@np.array([.3,-.4,.866])))
        c=tuple(int(v*light) for v in (126,157,139))
        draw.polygon([tuple(xy[i]) for i in tri],fill=c)
    draw.text((55,845),'Reference 01 / use the annotation tools to describe measured dimensions.',fill='#839378',font=small)
    out=Path(__file__).resolve().parents[1]/'public'/'demo-reference.png';image.save(out);print(out)

if __name__=='__main__':main()
