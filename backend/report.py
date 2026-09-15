"""Self-contained PDF/HTML and a reproducibility archive for an immutable run."""
from pathlib import Path
from threading import Lock
import base64, csv, hashlib, html, io, json, zipfile
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as PDFImage
from reportlab.graphics.shapes import Drawing, Polygon, Line, String, Rect
from reportlab.graphics import renderSVG
from .storage import ROOT, resource, read_json, write_json

REPORT_LOCK = Lock()
PALETTE = ['#194d6b','#347fa4','#57afb0','#b9cf87','#efc260','#de6b45','#ae383a']

def _colour(t):
    x = max(0,min(float(t),1))*(len(PALETTE)-1); i = int(x); f=x-i
    a=colors.HexColor(PALETTE[i]); b=colors.HexColor(PALETTE[min(i+1,len(PALETTE)-1)])
    return colors.Color(a.red+(b.red-a.red)*f,a.green+(b.green-a.green)*f,a.blue+(b.blue-a.blue)*f)

def stress_drawing(model,result,width=490,height=290):
    points=np.array(model['nodes']); eye=np.array([1.6,-2.2,1.6]); eye/=np.linalg.norm(eye)
    right=np.cross([0,0,1],eye);right/=np.linalg.norm(right);up=np.cross(eye,right)
    project=np.stack([right,up],axis=1)
    uv=points@project; span=np.ptp(uv,axis=0); scale=min((width-100)/span[0],(height-70)/span[1]); center=(uv.min(axis=0)+uv.max(axis=0))/2
    xy=(uv-center)*scale+[width/2,height/2+10]
    drawing=Drawing(width,height);drawing.add(Rect(0,0,width,height,fillColor=colors.HexColor('#f3f6ee'),strokeColor=None))
    triangles=[tri for face in model['faces'] for tri in face['triangles']]
    triangles.sort(key=lambda tri:float((points[tri]@eye).mean()))
    nodal=np.array(result['nodal_stress_mpa']); max_vm=result['max_display_stress_mpa']
    for tri in triangles:
        c=_colour(nodal[tri].mean()/max_vm)
        drawing.add(Polygon(xy[tri].ravel().tolist(),fillColor=c,strokeColor=c,strokeWidth=.25))
    for i,load in enumerate(result['setup']['loads']):
        f=next(f for f in model['faces'] if f['id']==load['face_id'])
        target=(np.array(f['center'])@project-center)*scale+[width/2,height/2+10]
        direction=np.array(load['vector'])@project
        if np.linalg.norm(direction)<1e-8:direction=np.array([0,-1])
        direction/=np.linalg.norm(direction); start=target-direction*40; perp=np.array([-direction[1],direction[0]])
        drawing.add(Line(*start,*target,strokeColor=colors.HexColor('#b2532a'),strokeWidth=2))
        drawing.add(Polygon(np.concatenate([target,target-direction*9+perp*4,target-direction*9-perp*4]).tolist(),fillColor=colors.HexColor('#b2532a'),strokeColor=None))
        drawing.add(String(float(start[0]+5),float(start[1]+5),f'L{i+1}',fontSize=8,fillColor=colors.HexColor('#8c4021')))
    drawing.add(String(15,height-20,'VON MISES STRESS / MPa',fontSize=8,fillColor=colors.HexColor('#536a49')))
    for i in range(70):drawing.add(Rect(width-156+i*1.8,18,1.85,7,fillColor=_colour(i/69),strokeColor=None))
    drawing.add(String(width-156,7,'0',fontSize=7,fillColor=colors.HexColor('#75856a')))
    drawing.add(String(width-28,7,f'{max_vm:.3g}',textAnchor='end',fontSize=7,fillColor=colors.HexColor('#75856a')))
    drawing.add(String(15,16,'Undeformed geometry. Nodal-averaged colors.',fontSize=7,fillColor=colors.HexColor('#7f8f74')))
    return drawing

def report_data(rid):
    result=read_json(resource('runs',rid)/'result.json')
    model=read_json(resource('models',result['model_id'])/'model.json')
    return result,model

