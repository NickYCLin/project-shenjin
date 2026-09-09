"""Rebuild the original Shenjin art set with Blender 4.0+; no external assets.

blender --background --python tools/blender/build_assets.py -- --render
All dimensions are meters. Source characters face -Y, glTF characters face +Z.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import struct
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'art'
random.seed(73)
parser = argparse.ArgumentParser()
parser.add_argument('--render', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    if collection.name != 'Collection':
        bpy.data.collections.remove(collection)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.context.preferences.filepaths.save_version = 0


def material(name, color, metallic=0, roughness=.6, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    if emission:
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = emission
    return mat


M = {
    'stone': material('Sandstone | warm ash', (.31,.25,.19), 0,.84),
    'lightstone': material('Sandstone | sun worn edge', (.52,.41,.28),0,.76),
    'darkstone': material('Obsidian | blue black', (.036,.064,.067),.25,.47),
    'floor': material('Arena | basalt teal', (.079,.13,.13),.15,.75),
    'gold': material('Bronze | polished gold', (.64,.36,.10),.76,.29),
    'bronze': material('Bronze | ancient patina', (.17,.27,.23),.65,.48),
    'teal': material('Enamel | peacock teal', (.009,.19,.20),.50,.27),
    'cloth': material('Cloth | saffron orange', (.65,.13,.035),0,.72),
    'leather': material('Leather | midnight', (.021,.033,.038),0,.8),
    'skin': material('Stone flesh | ivory', (.51,.48,.35),.2,.56),
    'ember': material('Divine fire | amber', (1,.35,.04),.2,.24,3.4),
    'aqua': material('Divine fire | turquoise', (.035,.70,.61),.1,.22,2.4),
    'mountain': material('Distant rock | slate blue', (.053,.095,.105),0,.95),
}
collections = {}
roots = {}


def asset(name):
    col = bpy.data.collections.new(name.upper())
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new(name + '_root', None)
    col.objects.link(root)
    root['units'] = 'meters'
    root['source_forward'] = '-Y'
    root['gltf_forward'] = '+Z'
    collections[name] = col
    roots[name] = root
    return name


def finish(obj, name, mat, group, bevel=0, smooth=False):
    obj.name = name
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collections[group].objects.link(obj)
    obj.parent = roots[group]
    obj.data.materials.append(M[mat])
    if bevel:
        mod = obj.modifiers.new('Hand softened edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def cube(name, loc, scale, mat, group, bevel=.03, rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotation:
        obj.rotation_euler = rotation
    return finish(obj,name,mat,group,bevel)


def cylinder(name, loc, radius, depth, mat, group, vertices=12, top=None, rotation=None):
    if top is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=vertices,radius1=radius,radius2=top,depth=depth,location=loc)
    obj=bpy.context.object
    if rotation:
        obj.rotation_euler=rotation
    return finish(obj,name,mat,group,.025 if radius > .25 else .008)


def sphere(name, loc, scale, mat, group, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=loc)
    obj=bpy.context.object
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(obj,name,mat,group,0,True)


def ico(name, loc, scale, mat, group, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions,radius=1,location=loc)
    obj=bpy.context.object
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(obj,name,mat,group)


def rod(name, a, b, radius, mat, group, top=None, vertices=10):
    a,b=Vector(a),Vector(b)
    obj=cylinder(name,(a+b)/2,radius,(b-a).length,mat,group,vertices,top)
    obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return obj


def ring(name, loc, radius, minor, mat, group, rotation=None, segments=64):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius,minor_radius=minor,major_segments=segments,minor_segments=6,location=loc)
    obj=bpy.context.object
    if rotation:
        obj.rotation_euler=rotation
    return finish(obj,name,mat,group,0,True)


def mesh(name, verts, faces, mat, group):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    obj=bpy.data.objects.new(name,data)
    collections[group].objects.link(obj)
    obj.parent=roots[group]
    obj.data.materials.append(M[mat])
    return obj


def diamond(name, center, width, length, thickness, mat, group):
    x,y,z=center
    verts=[(x,y,z+length/2),(x+width/2,y,z),(x,y,z-length/2),(x-width/2,y,z),(x,y-thickness/2,z),(x,y+thickness/2,z)]
    return mesh(name,verts,[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)],mat,group)


def banner(name, x,y,z,width,height,group):
    # Static original wind silhouette: no simulation or image texture dependency.
    verts=[]
    nx,nz=8,8
    for j in range(nz+1):
        t=j/nz
        for i in range(nx+1):
            u=i/nx
            verts.append((x+(u-.5)*width, y+math.sin(u*5+t*2)*.23*t, z-t*height+(abs(u-.5)*.3 if j==nz else 0)))
    faces=[]
    for j in range(nz):
        for i in range(nx):
            a=j*(nx+1)+i
            faces.append((a,a+1,a+nx+2,a+nx+1))
    obj=mesh(name,verts,faces,'cloth',group)
    mod=obj.modifiers.new('Woven cloth thickness','SOLIDIFY')
    mod.thickness=.018
    rod(name+' gilt crossbar',(x-width*.6,y,z+.03),(x+width*.6,y,z+.03),.055,'gold',group)
    diamond(name+' oath emblem',(x,y-.06,z-height*.38),width*.33,height*.26,.045,'gold',group)


def brazier(x,y,z,group,scale=1):
    cylinder('Brazier plinth',(x,y,z+.25*scale),.44*scale,.5*scale,'darkstone',group,8)
    cylinder('Bronze fire bowl',(x,y,z+.66*scale),.55*scale,.34*scale,'gold',group,8,top=.77*scale)
    for i in range(5):
        a=i*2.4
        ico('Captured divine ember',(x+math.sin(a)*.17*scale,y+math.cos(a)*.17*scale,z+(1+i*.06)*scale),(.13*scale,.12*scale,(.48-i*.045)*scale),'ember',group,1)


g=asset('temple')
# Flat, unobstructed combat arena. The top surface is exactly z=0.
cylinder('Arena foundation',(0,0,-.90),19.5,1.3,'darkstone',g,96)
cylinder('Arena upper stone',(0,0,-.22),18.5,.44,'floor',g,96)
for radius in (18.15,17.82,14.4):
    ring('Inlaid concentric oath circle',(0,0,.012),radius,.035,'gold',g,segments=96)
ring('Central turquoise seal',(0,0,.016),4.3,.055,'aqua',g)
ring('Central bronze seal',(0,0,.012),4.6,.08,'gold',g)
for i in range(48):
    a=i*math.tau/48
    rr=16.1
    # Shallow engraved radial markings; no raised collision in the battle area.
    obj=cube('Arena radial inlay',(math.sin(a)*rr,math.cos(a)*rr,.006),(.028,3.1,.014),'gold',g,0)
    obj.rotation_euler.z=-a
for i in range(3):
    a=i*math.tau/3
    rod('Three oath seal',(math.sin(a)*3.9,math.cos(a)*3.9,.026),(math.sin(a+math.tau/3)*3.9,math.cos(a+math.tau/3)*3.9,.026),.037,'gold',g,vertices=6)
# Broad approach and elevated causeway outside the combat radius.
cube('Pilgrim causeway',(0,-24,-.5),(8,15,1),'stone',g,.1)
for y in range(-29,-18,2):
    cube('Causeway joint',(0,y,.008),(7.8,.035,.02),'darkstone',g,0)
for x in (-4.25,4.25):
    cube('Causeway golden rim',(x,-24,.1),(.18,15,.2),'gold',g,.015)
for side in (-1,1):
    # Twin long retaining galleries hold the central scene open.
    cube('Outer gallery',(side*22,9,-.45),(6,34,1.3),'stone',g,.08)
    for y in (-4,7,18):
        x=side*21
        for z,size in ((.5,2.8),(.93,2.35),(1.25,1.85)):
            cube('Column tier',(x,y,z),(size,size,.32),'lightstone' if z==.93 else 'stone',g,.05)
        cylinder('Octagonal sanctum column',(x,y,5.5),.85,8.1,'stone',g,8,top=.67)
        for z in (1.6,3.1,7.6,9.45):
            cylinder('Column gilded collar',(x,y,z),.92,.22,'gold',g,8)
        cube('Column capital',(x,y,9.8),(2.3,2.3,.55),'lightstone',g,.07)
        cylinder('Lotus cup',(x,y,10.35),1.12,.6,'gold',g,8,top=.53)
        diamond('Column divine tip',(x,y,11.2),.58,1.25,.35,'aqua',g)
        if y != 7:
            banner('Saffron oath standard',x,y-.97,8.7,1.3,4.9,g)
    cube('Gallery lintel',(side*21,7,9.35),(1.5,25,.6),'stone',g,.08)
    cube('Gallery gilt cornice',(side*21,7,9.7),(1.8,25,.18),'gold',g,.025)
    for y in (-12,12):
        brazier(side*15.6,y,0,g,1.35)
    # Two offset ziggurats frame the distant god head.
    tx,ty=side*18,30
    for i in range(8):
        size=12-i*.93
        z=i*1.6+.8
        cube('Stepped shrine sandstone',(tx,ty,z),(size,size,1.6),'stone',g,.12)
        cube('Stepped shrine gold lip',(tx,ty,z+.78),(size+.28,size+.28,.16),'gold',g,.035)
    for j in range(4):
        cube('Shrine dark window',(tx+(j-1.5)*1.55,ty-6.04,2.1),(.7,.035,1.8),'darkstone',g,.03)
        cube('Shrine aperture turquoise',(tx+(j-1.5)*1.55,ty-6.07,2.1),(.10,.015,1.4),'aqua',g,.01)
    cylinder('Shrine crown',(tx,ty,14.3),2.4,3,'teal',g,8,top=.8)
    cylinder('Shrine gold spire',(tx,ty,17.3),.8,4,'gold',g,8,top=.04)
    sphere('Shrine sacred pearl',(tx,ty,18.0),(.24,.24,.24),'aqua',g)
    banner('Shrine long standard',tx,ty-5.95,11.0,2.1,6.8,g)
# Main temple: rising staircase, monumental gate and colossal original idol.
for i in range(12):
    cube('Processional stair',(0,18.9+i*.65,.16+i*.32),(13,.72,.32),'lightstone',g,.025)
cube('Head sanctum plinth',(0,32,2),(17,15,4),'stone',g,.15)
cube('Head sanctum gilt belt',(0,32,4.05),(17.5,15.5,.3),'gold',g,.08)
for x in (-7.1,7.1):
    cube('Gate pier',(x,25.5,11.4),(2.15,2.6,14.8),'stone',g,.12)
    for z in (4.6,5.2,11.8,18.2):
        cube('Gate pier gold courses',(x,25.5,z),(2.3,2.75,.28),'gold',g,.03)
    banner('Gate banner',x,24.12,12.8,1.45,5.6,g)
cube('Gate cross lintel',(0,25.5,18.7),(16.4,3.0,1.3),'lightstone',g,.14)
cube('Gate crown lintel',(0,25.5,19.5),(17.6,3.4,.32),'gold',g,.07)
diamond('Gate central sigil',(0,23.85,18.8),1.4,1.8,.45,'aqua',g)
for x in (-7.1,7.1):
    for z in (6.2,7.1,8.0,9.0,10.0,13.8,14.7,15.6,16.5):
        diamond('Gate carved lozenge',(x,24.13,z),.64,.59,.10,'bronze',g)
for x in (-5.8,5.8):
    for i in range(12):
        cube('Stair balustrade',(x,18.9+i*.65,.55+i*.32),(.4,.66,.65),'stone',g,.035)
        cube('Stair balustrade gilded cap',(x,18.9+i*.65,.88+i*.32),(.45,.70,.07),'gold',g,.008)

# Weathered mask, formed from original polygonal volumes, facing the arena (-Y).
sphere('Colossal divine head',(0,34,12),(5.0,3.45,7.1),'stone',g,32,20)
sphere('Colossal jaw',(0,32.05,9.0),(3.75,2.18,3.4),'lightstone',g,24,12)
for side in (-1,1):
    ico('Colossal cheek plane',(side*2.65,30.97,11.3),(1.52,.85,2.3),'lightstone',g,1)
    cube('Colossal closed eye',(side*1.84,30.76,13.8),(2.55,.5,.38),'darkstone',g,.12,rotation=(0,side*.08,side*.08))
    cube('Colossal gold eyelid',(side*1.83,30.45,13.96),(2.57,.18,.12),'gold',g,.025,rotation=(0,side*.08,side*.08))
    cube('Colossal brow',(side*1.84,30.92,14.55),(2.7,.9,.63),'lightstone',g,.16,rotation=(0,side*.06,side*.11))
    sphere('Colossal elongated ear',(side*4.65,33.3,11.2),(.86,1.0,2.75),'stone',g,16,12)
    ring('Colossal earring',(side*4.68,32.9,8.6),1.04,.17,'gold',g,(math.pi/2,0,0),32)
ico('Colossal geometric nose',(0,29.99,12.4),(.74,1.05,2.10),'lightstone',g,1)
cube('Colossal meditative mouth',(0,29.72,9.73),(2.65,.22,.14),'darkstone',g,.055)
cube('Colossal lower lip',(0,29.81,9.48),(2.45,.43,.32),'lightstone',g,.10)
diamond('Colossal forehead oath',(0,30.59,16.2),.82,1.6,.28,'aqua',g)
for z,rr in ((17.4,4.55),(18.0,4.5),(18.5,4.0),(19.1,3.5)):
    cylinder('God crown stacked diadem',(0,34,z),rr,.48,'gold' if z in (18.0,19.1) else 'teal',g,16)
for i in range(9):
    x=(i-4)*.88
    h=3.9-abs(i-4)*.48
    diamond('God crown flame',(x,32.6,19.0+h*.5),.83,h,.58,'gold',g)
ring('Great solar halo',(0,37.7,15),12.0,.30,'gold',g,(math.pi/2,0,0),96)
ring('Great solar inner flame',(0,37.5,15),11.35,.07,'ember',g,(math.pi/2,0,0),96)
for i in range(40):
    a=math.tau*i/40
    v=Vector((math.cos(a),0,math.sin(a)))
    a1=Vector((0,37.7,15))+v*12.2
    b1=Vector((0,37.7,15))+v*(13.0 if i%2 else 13.7)
    rod('Solar halo radial blade',a1,b1,.17,'gold',g,top=.025,vertices=4)
# Broken stone, retaining rocks and distant skyline stay outside the arena.
for side in (-1,1):
    for i in range(22):
        x=side*random.uniform(22.5,35)
        y=random.uniform(-15,44)
        z=random.uniform(-2,-.3)
        obj=ico('Scattered ancient foundation',(x,y,z),(random.uniform(1,3),random.uniform(1,3),random.uniform(1.5,4)),'stone',g,1)
        obj.rotation_euler.z=random.random()*math.pi
for i in range(16):
    x=(i-7.5)*8
    ico('Distant sacred mountain',(x,66+random.uniform(-3,15),-3),(random.uniform(7,13),random.uniform(6,13),random.uniform(12,29)),'mountain',g,1)


def warrior(group, height, four_arms=False):
    """Articulated statues built in normalized 1.8 m character proportions."""
    s=height/1.8
    def P(p): return tuple(v*s for v in p)
    def C(n,p,sc,m,b=.015): return cube(n,P(p),P(sc),m,group,b*s)
    def S(n,p,sc,m): return sphere(n,P(p),P(sc),m,group)
    def R(n,a,b,r,m,top=None): return rod(n,P(a),P(b),r*s,m,group,None if top is None else top*s)
    def D(n,p,w,h,t,m): return diamond(n,P(p),w*s,h*s,t*s,m,group)
    armor='bronze' if four_arms else 'teal'
    skin='stone' if four_arms else 'skin'
    # Legs visibly separated for readable silhouettes and a root at the feet.
    for side in (-1,1):
        x=.16*side
        C('Armored boot',(x,-.075,.09),(.23,.38,.18),'darkstone',.035)
        C('Boot gold toe',(x,-.25,.12),(.225,.10,.1),'gold')
        R('Shin',(x,0,.21),(x,.015,.52),.093,'leather',.08)
        C('Greave front',(x,-.097,.38),(.20,.07,.31),armor,.026)
        D('Greave gilt chevron',(x,-.14,.38),.18,.25,.025,'gold')
        S('Knee joint',(x,0,.58),(.11,.11,.10),'gold')
        R('Thigh',(x,.02,.62),(side*.13,0,.88),.12,'leather',.105)
        C('Thigh plate',(x,-.105,.75),(.21,.07,.24),armor,.028)
        C('Hip lamella',(side*.205,0,.86),(.12,.30,.28),armor,.035)
    S('Waist undersuit',(0,0,.95),(.22,.145,.17),'leather')
    cylinder('War belt',P((0,0,.98)),.24*s,.09*s,'gold',group,12)
    # Angular sculptural breastplate and central oath stone.
    S('Torso',(0,0,1.17),(.29,.17,.24),'leather')
    C('Breastplate',(0,-.12,1.22),(.48,.13,.28),armor,.055)
    for side in (-1,1):
        obj=C('Chest gold chevron',(side*.105,-.205,1.23),(.25,.035,.035),'gold',.008)
        obj.rotation_euler.y=side*-.32
        C('Rib bronze band',(side*.24,-.055,1.10),(.09,.24,.08),'gold')
    D('Heart oath crystal',(0,-.215,1.26),.095,.17,.045,'ember' if four_arms else 'aqua')
    for z in (1.01,1.07,1.13):
        C('Abdominal plate',(0,-.148,z),(.29,.05,.045),armor,.01)
    R('Neck',(0,0,1.38),(0,0,1.46),.073,skin)
    S('Head',(0,-.014,1.56),(.115,.11,.145),skin)
    S('Helmet',(0,.012,1.62),(.145,.132,.125),armor)
    C('Helmet face opening',(0,-.117,1.565),(.17,.025,.055),'darkstone',.006)
    C('Helmet eye light',(0,-.133,1.568),(.142,.012,.012),'ember' if four_arms else 'aqua',.002)
    D('Helmet brow crest',(0,-.128,1.677),.09,.18,.047,'gold')
    for side in (-1,1):
        D('Helmet cheek guard',(side*.113,-.079,1.52),.068,.20,.08,armor)
        R('Helmet swept horn',(side*.113,.024,1.65),(side*.205,.05,1.785),.045,'gold',.008)
    # Spread arms, with elbows and hands clearly distinguished.
    for side in (-1,1):
        shoulder=(side*.32,0,1.33)
        elbow=(side*.48,-.035,1.13)
        hand=(side*.57,-.12,.96)
        S('Shoulder joint',shoulder,(.12,.12,.12),'gold')
        S('Layered pauldron',(side*.34,0,1.38),(.18,.20,.10),armor)
        C('Pauldron gold rim',(side*.36,-.10,1.405),(.23,.22,.035),'gold')
        R('Upper arm',shoulder,elbow,.081,skin,.072)
        S('Elbow',elbow,(.088,.083,.083),'gold')
        R('Forearm',elbow,hand,.09,armor,.067)
        S('Gauntlet',hand,(.078,.07,.091),'gold')
        if four_arms:
            a=(side*.30,.10,1.20)
            b=(side*.65,.10,1.40)
            c=(side*.76,.08,1.67)
            S('Second shoulder',a,(.115,.115,.115),'gold')
            R('Second upper arm',a,b,.092,skin,.08)
            S('Second elbow',b,(.095,.095,.095),'gold')
            R('Raised second forearm',b,c,.10,armor,.065)
            S('Raised second hand',c,(.073,.065,.09),'gold')
            D('Held votive flame',(side*.77,.08,1.82),.11,.28,.1,'ember')
    # Front skirt and rear cloth are geometric, avoiding external textures.
    for side in (-1,1):
        verts=[P((side*.035,-.17,.94)),P((side*.20,-.14,.93)),P((side*.26,-.17,.62)),P((side*.04,-.205,.60))]
        mesh('Split saffron tabard',verts,[(0,1,2,3)],'cloth',group)
        R('Tabard gilt seam',(side*.045,-.209,.61),(side*.037,-.176,.92),.012,'gold')
    mesh('Short battle cloak',[P((-.21,.17,1.32)),P((.21,.17,1.32)),P((.29,.29,.68)),P((0,.31,.60)),P((-.29,.29,.68))],[(0,1,2,3,4)],'cloth',group)
    if four_arms:
        # Halo defines a readable four-armed sacred sentinel silhouette.
        ring('Sentinel solar halo',P((0,.27,1.18)),.60*s,.022*s,'gold',group,(math.pi/2,0,0),64)
        ring('Sentinel incandescent halo',P((0,.28,1.18)),.55*s,.009*s,'ember',group,(math.pi/2,0,0),64)
        for i in range(20):
            a=i*math.tau/20
            pa=(math.cos(a)*.62,.27,1.18+math.sin(a)*.62)
            pb=(math.cos(a)*.69,.27,1.18+math.sin(a)*.69)
            R('Halo ray',pa,pb,.022,'gold',.004)


g=asset('hero')
warrior(g,1.8)
g=asset('sentinel')
# Heroic silhouette including halo/flames remains below approximately 6.4 m.
warrior(g,6.0,True)
# Normalize final bounds including helmet horns and held flames, not just the
# anatomical template, so engine import heights match their documented values.
for character, target_height in (('hero',1.8),('sentinel',6.0)):
    bpy.context.view_layer.update()
    objs=[obj for obj in collections[character].objects if obj.type=='MESH']
    depsgraph=bpy.context.evaluated_depsgraph_get()
    highest=max((obj.matrix_world@v.co).z for obj in objs for v in obj.evaluated_get(depsgraph).data.vertices)
    factor=target_height/highest
    for obj in objs:
        obj.location*=factor
        obj.scale*=factor
g=asset('spear')
cylinder('Spear blackwood haft',(0,0,.98),.021,1.96,'leather',g,12)
for z in (.10,.48,.61,.74,1.55,1.82,1.93):
    cylinder('Spear gold grip ring',(0,0,z),.031,.028,'gold',g,12)
rod('Spear butt spike',(0,0,.04),(0,0,0),.024,'gold',g,.001)
diamond('Spear broad bronze blade',(0,0,2.16),.20,.48,.045,'gold',g)
diamond('Spear turquoise blade inset',(0,-.028,2.16),.07,.32,.015,'aqua',g)
for side in (-1,1):
    rod('Spear crescent guard',(0,0,1.92),(side*.135,0,2.06),.025,'gold',g,.008)
    rod('Spear crescent tip',(side*.135,0,2.06),(side*.12,0,2.17),.011,'gold',g,.001)


def glb_json(path):
    data=path.read_bytes()
    length,kind=struct.unpack_from('<II',data,12)
    assert kind==0x4e4f534a
    return json.loads(data[20:20+length])


def export_asset(name):
    # Keep sculptural source objects editable; exported copies are merged by
    # material to give the realtime prototype a small, predictable draw count.
    bpy.ops.object.select_all(action='DESELECT')
    root=bpy.data.objects.new(name+'_root_export',None)
    bpy.context.scene.collection.objects.link(root)
    root['units']='meters'
    temp=[root]
    meshes={}
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for source in list(collections[name].objects):
        if source.type!='MESH': continue
        data=bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph))
        obj=bpy.data.objects.new(source.name+'_baked',data)
        bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world=source.matrix_world.copy()
        obj.parent=root
        key=data.materials[0].name
        meshes.setdefault(key,[]).append(obj)
    merged=[]
    for key,objects in meshes.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects: obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join()
        obj=bpy.context.object
        obj.name=name+'__'+key.split(' |')[0].replace(' ','_')
        merged.append(obj)
    forward=bpy.data.objects.new('Facing_reference__source_minusY__gltf_plusZ',None)
    bpy.context.scene.collection.objects.link(forward)
    forward.parent=root
    forward.location=(0,-1,0)
    temp.extend(merged+[forward])
    bpy.ops.object.select_all(action='DESELECT')
    for obj in temp: obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    path=OUT/'exports'/f'{name}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    bpy.ops.export_scene.fbx(filepath=str(path.with_suffix('.fbx')),use_selection=True,object_types={'EMPTY','MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',path_mode='AUTO')
    triangles=0
    bounds=[]
    for obj in merged:
        obj.data.calc_loop_triangles()
        triangles+=len(obj.data.loop_triangles)
        bounds.extend([obj.matrix_world@v.co for v in obj.data.vertices])
    doc=glb_json(path)
    marker=next(node for node in doc['nodes'] if node.get('name','').startswith('Facing_reference'))
    assert all(abs(a-b)<1e-5 for a,b in zip(marker['translation'],[0,0,1])),marker
    result={
        'triangles':triangles,'material_batches':len(merged),
        'source_bounds_m':{'min':[min(p[i] for p in bounds) for i in range(3)],'max':[max(p[i] for p in bounds) for i in range(3)]},
        'glb_bytes':path.stat().st_size,'fbx_bytes':path.with_suffix('.fbx').stat().st_size,
        'gltf_forward_marker_translation':marker['translation'],
    }
    for obj in temp:
        bpy.data.objects.remove(obj,do_unlink=True)
    return result


for folder in ('source','exports','renders'):
    (OUT/folder).mkdir(parents=True,exist_ok=True)
manifest={name:export_asset(name) for name in collections}
assert manifest['temple']['triangles']<180000
assert manifest['hero']['triangles']<15000
assert manifest['sentinel']['triangles']<30000
assert all(v[k]<20_000_000 for v in manifest.values() for k in ('glb_bytes','fbx_bytes'))
(OUT/'exports'/'manifest.json').write_text(json.dumps({'generator':'tools/blender/build_assets.py','blender_version':bpy.app.version_string,'units':'meters','source_up':'+Z','source_character_forward':'-Y','gltf_up':'+Y','gltf_character_forward':'+Z','assets':manifest},indent=2)+'\n')

# Staging is applied only after exports, so every downloadable asset stays rooted
# at (0,0,0). The source .blend opens as the complete editable presentation scene.
roots['hero'].location=(0,-8,0)
roots['hero'].rotation_euler.z=math.pi
roots['spear'].location=(-.58,-7.86,.57)
roots['spear'].rotation_euler=(.25,-.15,.08)
roots['sentinel'].location=(0,5,0)

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.eevee.use_gtao=True
scene.eevee.gtao_distance=3
scene.eevee.gtao_factor=1.35
scene.eevee.use_bloom=True
scene.eevee.bloom_intensity=.16
scene.eevee.use_soft_shadows=True
scene.eevee.taa_render_samples=128
scene.render.resolution_x=1600
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath='//../renders/preview.png'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.085,.145,.20,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.40
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=.7

def light(name,kind,loc,color,energy,size=1,target=None):
    data=bpy.data.lights.new(name,kind)
    data.color=color
    data.energy=energy
    if kind=='AREA': data.shape='DISK'; data.size=size
    elif kind=='SUN': data.angle=.18
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=loc
    if target:
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj

light('Golden hour | key','SUN',(-30,-12,40),(1,.70,.38),3.3,target=(0,15,0))
light('Open sky | blue fill','AREA',(8,-12,24),(.34,.64,1),4500,25,target=(0,7,4))
light('Divine sanctum | warm bounce','AREA',(0,25,20),(1,.42,.14),3200,14,target=(0,0,2))
light('Sentinel rim','AREA',(-5,10,10),(.03,1,.77),850,6,target=(0,5,3))

camera_data=bpy.data.cameras.new('Lost Temple | beauty camera')
camera=bpy.data.objects.new('Lost Temple | beauty camera',camera_data)
scene.collection.objects.link(camera)
camera.location=(25,-33,23)
camera.rotation_euler=(Vector((0,15,8))-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.lens=27
camera_data.clip_end=300
scene.camera=camera
scene['project']='Shenjin: War of Three Oaths / original procedural first art study'
scene['rebuild']='blender --background --python tools/blender/build_assets.py -- --render'
scene['arena_contract']='Ground z=0, clear radius 18m. Hero (0,-8,0); Sentinel (0,5,0).'
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source'/'lost-temple.blend'))
if args.render:
    bpy.ops.render.render(write_still=True)
print('SHENJIN_ASSET_MANIFEST '+json.dumps(manifest))
