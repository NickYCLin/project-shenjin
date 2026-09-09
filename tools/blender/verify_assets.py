"""Round-trip GLB and FBX art imports and check source collision-floor spacing."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
expected={'temple':None,'hero':1.8,'sentinel':6.0,'spear':2.4}
results={}
for suffix in ('glb','fbx'):
    for name,height in expected.items():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        path=ROOT/'art'/'exports'/f'{name}.{suffix}'
        if suffix=='glb':
            bpy.ops.import_scene.gltf(filepath=str(path))
        else:
            bpy.ops.import_scene.fbx(filepath=str(path))
        bpy.context.view_layer.update()
        meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']
        assert meshes, path
        points=[obj.matrix_world@v.co for obj in meshes for v in obj.data.vertices]
        lo=[min(p[i] for p in points) for i in range(3)]
        hi=[max(p[i] for p in points) for i in range(3)]
        if height:
            assert abs(lo[2])<.002,(path,lo)
            assert abs(hi[2]-height)<.005,(path,hi,height)
            forward=next(obj for obj in bpy.context.scene.objects if obj.name.startswith('Facing_reference'))
            assert (forward.matrix_world.translation-Vector((0,-1,0))).length<.001
        assert not [obj for obj in bpy.context.scene.objects if obj.type in {'CAMERA','LIGHT'}]
        triangles=0
        for obj in meshes:
            obj.data.calc_loop_triangles()
            triangles+=len(obj.data.loop_triangles)
        results[f'{name}.{suffix}']={'meshes':len(meshes),'triangles':triangles,'bounds_m':{'min':lo,'max':hi},'bytes':path.stat().st_size}

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art'/'source'/'lost-temple.blend'))
def max_z(name):
    obj=bpy.data.objects[name]
    return max((obj.matrix_world@v.co).z for v in obj.data.vertices)
assert abs(max_z('Arena upper stone'))<1e-6
assert max_z('Arena foundation')<-.24
assert bpy.context.scene.render.resolution_x==1600
assert bpy.context.scene.render.resolution_y==900
results['checks']={'round_trip_imports':8,'source_ground_z':0,'foundation_top_z':max_z('Arena foundation'),'render_resolution':[1600,900],'original_materials_only':True}
(ROOT/'art'/'exports'/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
print('SHENJIN_ART_VERIFIED '+json.dumps(results['checks']))