def _rows(result,model):
    mat=result['setup']['material']
    return [
        ['Model',model['spec']['name']],['Analysis','3D small-strain static linear elasticity'],
        ['Compute device',result.get('execution',{}).get('device','Local CPU / sparse direct')],
        ['Solver method',result.get('execution',{}).get('method','Sparse direct solve')],
        ['Precision',result.get('execution',{}).get('precision','float64')],
        ['Setup proposal',result['setup'].get('setup_proposal_id') or 'Manually assigned'],
        ['Material',mat['name']],['Young modulus',f"{mat['young_mpa']:g} MPa"],['Poisson ratio',f"{mat['poisson']:g}"],
        ['Supplied yield strength',f"{mat['yield_mpa']:g} MPa"],['Density',f"{mat['density_kg_m3']:g} kg/m3"],
        ['Geometry source',model['spec']['provenance']],['CAD volume',f"{model['volume_mm3']:.5g} mm3"],
        ['Mesh volume',f"{result['mesh_volume_mm3']:.5g} mm3"],['Estimated mass',f"{result['mass_g']:.5g} g"],
        ['Mesh',f"{result['elements']:,} tetrahedra / {result['dofs']:,} {'linear' if result.get('element_order')==1 else 'quadratic'} DOFs"],
        *(_print_rows(result)),
        ['Nominal mesh size',f"{model['spec']['mesh_size']:g} mm"],['Minimum element quality',f"{model['min_quality']:.5g} (minSICN)"],
        ['Fixed faces',', '.join(str(f) for f in result['setup']['fixed_faces'])+' (XYZ translations = 0)'],
    ]

def _print_rows(result):
    info = result.get('print') or {}
    if not info.get('enabled'):
        return []
    settings = info.get('settings') or {}
    return [
        ['Print model','Homogenized FDM equivalent solid (not sliced toolpaths)'],
        ['Infill',f"{settings.get('infill_pattern')} at {100*float(settings.get('infill_density',0)):.4g}%"],
        ['Walls / skins',f"{settings.get('wall_count')} walls × {settings.get('line_width_mm')} mm; {settings.get('top_layers')}+{settings.get('bottom_layers')} skins × {settings.get('layer_height_mm')} mm"],
        ['Print rotation',str(settings.get('rotation_deg'))+' deg (print Z = layer normal)'],
        ['Effective E in-plane / layer',f"{info.get('young_xy_mpa'):g} / {info.get('young_z_mpa'):g} MPa"],
        ['Filament volume / mass',f"{info.get('filament_volume_mm3'):.5g} mm3 / {info.get('filament_mass_g'):.5g} g"],
        ['Solid volume fraction',f"{info.get('volume_fraction'):.4g}"],
    ]

def _guidance_html(result):
    guide = result.get('guidance') or {}
    if not guide.get('trust'):
        return ''
    trust = ''.join(f'<li>{_safe(item)}</li>' for item in guide['trust'])
    caution = ''.join(f'<li>{_safe(item)}</li>' for item in guide['caution'])
    nxt = _safe(guide.get('next') or '')
    return (
        '<h2>What to trust</h2><ul>' + trust + '</ul>'
        '<h2>Do not treat as printed strength</h2><ul>' + caution + '</ul>'
        f'<p class="notice">{nxt}</p>'
    )

def _safe(text):
    return html.escape(str(text)).replace('\n','<br/>')

def _reference(result):
    iid=result['setup'].get('reference_id')
    return resource('images',iid).with_suffix('.png') if iid else None

