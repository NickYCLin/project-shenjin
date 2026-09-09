"""Build the carved temple environment, preserving every version-one asset.

blender --background --python tools/blender/build_temple_v2.py -- --render
Optional --materials JSON maps material roles to baseColor/normal/roughness files.
All geometry is original procedural mesh; +Y is toward the distant shrine.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'art'
parser = argparse.ArgumentParser()
parser.add_argument('--render', action='store_true')
parser.add_argument('--materials', type=Path)
parser.add_argument('--samples', type=int, default=48)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
rng = random.Random(91173)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1

# One mesh/material role keeps runtime draw calls bounded even with thousands of carvings.
COLORS = {
    'stone': (.31, .245, .17), 'lightstone': (.46, .38, .27),
    'floor': (.22, .23, .20), 'darkstone': (.09, .095, .085),
    'gold': (.48, .30, .09), 'bronze': (.16, .23, .18),
    'cloth': (.27, .075, .025), 'rock': (.17, .205, .22),
    'statue': (.38, .40, .36), 'foliage': (.09, .16, .055),
}
NAMES = {
    'stone': 'Sandstone | carved sanctuary', 'lightstone': 'Light Stone | worn relief',
    'floor': 'Floor Stone | weathered paving', 'darkstone': 'Dark Stone | recessed carving',
    'gold': 'Old gold | ritual details', 'bronze': 'Bronze | patinated metal',
    'cloth': 'Cloth | weathered saffron', 'rock': 'Mountain Stone | layered slate',
    'statue': 'Light Stone | carved idol', 'foliage': 'Vegetation | cliff grasses',
}
texture_mapping = json.loads(args.materials.read_text()) if args.materials else {}
materials = {}
for key, color in COLORS.items():
    mat = bpy.data.materials.new(NAMES[key])
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Metallic'].default_value = .62 if key in ('gold', 'bronze') else 0
    bsdf.inputs['Roughness'].default_value = .57 if key in ('gold', 'bronze') else .85
    maps = texture_mapping.get(key, texture_mapping.get('rock', {}) if key == 'statue' else {})
    for role, socket in (('baseColor', 'Base Color'), ('roughness', 'Roughness'), ('metallic', 'Metallic')):
        if role not in maps:
            continue
        path = Path(maps[role])
        if not path.is_absolute(): path = ROOT / path
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(path), check_existing=True)
        if role != 'baseColor': tex.image.colorspace_settings.name = 'Non-Color'
        if role == 'baseColor' and key in ('gold', 'bronze', 'statue'):
            tint = mat.node_tree.nodes.new('ShaderNodeMixRGB')
            tint.blend_type = 'MULTIPLY'
            tint.inputs[0].default_value = 1
            tint.inputs[2].default_value = ((.64,.76,.78,1) if key == 'statue' else (*color,1))
            mat.node_tree.links.new(tex.outputs['Color'], tint.inputs[1])
            mat.node_tree.links.new(tint.outputs[0], bsdf.inputs[socket])
        else:
            mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs[socket])
    if 'normal' in maps:
        path = Path(maps['normal'])
        if not path.is_absolute(): path = ROOT / path
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(path), check_existing=True)
        tex.image.colorspace_settings.name = 'Non-Color'
        normal = mat.node_tree.nodes.new('ShaderNodeNormalMap')
        normal.inputs['Strength'].default_value = .24 if key == 'statue' else .75
        mat.node_tree.links.new(tex.outputs['Color'], normal.inputs['Color'])
        mat.node_tree.links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
    materials[key] = mat


class MeshBatch:
    def __init__(self, role):
        self.role, self.vertices, self.faces, self.smooth = role, [], [], []
    def add(self, verts, faces, smooth=False):
        offset = len(self.vertices)
        self.vertices.extend(verts)
        self.faces.extend(tuple(i + offset for i in f) for f in faces)
        self.smooth.extend([smooth] * len(faces))
    def finish(self):
        mesh = bpy.data.meshes.new('CarvedTemple_' + self.role)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        obj = bpy.data.objects.new('Temple V2 | ' + self.role, mesh)
        scene.collection.objects.link(obj)
        obj.data.materials.append(materials[self.role])
        uv = mesh.uv_layers.new(name='UVMap')
        for polygon, smooth in zip(mesh.polygons, self.smooth):
            polygon.use_smooth = smooth
            normal = polygon.normal
            axis = max(range(3), key=lambda i: abs(normal[i]))
            axes = [(1,2), (0,2), (0,1)][axis]
            scale = {'rock':.72, 'statue':.9, 'cloth':.7}.get(self.role,.32)
            for loop_index in polygon.loop_indices:
                p = mesh.vertices[mesh.loops[loop_index].vertex_index].co
                uv.data[loop_index].uv = (p[axes[0]]*scale, p[axes[1]]*scale)
        # Non-destructive source modifier supplies portable tangent vectors for
        # normal maps when either runtime format evaluates the mesh at export.
        obj.modifiers.new('Runtime tangent triangulation', 'TRIANGULATE')
        return obj


B = {key: MeshBatch(key) for key in COLORS}

def transform(verts, loc, angle=0):
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = loc
    return [(x+c*vx-s*vy, y+s*vx+c*vy, z+vz) for vx,vy,vz in verts]


def block(loc, size, role='stone', bevel=.035, angle=0):
    # Octagonal perimeter chamfers read as chipped masonry, not hard cube edges.
    x, y, z = (v/2 for v in size)
    b = min(bevel, x*.4, y*.4, z*.4)
    ring = [(-x+b,-y), (x-b,-y), (x,-y+b), (x,y-b),
            (x-b,y), (-x+b,y), (-x,y-b), (-x,-y+b)]
    verts = [(vx,vy,-z) for vx,vy in ring] + [(vx,vy,z-b) for vx,vy in ring]
    verts += [(vx*(x-b)/x,vy*(y-b)/y,z) for vx,vy in ring]
    faces = [tuple(range(7,-1,-1)), tuple(range(16,24))]
    for level in (0,8):
        for i in range(8):
            j = (i+1)%8
            faces.append((level+i,level+j,level+8+j,level+8+i))
    B[role].add(transform(verts,loc,angle), faces)


def tube(loc, radius, height, role='stone', sides=16, top=None, flutes=0):
    top = radius if top is None else top
    verts=[]
    for z,r in ((-height/2,radius),(height/2,top)):
        for i in range(sides):
            a = math.tau*i/sides
            rr = r*(1+flutes*math.cos(a*8))
            verts.append((loc[0]+rr*math.cos(a),loc[1]+rr*math.sin(a),loc[2]+z))
    faces=[tuple(range(sides-1,-1,-1)),tuple(range(sides,sides*2))]
    faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
    B[role].add(verts,faces,True)


def ellipsoid(loc, scale, role='stone', segments=24, rings=16, sculpt=None):
    verts=[]
    for j in range(rings+1):
        t=math.pi*j/rings
        for i in range(segments):
            a=math.tau*i/segments
            n=(math.sin(t)*math.cos(a), math.sin(t)*math.sin(a), math.cos(t))
            v=[loc[k]+scale[k]*n[k] for k in range(3)]
            if sculpt: v = sculpt(v,n)
            verts.append(v)
    faces=[]
    for j in range(rings):
        for i in range(segments):
            a=j*segments+i; b=j*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    B[role].add(verts,faces,True)


def arc(loc, radius, thickness, depth, start=0, end=math.pi, role='lightstone', steps=24):
    verts=[]
    for i in range(steps+1):
        a=start+(end-start)*i/steps
        for r,y in ((radius-thickness/2,-depth/2),(radius+thickness/2,-depth/2),
                    (radius-thickness/2,depth/2),(radius+thickness/2,depth/2)):
            verts.append((loc[0]+r*math.cos(a),loc[1]+y,loc[2]+r*math.sin(a)))
    faces=[(0,2,3,1)]
    for i in range(steps):
        a=i*4; n=a+4
        faces += [(a,n,n+1,a+1),(a+2,a+3,n+3,n+2),(a,a+2,n+2,n),(a+1,n+1,n+3,a+3)]
    n=steps*4; faces.append((n,n+1,n+3,n+2))
    B[role].add(verts,faces)


def relief_flower(x,y,z,r=.28,role='lightstone'):
    ellipsoid((x,y,z),(r*.32,.055,r*.32),role,12,6)
    for k in range(8):
        a=k*math.tau/8
        ellipsoid((x+r*.62*math.cos(a),y,z+r*.62*math.sin(a)),
                  (r*.26,.065,r*.26),role,8,4)


def column(x,y,z=0,h=8.2,r=.46):
    for dz,w,t in ((.12,2.0,.24),(.36,1.72,.24),(.62,1.45,.28)):
        block((x,y,z+dz),(r*w*1.5,r*w*1.5,t),'lightstone',.025)
    tube((x,y,z+h*.48),r,h-.95,'stone',32,top=r*.9,flutes=.06)
    for dz,rr,hh in ((1.0,1.2,.18),(1.25,1.1,.12),(h*.36,1.13,.16),
                     (h*.39,1.06,.10),(h*.72,1.1,.16),(h-.65,1.3,.3)):
        tube((x,y,z+dz),r*rr,hh,'lightstone',24)
    for i in range(12):
        a=math.tau*i/12
        ellipsoid((x+math.cos(a)*r*.9,y+math.sin(a)*r*.9,z+h-.38),
                  (.16,.16,.32),'lightstone',10,6)
    block((x,y,z+h-.08),(r*2.8,r*2.8,.3),'lightstone',.05)
    # Repeated shallow floral carving remains physical geometry in exported models.
    for dz in (1.75,2.6,4.1,5.1,6.2):
        if dz<h-1: relief_flower(x,y-r-.025,z+dz,r*.58)


def cornice(cx,cy,z,w,d):
    for dz,grow,t,role in ((0,0,.22,'stone'),(.22,.35,.18,'lightstone'),
                           (.39,.60,.16,'stone'),(.55,.72,.13,'lightstone')):
        block((cx,cy,z+dz),(w+grow,d+grow,t),role,.025)
    for i in range(max(2,int(w/.45))):
        xx=cx-w/2+(i+.5)*w/max(2,int(w/.45))
        block((xx,cy-d/2-.18,z-.19),(.18,.3,.32),'lightstone',.025)


def niche(x,y,z,w=1,h=1.7):
    block((x,y,z+h*.36),(w,.065,h*.73),'darkstone',.015)
    for s in (-1,1):
        block((x+s*w*.6,y-.1,z+h*.4),(.12,.19,h*.8),'lightstone',.018)
    arc((x,y-.13,z+h*.76),w*.55,.16,.19,0,math.pi,steps=12)
    # Small stone deity silhouette nested in an actual recessed framed opening.
    ellipsoid((x,y-.15,z+h*.57),(w*.16,.11,h*.13),'stone',12,8)
    ellipsoid((x,y-.15,z+h*.26),(w*.24,.1,h*.22),'lightstone',12,8)
    block((x,y-.17,z+.04),(w*.72,.3,.13),'lightstone',.015)


# Mortared paving: top surfaces vary by millimetres, with no coplanar overlays.
# Continuous lower terrain supports every structure and closes the ravine gaps.
ground_verts=[]
for j in range(37):
    for i in range(39):
        ground_verts.append((-76+i*4,-32+j*4,-.52+rng.uniform(-.12,.09)))
ground_faces=[]
for j in range(36):
    for i in range(38):
        a=j*39+i; ground_faces.append((a,a+1,a+40,a+39))
B['rock'].add(ground_verts,ground_faces)
block((0,0,-.38),(38,39,.65),'darkstone',.09)
for row in range(-19,20):
    y=row*1.035
    for col in range(-19,20):
        x=col*1.035 + (.5175 if row%2 else 0)
        if math.hypot(x,y)>19.0: continue
        top=rng.uniform(-.014,.004)
        role='lightstone' if abs(x)<2.8 and row%5==0 else 'floor'
        block((x,y,top-.10),(.998+rng.uniform(-.014,.014),1.005,.2),role,.025+rng.random()*.013)
# True inset mosaic tiles share the same surface height; no floating luminous circles.
for i in range(96):
    a=math.tau*i/96
    r=17.6
    block((math.cos(a)*r,math.sin(a)*r,.012),(.12,.44,.022),'bronze',.005,angle=a)
for i in range(9):
    block((0,-20.2-i*1.06,-.1),(7.4,1.025,.2),'floor',.035)
# Substantial carved retaining wall faces the camera below the arena's edge.
for side in (-1,1):
    for y in range(-14,20,2):
        block((side*19.4,y,-.8),(.7,1.94,1.2),'stone',.06)

# Galleries contain rounded arches, deep capitals, carved column bands and dentils.
for side in (-1,1):
    x=side*21.1
    block((x,7,-.1),(5.2,32,.6),'stone',.07)
    for y in (-6,-.5,5,10.5,16,21.5):
        column(x,y,.2,8.1,.56)
    cornice(x,7.7,8.4,3.7,31)
    for y in (-3.25,2.25,7.75,13.25,18.75):
        # Arc geometry lies in XZ; rotate into YZ for side gallery bays.
        before={k:len(v.vertices) for k,v in B.items()}
        arc((0,0,6.15),2.55,.34,.72,0,math.pi,steps=18)
        for key,batch in B.items():
            for idx in range(before[key],len(batch.vertices)):
                vx,vy,vz=batch.vertices[idx]
                batch.vertices[idx]=(x+vy,y+vx,vz)
    for y in (-6,5,16):
        # Small sculpted corner finials, with no floating crystals.
        tube((x,y,9.3),.52,.35,'lightstone',20,top=.26)
        ellipsoid((x,y,9.67),(.3,.3,.37),'stone',16,10)

# Four sculpted storeys, rather than unadorned stair pyramids.
for side in (-1,1):
    tx,ty=side*18.2,31.2
    for tier in range(4):
        w=12.0-tier*1.85; d=10.5-tier*1.4; z=.5+tier*4.0
        block((tx,ty,z+1.7),(w,d,3.4),'stone',.06)
        cornice(tx,ty,z+3.34,w,d)
        n=max(3,int(w/1.9))
        for j in range(n):
            xx=tx-w/2+(j+.5)*w/n
            niche(xx,ty-d/2-.08,z+.55, min(1.05,w/n*.65),1.95)
            relief_flower(xx,ty-d/2-.14,z+2.94,.23)
        # The two side walls use actual relief panels and staggered pilasters.
        for s in (-1,1):
            for j in range(max(2,int(d/2))):
                yy=ty-d/2+(j+.5)*d/max(2,int(d/2))
                block((tx+s*(w/2+.05),yy,z+1.65),(.18,.27,2.7),'lightstone',.02)
        for j in range(int(w/.8)):
            xx=tx-w/2+(j+.5)*.8
            arc((xx,ty-d/2-.15,z+3.85),.23,.09,.2,0,math.pi,steps=8)
    # Rounded ribbed amalaka and stacked pot finial are common shrine silhouettes.
    tube((tx,ty,17.15),2.25,.8,'stone',64,top=1.9,flutes=.055)
    for i in range(4):
        tube((tx,ty,17.8+i*.33),1.5-i*.23,.32,'lightstone',32,top=1.3-i*.23)
    ellipsoid((tx,ty,19.55),(.46,.46,.8),'gold',24,16)
    tube((tx,ty,20.3),.12,.6,'bronze',16,top=.03)

# A processional staircase opens into the giant idol sanctum.
for i in range(13):
    block((0,20.4+i*.66,.12+i*.25),(14,.655,.25),'lightstone',.018)
for layer in range(5):
    block((0,39.0,layer*.6+.3),(22.6-layer*.25,18.8-layer*.25,.6),
          'lightstone' if layer in (0,4) else 'stone',.055)
for x in (-8.8,-5.9,5.9,8.8):
    column(x,29.8,3.0,11.5,.62)
for x in (-7.35,7.35):
    arc((x,29.8,11.0),1.43,.35,.85,0,math.pi,steps=20)
cornice(0,31.0,14.6,21,4.8)
for i in range(29):
    x=(i-14)*.69
    relief_flower(x,28.51,14.22,.21)
# Side wings with continuous relief niches make the sanctum feel constructed.
for side in (-1,1):
    for j in range(5):
        x=side*(11.8+j*2.05)
        block((x,39,4.9),(2.02,7.8,3.8),'stone',.04)
        niche(x,35.04,3.5,1.1,2.25)
        cornice(x,39,6.9,2.02,7.8)

# The giant face is one continuous deformed surface, with sculpted anatomy.
sculpt_start={role:(len(B[role].vertices),len(B[role].faces)) for role in ('stone','lightstone')}
head_center=(0,43.5,23.4)
def gauss(x,z,cx,cz,sx,sz):
    return math.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
def face_sculpt(v,n):
    x,y,z=n
    front=max(0,-y)**3
    # Eye sockets recess; brow, bridge, nasal tip, cheekbones, lips and chin project.
    relief=0
    for s in (-1,1):
        relief-=1.18*gauss(x,z,s*.34,.08,.19,.13)
        relief+=.80*gauss(x,z,s*.34,.235,.23,.095)
        relief+=.38*gauss(x,z,s*.49,-.12,.24,.20)
        relief+=.70*gauss(x,z,s*.115,-.23,.068,.062)
        relief-=.27*gauss(x,z,s*.08,-.265,.035,.026)
    relief+=.97*gauss(x,z,0,.015,.09,.26)
    relief+=1.85*gauss(x,z,0,-.185,.13,.115)
    relief+=.62*gauss(x,z,0,-.385,.29,.034)
    relief+=.70*gauss(x,z,0,-.44,.25,.042)
    relief-=.22*gauss(x,z,0,-.414,.30,.018)
    relief+=.42*gauss(x,z,0,-.64,.31,.14)
    # Very subtle chipped surface undulation; never triangulated toy facets.
    relief+=.025*math.sin(x*57+z*33)*math.sin(z*63)
    v[1]-=relief*front
    # Narrow the lower jaw into a sculptural chin, retaining a broad forehead.
    if z<-.25: v[0]*=1-.13*((-z-.25)/.75)
    return v
ellipsoid(head_center,(6.6,4.85,8.5),'lightstone',128,96,face_sculpt)
# Neck and lower draped fragments create mass below the head.
ellipsoid((0,44.1,14.8),(3.15,3.0,4.7),'stone',48,32)
# The severed divine head rests on a carved reliquary, with a structurally
# continuous support. It is deliberately not assembled from primitive limbs.
block((0,44.1,7.65),(9.1,8.2,9.3),'stone',.12)
for z in (3.15,3.7,11.8,12.35):
    cornice(0,44.1,z,9.5,8.6)
for x in (-3.7,-1.25,1.25,3.7):
    block((x,39.92,7.85),(.24,.22,7.4),'lightstone',.03)
for x in (-2.45,0,2.45):
    for z in (4.8,6.4,8.0,9.6,11.0): relief_flower(x,39.86,z,.42)
for z in (11.7,12.15,12.6):
    tube((0,44.1,z),3.26,.21,'lightstone',64)
for side in (-1,1):
    ellipsoid((side*6.28,43.25,22.8),(1.14,1.16,2.45),'lightstone',40,28)
    ellipsoid((side*6.4,42.28,22.85),(.55,.18,1.53),'stone',24,20)
    # Closed stone eyelids sit inside the sculpted sockets, avoiding glowing eyes.
    lid_start=len(B['stone'].vertices)
    arc((side*2.27,39.48,24.04),.99,.12,.20,.08,math.pi-.08,role='stone',steps=24)
    arc((side*2.27,39.55,24.04),.99,.09,.16,math.pi+.08,math.tau-.08,role='stone',steps=24)
    for idx in range(lid_start,len(B['stone'].vertices)):
        vx,vy,vz=B['stone'].vertices[idx]
        B['stone'].vertices[idx]=(vx,vy,24.04+(vz-24.04)*.24)
    # Ancient metal earrings are modest loops, separate from the halo.
    arc((side*6.42,42.82,20.8),.67,.13,.2,0,math.tau,role='bronze',steps=24)
# Crown is carved stone and tarnished metal, built in a layered scalloped silhouette.
for z,r,h in ((30.5,5.92,.55),(31.05,6.08,.35),(31.51,5.6,.55),(32.1,5.35,.35)):
    tube((0,43.5,z),r,h,'stone' if z<31.1 else 'lightstone',64,top=r*.98)
for i in range(20):
    a=math.tau*i/20
    x,y=5.48*math.cos(a),43.5+5.48*math.sin(a)
    ellipsoid((x,y,32.4),(.58,.55,.93),'lightstone',16,12)
    if i%2==0: ellipsoid((x*.92,43.5+(y-43.5)*.92,33.15),(.20,.20,.37),'gold',12,8)
for i in range(4):
    tube((0,43.5,32.6+i*.66),4.75-i*.82,.66,'stone',64,top=4.2-i*.82,flutes=.025)
ellipsoid((0,43.5,35.58),(1.4,1.4,1.12),'lightstone',32,20)
# Disconnected, weathered halo segments: gaps, offsets and visible thickness.
for start,end,shift in ((.10,.73,.0),(.84,1.30,.25),(1.41,1.94,-.1),(2.10,2.65,.13),(2.79,3.10,.0),(3.6,4.02,-.1),(5.03,5.41,.15),(5.52,6.12,-.05)):
    arc((shift,47.0,23.4),11.45,.42,.72,start,end,'stone',max(10,int((end-start)*30)))
    arc((shift,46.6,23.4),11.4,.10,.08,start,end,'bronze',max(10,int((end-start)*30)))
    mid=(start+end)/2
    for a in (start+.10,mid,end-.10):
        rr=12.05
        ellipsoid((shift+rr*math.cos(a),47.0,23.4+rr*math.sin(a)),(.28,.4,.58),'stone',16,10)

# Sculptural stone uses fine, cool mottling, not the architectural brick texture.
for role,(vert_start,face_start) in sculpt_start.items():
    batch=B[role]
    B['statue'].add(batch.vertices[vert_start:],
        [tuple(index-vert_start for index in face) for face in batch.faces[face_start:]])
    B['statue'].smooth[-(len(batch.faces)-face_start):]=batch.smooth[face_start:]
    del batch.vertices[vert_start:]; del batch.faces[face_start:]; del batch.smooth[face_start:]

# Stratified cliff masses have many irregular ledges, not pyramidal mountain cones.
def cliff(cx,cy,width,depth,height,seed):
    rr=random.Random(seed)
    sides,levels=50,26
    angles=[math.tau*i/sides for i in range(sides)]
    outline=[1+.10*math.sin(a*3+seed)+.065*math.cos(a*7+seed*.3)
             +.035*math.sin(a*13+seed*.6) for a in angles]
    verts=[]
    for j in range(levels+1):
        t=j/levels
        # A broad irregular plateau with a broken cap retains vertical cliff faces.
        taper=1-.13*t-.23*max(0,(t-.81)/.19)
        ledge=(.045 if j%3==0 else -.025)
        for i,a in enumerate(angles):
            radial=(outline[i]+ledge+.055*math.sin(j*1.9+i*.6)+rr.uniform(-.027,.027))*taper
            zz=t*height + (.8*math.sin(i*1.7)+.4*math.cos(i*2.9))*t
            xx=cx+width*.5*radial*math.cos(a)+.8*math.sin(t*5)
            yy=cy+depth*.5*radial*math.sin(a)
            verts.append((xx,yy,zz-2.2))
    faces=[]
    for j in range(levels):
        for i in range(sides):
            a=j*sides+i; b=j*sides+(i+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.append(tuple(range(levels*sides,(levels+1)*sides)))
    face_start=len(B['rock'].faces)
    B['rock'].add(verts,faces,True)
    for index in range(levels*sides):
        if (index//sides)%5==0: B['rock'].smooth[face_start+index]=False
for side in (-1,1):
    for i in range(8):
        cliff(side*(27+i*3.7),34+i*6.4,13+rng.random()*9,14+rng.random()*8,
              18+rng.random()*22+i*1.6,320+i+int(side*10))
for i in range(9):
    cliff((i-4)*12,85+abs(i-4)*2,19,20,35+rng.random()*16,450+i)
# Fractured rubble stays outside the entire traversable radius.
for i in range(110):
    a=rng.uniform(-.15,math.pi+.15)
    r=rng.uniform(20.0,25)
    x,y=math.cos(a)*r,math.sin(a)*r
    if y>19 and abs(x)<8: continue
    block((x,y,rng.uniform(.07,.3)),(rng.uniform(.2,.9),rng.uniform(.3,.9),rng.uniform(.15,.55)),
          'stone',.065,angle=rng.random()*math.tau)
# Sparse cliff grass grows only outside the combat space and around masonry feet.
for patch in range(145):
    side=rng.choice((-1,1)); x=side*rng.uniform(19.2,25); y=rng.uniform(-10,43)
    for blade in range(9):
        bx=x+rng.uniform(-.24,.24); by=y+rng.uniform(-.24,.24)
        h=rng.uniform(.16,.48); lean=rng.uniform(-.17,.17); w=rng.uniform(.018,.04)
        B['foliage'].add([(bx-w,by,0),(bx+w,by,0),(bx+lean+w*.4,by+.03,h*.62),
                         (bx+lean,by+.07,h),(bx+lean-w*.4,by+.03,h*.62)],[(0,1,2,3,4)])
# Tattered cloth is a restrained accent, distinct from architectural material color.
for side in (-1,1):
    x,y,z=side*20.5,19.5,7.8
    verts=[]
    for j in range(17):
        for i in range(7):
            u,t=i/6,j/16
            verts.append((x+(u-.5)*1.25,y+.16*math.sin(u*6+t*5)*t,z-t*4.1+.12*math.sin(u*13)*t**8))
    faces=[]
    for j in range(16):
        for i in range(6):
            a=j*7+i; faces.append((a,a+1,a+8,a+7))
    B['cloth'].add(verts,faces,True)

objects=[batch.finish() for batch in B.values() if batch.vertices]
for obj in objects:
    obj['asset_version']='temple-v2'
    obj['authoring_units']='meters'
    obj['clear_arena_radius']=16.5
triangles=0
for obj in objects:
    obj.data.calc_loop_triangles()
    triangles+=len(obj.data.loop_triangles)
assert triangles<=600000, triangles
assert len(objects)<25,len(objects)
# All source images are packed for the editable .blend. GLB also embeds its maps.
for image in bpy.data.images:
    if image.source=='FILE':
        image.pack()
        # Blender otherwise copies the original high-quality JPEG verbatim and
        # ignores the runtime export quality. Mark pixels dirty without changing
        # them so the glTF writer re-encodes at 82, retaining the full 2K size.
        image.pixels[0] = image.pixels[0]
for sub in ('source','exports','renders'): (ART/sub).mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects: obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
glb=ART/'exports'/'temple-v2.glb'
fbx=ART/'exports'/'temple-v2.fbx'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
                          export_apply=True,export_yup=True,export_animations=False,
                          export_cameras=False,export_lights=False,export_extras=True,
                          export_tangents=True,
                          export_image_format='JPEG',export_jpeg_quality=82,
                          export_image_quality=82)
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
                         apply_unit_scale=True,axis_forward='-Z',axis_up='Y',
                         bake_anim=False,path_mode='COPY',embed_textures=True)
assert glb.stat().st_size<40*1024*1024,glb.stat().st_size

# Camera-only collision boxes use glTF Y-up coordinates: (x, z, -y).
# Pillars and solid cornices are separate boxes, leaving the arched bays open.
collision=[]
def collider(loc,size):
    x,y,z=loc; w,d,h=size
    collision.append({'min':[x-w/2,z-h/2,-y-d/2],
                      'max':[x+w/2,z+h/2,-y+d/2]})
for side in (-1,1):
    for y in (-6,-.5,5,10.5,16,21.5): collider((side*21.1,y,4.4),(1.8,1.8,8.8))
    collider((side*21.1,7.7,8.7),(4.4,31.7,.9))
    for tier in range(4):
        collider((side*18.2,31.2,2.2+tier*4),(12-tier*1.85,10.5-tier*1.4,3.8))
    for j in range(5): collider((side*(11.8+j*2.05),39,5.0),(2.02,7.8,4.1))
for x in (-8.8,-5.9,5.9,8.8): collider((x,29.8,8.75),(1.8,1.8,11.5))
collider((0,31,14.9),(21.7,5.5,.9))
(ART/'exports'/'temple-v2-colliders.json').write_text(json.dumps({'boxes':collision},indent=2)+'\n')

# Rendering setup is intentionally absent from either environment export.
world=bpy.data.worlds.new('Cool high-altitude atmosphere')
scene.world=world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.36,.49,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5
sun_data=bpy.data.lights.new('Late sun from courtyard left','SUN')
sun_data.energy=2.7; sun_data.color=(1,.89,.73); sun_data.angle=.13
sun=bpy.data.objects.new('Late sun from courtyard left',sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler=(math.radians(57),math.radians(-26),math.radians(-32))
fill_data=bpy.data.lights.new('Large sky opening','AREA')
fill_data.energy=8500; fill_data.color=(.47,.67,1); fill_data.shape='DISK'; fill_data.size=40
fill=bpy.data.objects.new('Large sky opening',fill_data)
scene.collection.objects.link(fill)
fill.location=(8,-6,24)
fill.rotation_euler=(Vector((0,23,7))-fill.location).to_track_quat('-Z','Y').to_euler()
# A genuine render-only atmospheric volume softens distant cliffs while keeping
# the traversable courtyard sharp. It is never exported as game geometry.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,71,29))
haze=bpy.context.object
haze.name='Render only | distant mountain haze'
haze.scale=(180,94,66)
haze_mat=bpy.data.materials.new('Render only | cool aerial perspective')
haze_mat.use_nodes=True
haze_nodes=haze_mat.node_tree.nodes
haze_nodes.clear()
haze_output=haze_nodes.new('ShaderNodeOutputMaterial')
haze_scatter=haze_nodes.new('ShaderNodeVolumeScatter')
haze_scatter.inputs['Color'].default_value=(.56,.67,.76,1)
haze_scatter.inputs['Density'].default_value=.004
haze_scatter.inputs['Anisotropy'].default_value=.12
haze_mat.node_tree.links.new(haze_scatter.outputs[0],haze_output.inputs['Volume'])
haze.data.materials.append(haze_mat)
cam_data=bpy.data.cameras.new('Courtyard architecture view')
cam=bpy.data.objects.new('Courtyard architecture view',cam_data)
scene.collection.objects.link(cam)
cam.location=(0,-20,3.6)
cam.rotation_euler=(Vector((0,18,8.5))-cam.location).to_track_quat('-Z','Y').to_euler()
cam_data.lens=23
scene.camera=cam
scene.render.engine='BLENDER_EEVEE'
scene.eevee.taa_render_samples=max(64,args.samples)
scene.eevee.use_gtao=True
scene.eevee.gtao_distance=3
scene.eevee.gtao_factor=1.25
scene.eevee.use_soft_shadows=True
scene.eevee.shadow_cube_size='4096'
scene.eevee.shadow_cascade_size='4096'
scene.render.resolution_x=1920
scene.render.resolution_y=1080
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath='//../renders/temple-v2.png'
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.film_transparent=False
for image in bpy.data.images:
    if image.source=='FILE' and image.filepath:
        image.filepath='//'+os.path.relpath(
            bpy.path.abspath(image.filepath), ART/'source').replace(os.sep,'/')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'source'/'lost-temple-v2.blend'),compress=True)
print('TEMPLE_V2_BUILD '+json.dumps({'triangles':triangles,'meshes':len(objects),'glb_bytes':glb.stat().st_size,'materials':list(materials),'textures':bool(texture_mapping)}))
if args.render: bpy.ops.render.render(write_still=True)

# Reimport both deliveries into a disposable scene and verify their contract.
source_bounds=[]
for obj in objects:
    source_bounds.extend(obj.matrix_world@vertex.co for vertex in obj.data.vertices)
expected_lo=[min(v[i] for v in source_bounds) for i in range(3)]
expected_hi=[max(v[i] for v in source_bounds) for i in range(3)]
for path in (glb,fbx):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    if path.suffix=='.glb': bpy.ops.import_scene.gltf(filepath=str(path))
    else: bpy.ops.import_scene.fbx(filepath=str(path))
    meshes=[obj for obj in scene.objects if obj.type=='MESH']
    points=[obj.matrix_world@vertex.co for obj in meshes for vertex in obj.data.vertices]
    lo=[min(v[i] for v in points) for i in range(3)]
    hi=[max(v[i] for v in points) for i in range(3)]
    assert max(abs(lo[i]-expected_lo[i]) for i in range(3))<.005,(path,lo,expected_lo)
    assert max(abs(hi[i]-expected_hi[i]) for i in range(3))<.005,(path,hi,expected_hi)
    assert len(meshes)<25
    assert not [obj for obj in scene.objects if obj.type in ('CAMERA','LIGHT')]
    assert all(obj.data.uv_layers for obj in meshes)
    print('TEMPLE_V2_VERIFIED '+json.dumps({'file':path.name,'meshes':len(meshes),'bounds_min':lo,'bounds_max':hi,'bytes':path.stat().st_size}))
