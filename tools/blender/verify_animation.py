"""Verify GLB skin data and round-trip both skeletal formats using Blender.

blender --background --python tools/blender/verify_animation.py
Raises on missing clips, invalid weights, moving roots or floor penetration.
"""
from pathlib import Path
import json
import math
import re
import struct

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'art'
MANIFEST = ART / 'exports' / 'animation-manifest.json'
manifest = json.loads(MANIFEST.read_text())
report = {'glb_structure': {}, 'round_trip': {}}


def load_glb(path):
    blob = path.read_bytes()
    assert blob[:4] == b'glTF'
    json_size, kind = struct.unpack_from('<II', blob, 12)
    assert kind == 0x4e4f534a
    doc = json.loads(blob[20:20 + json_size])
    binary_start = 20 + json_size
    binary_size, binary_kind = struct.unpack_from('<II', blob, binary_start)
    assert binary_kind == 0x004e4942
    return doc, blob[binary_start + 8:binary_start + 8 + binary_size]


def accessor(doc, binary, index):
    item = doc['accessors'][index]
    view = doc['bufferViews'][item['bufferView']]
    component = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}[item['componentType']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[item['type']]
    fmt = '<' + component * count
    stride = view.get('byteStride', struct.calcsize(fmt))
    start = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    return [struct.unpack_from(fmt, binary, start + row * stride) for row in range(item['count'])]


for character, info in manifest['assets'].items():
    doc, binary = load_glb(ART / 'exports' / (character + '-rigged.glb'))
    assert len(doc['skins']) == 1
    joint_count = len(doc['skins'][0]['joints'])
    node_names = {i: n.get('name', '') for i, n in enumerate(doc['nodes'])}
    assert 'WeaponSocket' in node_names.values() and 'WeaponTip' in node_names.values()
    scene_roots = set(doc['scenes'][doc.get('scene', 0)]['nodes'])
    assert all(i in scene_roots for i, node in enumerate(doc['nodes']) if 'skin' in node)
    skinned_vertices = 0
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            attributes = primitive['attributes']
            if doc.get('materials', [])[primitive['material']].get('normalTexture'):
                assert 'TANGENT' in attributes and 'TEXCOORD_0' in attributes
                tangents = accessor(doc, binary, attributes['TANGENT'])
                assert all(abs(sum(value * value for value in tangent[:3]) - 1.) < .0002 for tangent in tangents)
                assert all(abs(abs(tangent[3]) - 1.) < .00001 for tangent in tangents)
            assert 'TEXCOORD_1' not in attributes, 'Merged characters must share one consistently named UV layer'
            weights = accessor(doc, binary, attributes['WEIGHTS_0'])
            joints = accessor(doc, binary, attributes['JOINTS_0'])
            assert len(weights) == len(joints)
            for values, indices in zip(weights, joints):
                assert all(math.isfinite(value) and value >= 0 for value in values)
                assert abs(sum(values) - 1.) < .00001, values
                assert all(index < joint_count for index in indices)
            skinned_vertices += len(weights)
    clips = {}
    for animation in doc['animations']:
        name = animation['name']
        expected = info['clips'][name]
        varying_bones = set()
        root_displacement = 0.
        for channel in animation['channels']:
            sampler = animation['samplers'][channel['sampler']]
            times = accessor(doc, binary, sampler['input'])
            values = accessor(doc, binary, sampler['output'])
            assert len(times) == len(values) and len(times) > 0
            assert abs(times[-1][0] - times[0][0] - expected['duration_seconds']) < .00001
            assert all(math.isfinite(v) for value in values for v in value)
            movement = max(sum((a - b) ** 2 for a, b in zip(value, values[0])) ** .5 for value in values)
            bone_name = node_names[channel['target']['node']]
            if movement > .0001:
                varying_bones.add(bone_name)
            if bone_name in ('Root', info['armature']) and channel['target']['path'] == 'translation':
                root_displacement = max(root_displacement, movement)
            if expected['loop']:
                assert max(abs(a - b) for a, b in zip(values[0], values[-1])) < .0001, (character, name, bone_name, 'loop seam')
        assert root_displacement < .00001
        assert len(varying_bones) >= 3, (character, name, varying_bones)
        if name == 'Walk':
            assert {'Thigh.L', 'Thigh.R', 'Shin.L', 'Shin.R', 'UpperArm.L', 'UpperArm.R'} <= varying_bones
        clips[name] = {'animated_bones': sorted(varying_bones), 'root_displacement_m': root_displacement}
    assert set(clips) == set(info['clips'])
    report['glb_structure'][character] = {'skins': 1, 'joint_count': joint_count, 'weighted_vertices': skinned_vertices, 'clips': clips}


def clip_alias(action_name, names):
    # Blender's FBX importer adds its armature/AnimStack separator; never choose
    # an arbitrary first clip when an expected semantic name cannot be found.
    candidates = [name for name in names if re.search(r'(?:^|[|_])' + re.escape(name) + r'(?:$|[|_]|\.\d+$)', action_name)]
    assert len(candidates) == 1, (action_name, candidates)
    return candidates[0]


for suffix in ('glb', 'fbx'):
    for character, info in manifest['assets'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.fps = manifest['fps']
        path = ART / 'exports' / f'{character}-rigged.{suffix}'
        if suffix == 'glb':
            bpy.ops.import_scene.gltf(filepath=str(path))
        else:
            bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
        rigs = [obj for obj in scene.objects if obj.type == 'ARMATURE']
        meshes = [obj for obj in scene.objects if obj.type == 'MESH']
        assert len(rigs) == 1 and meshes
        rig = rigs[0]
        custom_shapes = {bone.custom_shape for bone in rig.pose.bones if bone.custom_shape}
        meshes = [mesh for mesh in meshes if mesh not in custom_shapes]
        assert set(info['bones']) <= set(rig.data.bones.keys())
        assert len(rig.data.bones) == len(info['bones'])
        for mesh in meshes:
            assert any(mod.type == 'ARMATURE' and mod.object == rig for mod in mesh.modifiers)
            assert all(vertex.groups and abs(sum(group.weight for group in vertex.groups) - 1.) < .00001 for vertex in mesh.data.vertices)
        actions = {}
        for action in bpy.data.actions:
            if not any('pose.bones' in curve.data_path for curve in action.fcurves):
                continue
            alias = clip_alias(action.name, info['clips'])
            assert alias not in actions, (path, alias, 'duplicate animation')
            actions[alias] = action
        assert set(actions) == set(info['clips']), (path, list(actions))
        if rig.animation_data:
            rig.animation_data.action = None
            for track in rig.animation_data.nla_tracks:
                track.mute = True
        rig.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        points = [obj.matrix_world @ v.co for obj in meshes for v in obj.evaluated_get(depsgraph).data.vertices]
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        assert abs(low[2]) < .002, (path, low)
        assert abs(high[2] - info['height_m']) < .005, (path, high)
        socket = rig.data.bones['WeaponSocket'].head_local
        tip = rig.data.bones['WeaponTip'].head_local
        direction = (rig.matrix_world.to_3x3() @ (tip - socket)).normalized()
        assert (direction - Vector((0, -1, 0))).length < .0001, (path, direction)
        rig.data.pose_position = 'POSE'
        rig.animation_data_create()
        animation_report = {}
        for clip, action in actions.items():
            rig.animation_data.action = action
            start, end = action.frame_range
            duration = (end - start) / (scene.render.fps / scene.render.fps_base)
            assert abs(duration - info['clips'][clip]['duration_seconds']) < .011, (path, clip, duration)
            lowest = math.inf
            root_positions = []
            # Sample every 50 ms plus the exact last frame of every clip.
            frames = sorted(set([float(f) for f in range(math.ceil(start), math.floor(end) + 1, 5)] + [float(start), float(end)]))
            for frame in frames:
                scene.frame_set(math.floor(frame), subframe=frame % 1)
                depsgraph = bpy.context.evaluated_depsgraph_get()
                floor = min((obj.matrix_world @ v.co).z for obj in meshes for v in obj.evaluated_get(depsgraph).data.vertices)
                lowest = min(lowest, floor)
                root_positions.append(rig.matrix_world @ rig.pose.bones['Root'].head)
            displacement = max((position - root_positions[0]).length for position in root_positions)
            assert displacement < .00001, (path, clip, 'root motion', displacement)
            assert lowest > -.006, (path, clip, 'floor penetration', lowest)
            animation_report[clip] = {'imported_action': action.name, 'duration_seconds': round(duration, 6),
                                      'samples': len(frames), 'minimum_vertex_z_m': round(lowest, 7),
                                      'root_displacement_m': round(displacement, 7)}
        report['round_trip'][path.name] = {'armatures': 1, 'bones': len(rig.data.bones), 'meshes': len(meshes),
                                         'rest_bounds_m': {'min': low, 'max': high}, 'clips': animation_report}

bpy.ops.wm.open_mainfile(filepath=str(ART / 'source' / 'animated-characters.blend'))
assert len([obj for obj in bpy.data.objects if obj.type == 'ARMATURE']) == 2
assert all(scene.render.filepath.startswith('//') for scene in bpy.data.scenes)
report['checks'] = {'round_trip_imports': 4, 'clip_total': 13, 'source_relative_render_paths': True,
                    'normalized_vertex_weights': True, 'loop_endpoints_match': True,
                    'in_place_root': True, 'weapon_axis_verified': True}
manifest['verification'] = report
MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
print('SHENJIN_ANIMATION_VERIFIED ' + json.dumps(report['checks']))