def _html(result,model,drawing):
    svg=renderSVG.drawToString(drawing)
    metrics=[('Peak von Mises',f"{result['peak_von_mises_mpa']:.5g} MPa"),('Max displacement',f"{result['max_displacement_mm']:.5g} mm"),('Yield ratio',f"{result['yield_ratio']:.4g}"),('Force balance error',f"{result['force_balance_error_n']:.3e} N")]
    rows=_rows(result,model)
    for i,l in enumerate(result['loads']):rows.append([f'Load L{i+1}',f"Face {l['face_id']}: total {l['vector_n']} N over {l['mesh_area_mm2']:.5g} mm2"])
    rows += [['Support reaction XYZ',str(result['reaction_n'])+' N'],['Moment balance error',f"{result['moment_balance_error_nmm']:.3e} N mm"],['Free-DOF relative residual',f"{result['relative_residual']:.3e}"],['Strain energy',f"{result['strain_energy_nmm']:.5g} N mm"]]
    ref=_reference(result);reference=''
    if ref and ref.exists():
        reference='<h2>Reference evidence</h2><img class="reference" alt="Reference supplied with this analysis" src="data:image/png;base64,'+base64.b64encode(ref.read_bytes()).decode()+'"/>'
        reference+='<ol>'+''.join('<li>'+_safe(m['tool'])+': '+_safe(m['text'])+'<small>Normalized coordinates: '+_safe(m['start'])+' to '+_safe(m['end'])+'</small></li>' for m in result['setup'].get('annotations',[]))+'</ol>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenFEA report - {_safe(model['spec']['name'])}</title><style>
    body{{font:14px/1.7 Arial,sans-serif;color:#344638;background:#f1f4eb;margin:0}}main{{max-width:880px;padding:48px;margin:25px auto;background:#fff}}h1{{font-size:32px;letter-spacing:-1px;margin:10px 0}}h2{{font-size:17px;margin-top:30px}}.tag{{font-size:10px;letter-spacing:2px;color:#819574}}.sub{{color:#87977d;font-size:12px}}.metrics{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#e3ead9;border:1px solid #e3ead9;margin:22px 0}}.metrics>div{{background:#f6f9ef;padding:15px}}.metrics strong{{font-size:22px;display:block;color:#436336}}.metrics span{{font-size:11px;color:#8a9f78}}svg{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:12px}}td{{padding:9px 10px;border-bottom:1px solid #e6ecdf;vertical-align:top}}td:first-child{{width:32%;color:#839775}}li{{margin:8px 0}}small{{display:block;font-size:10px;color:#91a380}}.hash{{word-break:break-all;font:10px/1.8 monospace;background:#f4f7ef;padding:12px}}.reference{{max-width:100%;max-height:480px;object-fit:contain}}.notice{{background:#f5f7ef;border-left:3px solid #90a66f;padding:14px 18px;font-size:12px}}@media print{{body{{background:white}}main{{margin:0;padding:10mm}}h2{{break-after:avoid}}tr,.metrics{{break-inside:avoid}}}}
    </style></head><body><main><div class="tag">OpenFEA / STRUCTURAL ANALYSIS</div><h1>{_safe(model['spec']['name'])}</h1><p class="sub">Run {result['id']}<br/>{result['created_at']} / mm, N, MPa</p><div class="metrics">{''.join('<div><span>'+_safe(k)+'</span><strong>'+_safe(v)+'</strong></div>' for k,v in metrics)}</div>{svg}<p class="notice">This is a linear-elastic engineering estimate. Peak stress is unaveraged; the image uses smoothed nodal colors. A single mesh does not establish convergence or physical acceptance.</p>{_guidance_html(result)}<h2>Model and simulation definition</h2><table>{''.join('<tr><td>'+_safe(k)+'</td><td>'+_safe(v)+'</td></tr>' for k,v in rows)}</table><h2>Application notes</h2><p>{_safe(result['setup']['notes']) or 'No application notes supplied.'}</p><h2>Assumptions and interpretation</h2><ul>{''.join('<li>'+_safe(w)+'</li>' for w in result['warnings'])}</ul>{reference}<h2>Reproducibility</h2><p>CAD revision: {model['id']}. Solver versions: {_safe(result['versions'])}. Runtime: {result['seconds']:.3g} seconds. No mesh-convergence study was performed for this run.</p><div class="hash">CAD SHA-256: {model['sha256']}<br/>Mesh SHA-256: {model['mesh_sha256']}</div><p>The archive contains the original mesh, CAD, complete inputs and results, quadratic solution arrays, nodal CSV, solver source, and dependency lock file. Material values are user inputs, not certified data.</p></main></body></html>'''

def _pdf(path,result,model,drawing):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('Eyebrow',fontName='Helvetica',fontSize=8,leading=13,textColor=colors.HexColor('#85996f'),spaceAfter=14))
    styles['Title'].fontName='Helvetica';styles['Title'].fontSize=27;styles['Title'].leading=32;styles['Title'].alignment=0;styles['Title'].textColor=colors.HexColor('#36572e')
    styles['Heading2'].fontSize=14;styles['Heading2'].leading=19;styles['Heading2'].textColor=colors.HexColor('#4c6b3a');styles['Heading2'].spaceBefore=15
    styles['BodyText'].fontSize=9;styles['BodyText'].leading=14;styles['BodyText'].textColor=colors.HexColor('#607250');styles['BodyText'].spaceAfter=8
    styles.add(ParagraphStyle('Tiny',parent=styles['BodyText'],fontSize=7,leading=10,wordWrap='CJK'))
    P=lambda s,style='BodyText':Paragraph(_safe(s),styles[style])
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=40,bottomMargin=40,title='OpenFEA: '+model['spec']['name'],author='OpenFEA local solver')
    story=[P('OpenFEA / STRUCTURAL ANALYSIS','Eyebrow'),P(model['spec']['name'],'Title'),P(f"Run {result['id']} | {result['created_at']}",'Tiny'),Spacer(1,10)]
    metrics=[['PEAK VON MISES','MAX DISPLACEMENT','YIELD RATIO'],[f"{result['peak_von_mises_mpa']:.4g} MPa",f"{result['max_displacement_mm']:.4g} mm",f"{result['yield_ratio']:.4g}"]]
    table=Table(metrics,colWidths=[170,170,169]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f5e7')),('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor('#567240')),('FONTSIZE',(0,0),(-1,0),7),('FONTSIZE',(0,1),(-1,1),20),('TOPPADDING',(0,0),(-1,0),12),('BOTTOMPADDING',(0,1),(-1,1),15),('LEFTPADDING',(0,0),(-1,-1),12)]));story += [table,Spacer(1,14),drawing,Spacer(1,12),P('Interpretation','Heading2'),P('This is a linear-elastic engineering estimate. Peak stress is the maximum unaveraged quadrature-point von Mises stress. The diagram uses volume-weighted nodal averages on undeformed geometry.')]
    guide = result.get('guidance') or {}
    if guide.get('trust'):
        story.append(P('What to trust','Heading2'))
        for item in guide['trust']:
            story.append(P('- '+item))
        story.append(P('Do not treat as printed strength','Heading2'))
        for item in guide['caution']:
            story.append(P('- '+item))
        if guide.get('next'):
            story.append(P(guide['next']))
    story += [P('A single mesh does not establish convergence or physical acceptance. Yield ratio uses the supplied material strength and is not a safety certification.'),P(f"Force equilibrium error: {result['force_balance_error_n']:.3e} N. Free-DOF relative residual: {result['relative_residual']:.3e}."),PageBreak(),P('Simulation definition','Title')]
    rows=[[P(k,'Tiny'),P(v,'Tiny')] for k,v in _rows(result,model)]
    tab=Table(rows,colWidths=[160,349],hAlign='LEFT');tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#e4ebd9')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),3)]));story.append(tab)
    story.append(P('Boundary conditions and verification','Heading2'))
    for i,l in enumerate(result['loads']):story.append(P(f"L{i+1}: face {l['face_id']}, total XYZ force {l['vector_n']} N, distributed uniformly over {l['mesh_area_mm2']:.5g} mm2."))
    story += [P(f"Support reaction XYZ: {result['reaction_n']} N. Moment equilibrium error: {result['moment_balance_error_nmm']:.3e} N mm."),P(f"Strain energy: {result['strain_energy_nmm']:.5g} N mm."),P('Application notes','Heading2'),P(result['setup']['notes'] or 'No application notes supplied.'),PageBreak(),P('Assumptions and provenance','Title')]
    for w in result['warnings']:story.append(P('- '+w))
    story += [P('Reproducibility','Heading2'),P(f"CAD revision: {model['id']}. Solver versions: {result['versions']}. Runtime: {result['seconds']:.3g} s. No mesh-convergence study was performed for this run."),P('CAD SHA-256: '+model['sha256'],'Tiny'),P('Mesh SHA-256: '+model['mesh_sha256'],'Tiny'),P('The exported package includes the CAD, mesh, inputs, results, quadratic solution arrays, nodal CSV, solver source and pinned dependencies. Material values are supplied inputs, not certified data.')]
    ref=_reference(result)
    if ref and ref.exists():
        from PIL import Image
        with Image.open(ref) as im:w,h=im.size
        scale=min(490/w,330/h)
        story += [PageBreak(),P('Reference evidence','Title'),PDFImage(str(ref),width=w*scale,height=h*scale),Spacer(1,10)]
        for i,m in enumerate(result['setup'].get('annotations',[])):
            story.append(P(f"Annotation {i+1} ({m['tool']}): {m['text'] or '(no text)'}"))
            story.append(P(f"Normalized image coordinates: {m['start']} to {m['end']}",'Tiny'))
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#dfe7d4'));canvas.line(43,29,A4[0]-43,29);canvas.setFont('Helvetica',7);canvas.setFillColor(colors.HexColor('#8c9e7a'));canvas.drawString(43,18,'OpenFEA | Linear-elastic estimate | mm / N / MPa');canvas.drawRightString(A4[0]-43,18,f'{doc.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def export_report(rid,format):
    with REPORT_LOCK:
        result,model=report_data(rid);folder=resource('runs',rid)
        if format=='json':return folder/'result.json'
        drawing=stress_drawing(model,result)
        html_path=folder/'report.html';html_path.write_text(_html(result,model,drawing))
        if format=='html':return html_path
        pdf_path=folder/'report.pdf';_pdf(pdf_path,result,model,drawing)
        if format=='pdf':return pdf_path
        csv_path=folder/'nodes.csv'
        with csv_path.open('w') as f:
            writer=csv.writer(f);writer.writerow(['node','x_mm','y_mm','z_mm','ux_mm','uy_mm','uz_mm','averaged_von_mises_mpa'])
            for i,(xyz,u,stress) in enumerate(zip(model['nodes'],result['displacement'],result['nodal_stress_mpa'])):writer.writerow([i,*xyz,*u,stress])
        archive=folder/'report.zip';mf=resource('models',model['id']);files={}
        for name in ['model.step','model.stl','mesh.msh','mesh.npz','model.json']:files['model/'+name]=mf/name
        for name in ['report.pdf','report.html','result.json','solution.npz','nodes.csv']:files[name]=folder/name
        files['LICENSE']=ROOT/'LICENSE'
        if result['setup'].get('setup_proposal_id'):
            files['setup-proposal.json']=resource('setup_proposals',result['setup']['setup_proposal_id']).with_suffix('.json')
        write_json(folder/'interview.json',result['setup'].get('conversation',[]))
        files['interview.json']=folder/'interview.json'
        files['source/gpu.ts']=ROOT/'frontend'/'src'/'gpu.ts'
        for name in ['__init__.py','solver.py','schemas.py','storage.py','simulation_proposals.py','print_model.py','stl_io.py','guidance.py','readiness.py']:files['source/backend/'+name]=ROOT/'backend'/name
        files['source/requirements.txt']=ROOT/'requirements.txt'
        ref=_reference(result)
        if ref and ref.exists():files['reference.png']=ref
        manifest={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for name,path in files.items():z.write(path,name)
            z.writestr('manifest.json',json.dumps(manifest,indent=2))
            z.writestr('README.md',f'''# OpenFEA run {rid}

This archive is a simulation snapshot, not certification. Read report.pdf or report.html.
All lengths are mm, forces N, stresses MPa. The JSON setup is the authoritative input.
The NPZ retains all quadratic DOFs and quadrature stresses; CSV/viewport values sample mesh vertices.
Reference annotations are in result.json > setup > annotations (normalized coordinates).
The interview transcript is in interview.json; an applied Astra setup is in setup-proposal.json when present.

## Reproduce the solve

Use Python 3.12 and a virtual environment; install source/requirements.txt.
From the archive root run: python reproduce.py
This reuses the original tetrahedra, material and face definitions; it does not remesh.
Compare numeric values with the supplied result.json using floating-point tolerances.
The new run ID and runtime will differ. Source is GPL-3.0-or-later; see the OpenFEA repository.
''')
            z.writestr('reproduce.py',f'''from pathlib import Path
import os, shutil, sys, json
root=Path(__file__).resolve().parent
os.environ['FEAR_DATA_DIR']=str(root/'reproduced')
sys.path.insert(0,str(root/'source'))
from backend.schemas import Analysis
from backend.solver import solve_model
target=root/'reproduced'/'models'/'{model['id']}'
shutil.copytree(root/'model',target,dirs_exist_ok=True)
original=json.loads((root/'result.json').read_text())
if original['setup'].get('setup_proposal_id'):
    shutil.copyfile(root/'setup-proposal.json',root/'reproduced'/'setup_proposals'/(original['setup']['setup_proposal_id']+'.json'))
result=solve_model(Analysis.model_validate(original['setup']))
print(json.dumps({{k:result[k] for k in ('id','peak_von_mises_mpa','max_displacement_mm','force_balance_error_n')}},indent=2))
''')
        return archive
