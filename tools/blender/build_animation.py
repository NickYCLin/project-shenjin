"""Build original skinned characters and in-place skeletal animation in Blender 4.0+.

blender --background --python tools/blender/build_animation.py -- --render
The editable static sculptural source is read but never overwritten.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

import bpy
import bmesh
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'art'
FPS = 100
CLIPS = {
    'hero': {'Idle': 2., 'Walk': .8, 'Thrust': .55, 'Dodge': .32, 'Hit': .35, 'Death': 1.4},
    'sentinel': {'Idle': 2.4, 'Walk': 1.2, 'Windup': 1.1, 'Slam': .3, 'Recover': 1.05, 'Hit': .4, 'Death': 1.8},
}
parser = argparse.ArgumentParser()
parser.add_argument('--render', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(ART / 'source' / 'lost-temple.blend'))
bpy.context.preferences.filepaths.save_version = 0
source_scene = bpy.context.scene
source_scene.name = 'Original editable sculptures'


def configure_metal_surface():
    """Use available CC0 microstructure while preserving the bronze/teal palette."""
    folder = ART / 'textures' / 'metal_plate'
    normal_path = folder / 'metal_plate_nor_gl_2k.jpg'
    rough_path = folder / 'metal_plate_rough_2k.jpg'
    if not normal_path.exists() or not rough_path.exists():
        return False
    normal = bpy.data.images.load(str(normal_path), check_existing=True)
    rough = bpy.data.images.load(str(rough_path), check_existing=True)
    for im in (normal, rough):
        im.colorspace_settings.name = 'Non-Color'
        im.pack()
        im.filepath = '//../textures/metal_plate/' + Path(im.filepath).name
    for name in ('Bronze | polished gold', 'Bronze | ancient patina', 'Enamel | peacock teal'):
        material = bpy.data.materials[name]
        nodes, links = material.node_tree.nodes, material.node_tree.links
        shader = nodes.get('Principled BSDF')
        palette = {'Bronze | polished gold': (.42, .23, .073, 1),
                   'Bronze | ancient patina': (.085, .120, .095, 1),
                   'Enamel | peacock teal': (.012, .065, .065, 1)}
        material.diffuse_color = palette[name]
        shader.inputs['Base Color'].default_value = palette[name]
        ntex = nodes.new('ShaderNodeTexImage')
        ntex.name, ntex.image = 'CC0 metal microstructure | normal', normal
        normal_node = nodes.new('ShaderNodeNormalMap')
        normal_node.inputs['Strength'].default_value = .27
        links.new(ntex.outputs['Color'], normal_node.inputs['Color'])
        links.new(normal_node.outputs['Normal'], shader.inputs['Normal'])
        rtex = nodes.new('ShaderNodeTexImage')
        rtex.name, rtex.image = 'CC0 metal weathering | roughness', rough
        links.new(rtex.outputs['Color'], shader.inputs['Roughness'])
    return True


HAS_PBR = configure_metal_surface()


def ease(v):
    v = max(0., min(1., v))
    return v * v * (3. - 2. * v)


def envelope(u, peak=.36):
    return ease(u / peak) if u < peak else 1. - ease((u - peak) / (1. - peak))


def transform(start, end, rest):
    """Map a bone's rest orientation to a world-space segment without scaling it."""
    rotation = (rest.tail_local - rest.head_local).rotation_difference(end - start)
    result = rotation.to_matrix().to_4x4() @ rest.matrix_local
    result.translation = start
    return result


def two_bone(start, end, length_a, length_b, pole):
    """Analytical limb solve; export contains baked bones, no runtime IK required."""
    direction = end - start
    distance = max(.0001, min(direction.length, length_a + length_b - .00001))
    axis = direction.normalized()
    bend = pole - axis * pole.dot(axis)
    if bend.length < .001:
        bend = axis.cross(Vector((1, 0, 0)))
    bend.normalize()
    along = (length_a ** 2 - length_b ** 2 + distance ** 2) / (2 * distance)
    height = math.sqrt(max(0., length_a ** 2 - along ** 2))
    return start + axis * along + bend * height, start + axis * distance


def glb_document(path):
    data = path.read_bytes()
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4e4f534a
    return json.loads(data[20:20 + size])


def refine_sculpture(name, scene, pieces, scale):
    """Replace block armor with layered curved metal and original relief detail.

    These are actual mesh surfaces and segmented hand anatomy, retained in the
    editable source and bound to the same skeleton as the locomotion prototype.
    """
    materials = {
        'armor': bpy.data.materials['Bronze | ancient patina' if name == 'sentinel' else 'Enamel | peacock teal'],
        'gold': bpy.data.materials['Bronze | polished gold'],
        'dark': bpy.data.materials['Leather | midnight'],
        'cloth': bpy.data.materials['Cloth | saffron orange'],
        'skin': bpy.data.materials['Sandstone | warm ash' if name == 'sentinel' else 'Stone flesh | ivory'],
        'glow': bpy.data.materials['Divine fire | amber' if name == 'sentinel' else 'Divine fire | turquoise'],
    }
    palette = {
        'hero': {
            'armor': ('Blackened iron', (.014, .018, .021, 1), .76, .48),
            'gold': ('Antique gold', (.37, .215, .070, 1), .78, .39),
            'dark': ('Worn black leather', (.009, .007, .005, 1), 0., .91),
            'cloth': ('Weathered ivory silk', (.34, .31, .255, 1), 0., .93),
            'skin': ('Shadow skin', (.135, .073, .044, 1), 0., .82),
            'glow': ('Amber oath inset', (.30, .105, .019, 1), .1, .35),
        },
        'sentinel': {
            'armor': ('Aged bronze', (.063, .074, .050, 1), .65, .57),
            'gold': ('Ancient gold relief', (.31, .178, .056, 1), .71, .48),
            'dark': ('Obsidian recess', (.008, .012, .011, 1), .1, .88),
            'cloth': ('Oxblood silk', (.083, .010, .008, 1), 0., .93),
            'skin': ('Dark limestone', (.075, .088, .071, 1), .08, .87),
            'glow': ('Divine ember', (.49, .12, .018, 1), .1, .38),
        },
    }[name]
    for key, (label, color, metallic, roughness) in palette.items():
        copied = materials[key].copy()
        copied.name = name.title() + ' | ' + label
        copied.diffuse_color = color
        shader = copied.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = color
        shader.inputs['Metallic'].default_value = metallic
        shader.inputs['Roughness'].default_value = roughness
        if key == 'glow':
            shader.inputs['Emission Color'].default_value = color
            shader.inputs['Emission Strength'].default_value = .65 if name == 'hero' else 1.25
        copied.use_backface_culling = False
        materials[key] = copied

    def mesh(label, vertices, faces, mat, joint, smooth=True):
        data = bpy.data.meshes.new(name + ' ' + label)
        data.from_pydata([Vector(v) * scale for v in vertices], [], faces)
        data.update()
        obj = bpy.data.objects.new(name + ' | ' + label, data)
        scene.collection.objects.link(obj)
        data.materials.append(materials[mat])
        obj['original_sculpture'] = label
        obj['assigned_bone'] = joint
        obj['detail_pass'] = 'Curved armor and hand-sculpted procedural relief'
        for polygon in data.polygons:
            polygon.use_smooth = smooth
        pieces.append(obj)
        return obj

    def tube(label, path, radius, mat, joint, closed=False, sides=6):
        vertices, faces = [], []
        for i, point in enumerate(path):
            p = Vector(point)
            tangent = (Vector(path[(i + 1) % len(path)]) - Vector(path[i - 1])).normalized() if closed else (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(i - 1, 0)])).normalized()
            normal = tangent.cross(Vector((0, 1, 0)))
            if normal.length < .01:
                normal = tangent.cross(Vector((1, 0, 0)))
            normal.normalize()
            binormal = tangent.cross(normal).normalized()
            for j in range(sides):
                angle = math.tau * j / sides
                vertices.append(p + radius * (normal * math.cos(angle) + binormal * math.sin(angle)))
        for i in range(len(path) if closed else len(path) - 1):
            for j in range(sides):
                faces.append((i * sides + j, i * sides + (j + 1) % sides, ((i + 1) % len(path)) * sides + (j + 1) % sides, ((i + 1) % len(path)) * sides + j))
        return mesh(label, vertices, faces, mat, joint)

    def ellipsoid(label, center, radii, mat, joint, segments=20, rings=12):
        vertices, faces = [], []
        for row in range(rings + 1):
            theta = math.pi * row / rings
            for column in range(segments):
                phi = math.tau * column / segments
                vertices.append((center[0] + radii[0] * math.sin(theta) * math.cos(phi), center[1] + radii[1] * math.sin(theta) * math.sin(phi), center[2] + radii[2] * math.cos(theta)))
        for row in range(rings):
            for column in range(segments):
                a = row * segments + column
                b = row * segments + (column + 1) % segments
                faces.append((a, b, b + segments, a + segments))
        return mesh(label, vertices, faces, mat, joint)

    def shield(label, x, y, z, width, height, joint, mat='armor', ribs=3):
        # Crown to tapered spear point, curved across the limb; no cube faces.
        nx, nz = 14, 16
        vertices, faces = [], []
        def point(u, t):
            taper = (.66 + .34 * math.sin(math.pi * t / 2)) * (1. - .72 * max(0., (t - .78) / .22))
            xx = u * width * taper * .5
            yy = y + .039 * (abs(u) ** 1.8) - .008 * math.cos(u * math.pi * ribs) * math.sin(math.pi * t)
            zz = z + height * (.5 - t)
            return (x + xx, yy, zz)
        for row in range(nz + 1):
            for column in range(nx + 1):
                vertices.append(point(column / nx * 2. - 1., row / nz))
        for row in range(nz):
            for column in range(nx):
                a = row * (nx + 1) + column
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
        obj = mesh(label, vertices, faces, mat, joint)
        edge = [point(-1, k / nz) for k in range(nz + 1)]
        edge += [point(1, k / nz) for k in range(nz, -1, -1)]
        tube(label + ' rolled gold border', [(a, b - .006, c) for a, b, c in edge], .005, 'gold', joint, True)
        for sign in (-1, 1):
            for row in range(3):
                points = []
                for k in range(25):
                    t = k / 24
                    a = math.pi * 2.2 * t
                    radius = width * .15 * (1. - .8 * t)
                    xx = x + sign * (width * .20 + math.cos(a) * radius)
                    zz = z + height * (.25 - row * .22) + math.sin(a) * radius
                    yy = y - .015 + .027 * ((xx - x) / (width * .5)) ** 2
                    points.append((xx, yy, zz))
                tube(label + ' chased spiral', points, .0021, 'gold', joint, sides=5)
        return obj

    remove = {
        'Armored boot', 'Boot gold toe', 'Greave front', 'Greave gilt chevron', 'Thigh plate',
        'Hip lamella', 'Breastplate', 'Chest gold chevron', 'Rib bronze band',
        'Abdominal plate', 'Layered pauldron', 'Pauldron gold rim',
        'Helmet', 'Helmet face opening', 'Helmet eye light', 'Helmet brow crest',
        'Helmet cheek guard', 'Helmet swept horn', 'Split saffron tabard',
        'Tabard gilt seam', 'Gauntlet', 'Upper arm', 'Forearm',
        'Second upper arm', 'Raised second forearm', 'Raised second hand', 'Held votive flame',
        'Short battle cloak',
    }
    for piece in list(pieces):
        label = piece['original_sculpture'].split('.')[0]
        if label in remove:
            pieces.remove(piece)
            bpy.data.objects.remove(piece, do_unlink=True)
            continue
        previous = piece.data.materials[0].name
        key = ('gold' if previous.startswith('Bronze | polished') else
               'armor' if previous.startswith(('Enamel', 'Bronze | ancient')) else
               'cloth' if previous.startswith('Cloth') else
               'glow' if previous.startswith('Divine') else
               'skin' if previous.startswith(('Stone flesh', 'Sandstone')) else 'dark')
        piece.data.materials.clear()
        piece.data.materials.append(materials[key])
        center = sum((v.co for v in piece.data.vertices), Vector()) / len(piece.data.vertices)
        if label in ('Knee joint', 'Elbow', 'Shoulder joint', 'Second shoulder', 'Second elbow'):
            for vertex in piece.data.vertices:
                vertex.co = center + (vertex.co - center) * .78
            piece.data.materials.clear()
            piece.data.materials.append(materials['dark'])
        if label == 'Armored boot':
            for vertex in piece.data.vertices:
                local = (vertex.co - center) / scale
                local.x *= .78 * (1. - .18 * max(0., -local.y / .19))
                local.y *= .82
                local.z *= .90
                vertex.co = center + local * scale
                vertex.co.z -= .009 * scale
        if label == 'Head':
            anchor = Vector((0, 0, 1.46)) * scale
            for vertex in piece.data.vertices:
                delta = vertex.co - anchor
                vertex.co = anchor + Vector((delta.x * .83, delta.y * .87, delta.z * .79))
        if label == 'War belt':
            piece.data.materials.clear()
            piece.data.materials.append(materials['dark'])

    for side, suffix in ((-1, 'L'), (1, 'R')):
        leg = side * .16
        # Anatomical boots: rounded toe, narrow ankle, arched upper and a flat
        # thin sole replace the original oversized rectangular block feet.
        vertices, faces = [], []
        profiles = [(0., .078, -.070, .140), (.018, .082, -.070, .145),
                    (.047, .080, -.066, .142), (.079, .074, -.053, .124),
                    (.119, .067, -.025, .090), (.180, .059, .000, .064)]
        for z, width, y, depth in profiles:
            for k in range(32):
                a = k / 32 * math.tau
                vertices.append((leg + math.cos(a) * width, y + math.sin(a) * depth, z))
        faces.append(tuple(range(31, -1, -1)))
        for row in range(len(profiles) - 1):
            for k in range(32):
                a = row * 32 + k
                b = row * 32 + (k + 1) % 32
                faces.append((a, b, b + 32, a + 32))
        faces.append(tuple((len(profiles) - 1) * 32 + k for k in range(32)))
        mesh('Sculpted anatomical battle boot', vertices, faces, 'dark', 'Foot.' + suffix)
        for row in (1, 5):
            tube('Boot welt and ankle bronze rim', [vertices[row * 32 + k] for k in range(32)], .0035, 'gold', 'Foot.' + suffix, True)
        shield('Anatomical engraved greave', leg, -.123, .40, .185, .39, 'Shin.' + suffix)
        shield('Overlapping thigh cuisse', leg, -.118, .76, .19, .25, 'Thigh.' + suffix)
        shield('Pointed knee guard', leg, -.151, .57, .17, .17, 'Shin.' + suffix)
        for row in range(3):
            path = [(leg + math.cos(math.pi + k / 20 * math.pi) * .090, -.015 + math.sin(math.pi + k / 20 * math.pi) * .123, .23 + row * .11) for k in range(21)]
            tube('Greave transverse locking strap', path, .009, 'dark', 'Shin.' + suffix)
        for row in range(4):
            z = .075 + row * .028
            lower, upper = next((a, b) for a, b in zip(profiles, profiles[1:]) if a[0] <= z <= b[0])
            t = (z - lower[0]) / (upper[0] - lower[0])
            width, cy, depth = [lower[i] * (1 - t) + upper[i] * t for i in (1, 2, 3)]
            path = []
            for k in range(17):
                x = (k / 16 - .5) * width * 1.7
                path.append((leg + x, cy - depth * math.sqrt(1 - (x / width) ** 2) - .001, z))
            tube('Articulated sabaton seam', path, .004, 'gold', 'Foot.' + suffix)
        # Three overlapping, curved shoulder lames follow the upper arm.
        for tier in range(3):
            vertices, faces = [], []
            for row in range(9):
                t = row / 8
                for col in range(21):
                    a = math.pi * (.06 + .90 * col / 20)
                    radius = .162 - tier * .016 + .016 * math.sin(math.pi * t)
                    vertices.append((side * (.31 + tier * .059 + .040 * t), -math.cos(a) * radius,
                                     1.36 - tier * .042 + math.sin(a) * (.066 + .010 * t) - t * .039))
            for row in range(8):
                for col in range(20):
                    a = row * 21 + col
                    faces.append((a, a + 1, a + 22, a + 21))
            mesh('Layered lotus shoulder lame', vertices, faces, 'armor', 'UpperArm.' + suffix)
            for row in (0, 8):
                tube('Shoulder chased gold lip', [vertices[row * 21 + k] for k in range(21)], .005, 'gold', 'UpperArm.' + suffix)
            for i in range(5):
                point = vertices[8 * 21 + 2 + i * 4]
                ellipsoid('Shoulder hammered rivet', point, (.0055, .0055, .0055), 'gold', 'UpperArm.' + suffix, 8, 5)
        # Forearm armor uses the original elbow/hand axis with fine gold cuffs.
        elbow, hand = Vector((side * .48, -.035, 1.13)), Vector((side * .57, -.12, .96))
        shoulder = Vector((side * .32, 0, 1.33))
        limb_segments = [(shoulder, elbow, .073, .093, .057, 'UpperArm.' + suffix, 'skin'),
                         (elbow, hand, .071, .081, .047, 'Forearm.' + suffix, 'armor')]
        if name == 'sentinel':
            limb_segments += [(Vector((side * .30, .10, 1.20)), Vector((side * .65, .10, 1.40)), .088, .105, .068, 'UpperArm2.' + suffix, 'skin'),
                              (Vector((side * .65, .10, 1.40)), Vector((side * .76, .08, 1.67)), .075, .084, .048, 'Forearm2.' + suffix, 'armor')]
        for start, end, radius_start, radius_mid, radius_end, joint, surface in limb_segments:
            tangent = (end - start).normalized()
            normal = tangent.cross(Vector((0, 1, 0))).normalized()
            bitangent = tangent.cross(normal).normalized()
            vertices, faces = [], []
            for row in range(17):
                t = row / 16
                radius = radius_start * (1. - t) + radius_end * t + (radius_mid - (radius_start + radius_end) / 2) * math.sin(t * math.pi)
                center = start.lerp(end, t)
                for k in range(24):
                    a = k / 24 * math.tau
                    profile = 1. + .055 * math.sin(a * 3) * math.sin(t * math.pi)
                    vertices.append(center + radius * profile * (normal * math.cos(a) + bitangent * math.sin(a)))
            for row in range(16):
                for k in range(24):
                    a = row * 24 + k
                    b = row * 24 + (k + 1) % 24
                    faces.append((a, b, b + 24, a + 24))
            mesh('Sculpted muscle and tapered vambrace', vertices, faces, surface, joint)
            if surface == 'armor':
                for k in range(5):
                    a = math.pi * .65 + k * .25
                    path = []
                    for row in range(15):
                        t = .08 + row / 14 * .80
                        radius = radius_start * (1. - t) + radius_end * t + (radius_mid - (radius_start + radius_end) / 2) * math.sin(t * math.pi)
                        path.append(start.lerp(end, t) + (radius + .003) * (normal * math.cos(a) + bitangent * math.sin(a)))
                    tube('Vambrace longitudinal gold fluting', path, .0028, 'gold', joint)
        axis = (hand - elbow).normalized()
        normal = axis.cross(Vector((0, 1, 0))).normalized()
        tangent = axis.cross(normal).normalized()
        for row in range(5):
            center = elbow.lerp(hand, .18 + row * .14)
            radius = .078 - row * .004
            path = [center + radius * (normal * math.cos(k / 24 * math.tau) + tangent * math.sin(k / 24 * math.tau)) for k in range(24)]
            tube('Bracer articulated gilt hoop', path, .0045, 'gold', 'Forearm.' + suffix, True)
        # Closed palm and individually modelled curled fingers replace mittens.
        ellipsoid('Leather wrapped palm', hand, (.045, .041, .060), 'dark', 'Hand.' + suffix)
        for finger in range(4):
            x = hand.x + (finger - 1.5) * .018
            for joint in range(3):
                angle = .4 + joint * .65
                center = (x, hand.y - .041 + .021 * math.sin(angle), hand.z - .037 + .026 * math.cos(angle))
                ellipsoid('Individual articulated finger', center, (.0095, .012, .016), 'skin', 'Hand.' + suffix, 10, 7)
                if joint == 0:
                    ellipsoid('Engraved knuckle plate', (x, hand.y - .045, hand.z + .001), (.011, .011, .014), 'gold', 'Hand.' + suffix, 10, 6)
        ellipsoid('Opposing grip thumb', (hand.x - side * .045, hand.y - .017, hand.z - .002), (.017, .018, .031), 'skin', 'Hand.' + suffix)
        if name == 'sentinel':
            palm = Vector((side * .76, .08, 1.67))
            ellipsoid('Upper hand anatomical palm', palm, (.047, .033, .060), 'skin', 'Hand2.' + suffix)
            for finger in range(4):
                x = palm.x + (finger - 1.5) * .019
                for segment in range(3):
                    center = (x, palm.y - .031 + segment * .010, palm.z + .038 + segment * .020)
                    ellipsoid('Upper hand finger segment', center, (.010, .011, .015), 'skin', 'Hand2.' + suffix, 10, 7)
            ellipsoid('Upper hand curved thumb', (palm.x - side * .049, palm.y - .003, palm.z + .005), (.016, .017, .031), 'skin', 'Hand2.' + suffix)
        # Long, pleated cloth with a geometric embroidered hem.
        vertices, faces = [], []
        for row in range(25):
            t = row / 24
            for col in range(13):
                u = col / 12
                x = side * (.025 + .19 * u + .025 * t)
                y = -.174 - .027 * math.sin(u * math.pi * 6) * (.3 + t * .7) - .03 * t
                z = .96 - .50 * t + (.040 * math.sin(u * math.pi) + .022 * math.sin(u * math.pi * 7)) * t ** 5
                vertices.append((x, y, z))
        for row in range(24):
            for col in range(12):
                a = row * 13 + col
                faces.append((a, a + 1, a + 14, a + 13))
        mesh('Folded oath silk tabard', vertices, faces, 'cloth', 'Tabard.' + suffix)
        for column in (0, 12):
            tube('Tabard woven edge braid', [vertices[row * 13 + column] for row in range(25)], .0032, 'gold', 'Tabard.' + suffix)
        for row in (20, 22):
            tube('Tabard embroidered hem', [vertices[row * 13 + k] for k in range(13)], .0027, 'gold', 'Tabard.' + suffix)
        for t in range(5):
            shield('Waist suspended lamellar scale', side * (.225 + .006 * t), -.045, .94 - t * .059, .102, .13, 'Thigh.' + suffix, ribs=1)
        # Paired breastplate has convex surfaces, engraved spirals, and a spine
        # ridge; four lower lames keep a readable abdominal silhouette.
        shield('Forged pectoral plate', side * .125, -.199, 1.225, .245, .31, 'Spine')
    # Three narrow, deeply folded tails leave the back armor visible and move
    # from the cloak bone; their torn hems replace the rigid orange rectangle.
    for panel in range(3):
        vertices, faces = [], []
        for row in range(29):
            t = row / 28
            for col in range(11):
                u = col / 10
                x = (panel - 1) * (.115 + .04 * t) + (u - .5) * (.095 + .02 * t)
                y = .170 + .145 * t + .030 * math.sin(u * math.pi * 4 + panel) * (.25 + .75 * t)
                z = 1.28 - (.72 + .07 * (panel % 2)) * t + (.028 * math.sin(u * math.pi * 5 + panel) + .017 * math.cos(u * 21)) * t ** 7
                vertices.append((x, y, z))
        for row in range(28):
            for col in range(10):
                a = row * 11 + col
                faces.append((a, a + 1, a + 12, a + 11))
        mesh('Tattered folded back silk tail', vertices, faces, 'cloth', 'Cloak')
        for edge in (0, 10):
            tube('Weathered cloak narrow seam', [vertices[row * 11 + edge] for row in range(29)], .002, 'dark', 'Cloak')
    for row in range(4):
        shield('Flexible abdominal lame', 0., -.223 + row * .012, 1.105 - row * .039, .265 - row * .011, .068, 'Pelvis', ribs=2)
    # Oath medallion: twelve chased rays around a luminous inset stone.
    for ring_radius in (.050, .064):
        path = [(math.cos(k / 40 * math.tau) * ring_radius, -.235, 1.25 + math.sin(k / 40 * math.tau) * ring_radius) for k in range(40)]
        tube('Oath medallion concentric relief', path, .004, 'gold', 'Spine', True)
    for k in range(12):
        a = k / 12 * math.tau
        path = [(math.cos(a) * (.068 + i / 4 * .026), -.231, 1.25 + math.sin(a) * (.068 + i / 4 * .026)) for i in range(5)]
        tube('Oath medallion sun ray', path, .0027, 'gold', 'Spine')
    # Face planes are smaller than the first sculpt and are no longer hidden by
    # a rectangular visor. A long narrow crown preserves the 1.8 m export bound.
    # A stern faceted war mask has deep eye recesses and a continuous nose keel.
    # Neither character uses floating eyeballs, nose balls or smiling lip tubes.
    face_mat = 'armor' if name == 'hero' else 'skin'
    vertices = [(-.085, -.068, 1.616), (.085, -.068, 1.616),
                (-.080, -.083, 1.553), (.080, -.083, 1.553),
                (-.064, -.077, 1.479), (.064, -.077, 1.479),
                (0, -.111, 1.456), (0, -.146, 1.527), (0, -.116, 1.616),
                (-.018, -.131, 1.552), (.018, -.131, 1.552)]
    faces = [(0, 2, 9, 8), (8, 10, 3, 1), (2, 4, 7, 9), (10, 7, 5, 3), (4, 6, 7), (7, 6, 5), (9, 7, 10, 8)]
    mesh('Severe faceted oath war mask', vertices, faces, face_mat, 'Head', False)
    for side in (-1, 1):
        eye = [(side * .020, -.132, 1.574), (side * .068, -.100, 1.583),
               (side * .065, -.101, 1.565), (side * .022, -.132, 1.563)]
        mesh('Deep slanted eye recess', eye, [(0, 1, 2, 3)], 'dark', 'Head', False)
        tube('Heavy angled mask brow', [(side * .017, -.136, 1.583), (side * .045, -.118, 1.594), (side * .075, -.096, 1.593)], .011, face_mat, 'Head')
        tube('Recessed ember eye glint', [(side * .029, -.133, 1.570), (side * .052, -.116, 1.576)], .0018, 'glow', 'Head')
        tube('Mask cheek etched gold line', [(side * .067, -.091, 1.548), (side * .050, -.107, 1.513), (side * .024, -.121, 1.478)], .0025, 'gold', 'Head')
    ellipsoid('Swept dark hair and helmet liner', (0, .012, 1.622), (.10, .103, .082), 'dark', 'Head', 28, 16)
    if name == 'hero':
        for strand in range(19):
            x = (strand - 9) * .010
            path = []
            for k in range(23):
                t = k / 22
                path.append((x * (1 - .40 * t) + .032 * math.sin(t * 4 + strand * .4) * t,
                             .055 + .092 * math.sin(t * math.pi / 2) + .020 * math.sin(t * 7 + strand),
                             1.68 - .36 * t - .04 * math.sin(strand)))
            tube('Long swept battle hair lock', path, .0065, 'dark', 'Head', sides=7)
    for row in range(3):
        path = [(math.cos(k / 48 * math.tau) * (.099 + row * .004), math.sin(k / 48 * math.tau) * .106, 1.625 + row * .017) for k in range(48)]
        tube('Crown engraved diadem band', path, .005, 'gold', 'Head', True)
    for side in (-1, 1):
        for layer in range(3):
            path = []
            for k in range(18):
                t = k / 17
                path.append((side * (.045 + layer * .018 + .021 * math.sin(t * math.pi)), -.099 + .08 * t,
                             1.66 + .099 * t - layer * .011))
            tube('Fluted crown flame blade', path, .008 - layer * .001, 'gold', 'Head')
    if name == 'hero':
        # Exact tip bound equals the original normalized source height.
        top = 1.8 / scale
        mesh('Crown narrow sovereign fin', [(-.017, -.070, 1.66), (.017, -.070, 1.66), (0, -.030, top), (0, -.092, 1.705)],
             [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)], 'gold', 'Head', False)
    if name == 'sentinel':
        top = 6.0 / scale
        mesh('Halo sovereign flame crown', [(-.062, .25, top - .22), (.062, .25, top - .22),
              (0, .25, top), (0, .208, top - .145), (0, .292, top - .145)],
             [(0, 1, 3), (0, 3, 2), (1, 2, 3), (0, 4, 1), (0, 2, 4), (1, 4, 2)], 'gold', 'Spine', False)
        # Halo filigree is physical geometry and follows the Spine bone.
        for k in range(32):
            angle = k / 32 * math.tau
            radius = .59
            x, z = math.cos(angle) * radius, 1.18 + math.sin(angle) * radius
            path = [(x + math.cos(t / 20 * math.tau) * .014, .238, z + math.sin(t / 20 * math.tau) * .021) for t in range(20)]
            tube('Halo carved lattice knot', path, .0032, 'gold', 'Spine', True)
    return pieces


def make_character(name):
    source_objects = [obj for obj in bpy.data.collections[name.upper()].objects if obj.type == 'MESH']
    source_root = bpy.data.objects[name + '_root']
    root_inverse = source_root.matrix_world.inverted()
    head_source = next(obj for obj in source_objects if obj.name.split('.')[0] == 'Head')
    scale = (root_inverse @ head_source.matrix_world).translation.z / 1.56
    scene = bpy.data.scenes.new(name.title() + ' | animated')
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.
    scene.render.fps = FPS
    scene.render.fps_base = 1.
    scene.frame_start = 0
    scene.frame_end = 240
    bpy.context.window.scene = scene
    # Linked source data is evaluated in its original scene to preserve bevels.
    bpy.context.window.scene = source_scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pieces = []
    for source in source_objects:
        data = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph))
        data.transform(root_inverse @ source.matrix_world)
        piece = bpy.data.objects.new(name + ' | ' + source.name, data)
        scene.collection.objects.link(piece)
        piece['original_sculpture'] = source.name
        pieces.append(piece)
    bpy.context.window.scene = scene
    pieces = refine_sculpture(name, scene, pieces, scale)
    data = bpy.data.armatures.new(name.title() + 'Skeleton')
    rig = bpy.data.objects.new(name.title() + 'Rig', data)
    scene.collection.objects.link(rig)
    rig.show_in_front = True
    rig['units'] = 'meters'
    rig['source_forward'] = '-Y'
    rig['gltf_forward'] = '+Z'
    rig['root_motion'] = False
    rig['weapon_socket'] = 'WeaponSocket'
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')

    def bone(n, h, t, parent=None, deform=True):
        b = data.edit_bones.new(n)
        b.head = Vector(h) * scale
        b.tail = Vector(t) * scale
        b.use_deform = deform
        if parent:
            b.parent = data.edit_bones[parent]
        return b

    bone('Root', (0, 0, 0), (0, 0, .15), deform=False)
    bone('Pelvis', (0, 0, .9), (0, 0, 1.03), 'Root')
    bone('Spine', (0, 0, 1.03), (0, 0, 1.36), 'Pelvis')
    bone('Neck', (0, 0, 1.36), (0, 0, 1.46), 'Spine')
    bone('Head', (0, 0, 1.46), (0, 0, 1.72), 'Neck')
    bone('Cloak', (0, .18, 1.30), (0, .30, .65), 'Spine')
    for side, suffix in ((-1, 'L'), (1, 'R')):
        bone('Thigh.' + suffix, (side * .13, 0, .88), (side * .16, 0, .58), 'Pelvis')
        bone('Shin.' + suffix, (side * .16, 0, .58), (side * .16, 0, .12), 'Thigh.' + suffix)
        bone('Foot.' + suffix, (side * .16, 0, .12), (side * .16, -.25, .12), 'Shin.' + suffix)
        bone('UpperArm.' + suffix, (side * .32, 0, 1.33), (side * .48, -.035, 1.13), 'Spine')
        bone('Forearm.' + suffix, (side * .48, -.035, 1.13), (side * .57, -.12, .96), 'UpperArm.' + suffix)
        bone('Hand.' + suffix, (side * .57, -.12, .96), (side * .57, -.22, .96), 'Forearm.' + suffix)
        bone('Tabard.' + suffix, (side * .12, -.16, .94), (side * .15, -.19, .61), 'Pelvis')
        if name == 'sentinel':
            bone('UpperArm2.' + suffix, (side * .30, .10, 1.20), (side * .65, .10, 1.40), 'Spine')
            bone('Forearm2.' + suffix, (side * .65, .10, 1.40), (side * .76, .08, 1.67), 'UpperArm2.' + suffix)
            bone('Hand2.' + suffix, (side * .76, .08, 1.67), (side * .76, .08, 1.80), 'Forearm2.' + suffix)
    # A glTF spear's long axis is +Y. Local +Y of this socket points forward.
    bone('WeaponSocket', (.57, -.12, .96), (.57, -.32, .96), 'Hand.R', False)
    bone('WeaponTip', (.57, -.32, .96), (.57, -.42, .96), 'WeaponSocket', False)
    bpy.ops.object.mode_set(mode='OBJECT')

    def piece_bone(piece):
        if piece.get('assigned_bone'):
            return piece['assigned_bone']
        n = piece['original_sculpture'].split('.')[0]
        center = sum((v.co for v in piece.data.vertices), Vector()) / len(piece.data.vertices)
        suffix = '.R' if center.x > 0 else '.L'
        if n in ('Armored boot', 'Boot gold toe'):
            return 'Foot' + suffix
        if n in ('Shin', 'Greave front', 'Greave gilt chevron', 'Knee joint'):
            return 'Shin' + suffix
        if n in ('Thigh', 'Thigh plate', 'Hip lamella'):
            return 'Thigh' + suffix
        if n in ('Shoulder joint', 'Layered pauldron', 'Pauldron gold rim', 'Upper arm'):
            return 'UpperArm' + suffix
        if n in ('Elbow', 'Forearm'):
            return 'Forearm' + suffix
        if n == 'Gauntlet':
            return 'Hand' + suffix
        if n in ('Second shoulder', 'Second upper arm'):
            return 'UpperArm2' + suffix
        if n in ('Second elbow', 'Raised second forearm'):
            return 'Forearm2' + suffix
        if n in ('Raised second hand', 'Held votive flame'):
            return 'Hand2' + suffix
        if n.startswith('Helmet') or n == 'Head':
            return 'Head'
        if n == 'Neck':
            return 'Neck'
        if n in ('Split saffron tabard', 'Tabard gilt seam'):
            return 'Tabard' + suffix
        if n == 'Short battle cloak':
            return 'Cloak'
        if n in ('Waist undersuit', 'War belt', 'Abdominal plate'):
            return 'Pelvis'
        return 'Spine'

    for piece in pieces:
        joint = piece_bone(piece)
        # Local box projection avoids untextured new plates and puts UV seams
        # on changes of surface direction. Textures contain no baked lighting.
        for layer in list(piece.data.uv_layers):
            piece.data.uv_layers.remove(layer)
        uv = piece.data.uv_layers.new(name='SurfaceUV')
        for polygon in piece.data.polygons:
            dominant = max(range(3), key=lambda i: abs(polygon.normal[i]))
            axes = ((1, 2), (0, 2), (0, 1))[dominant]
            for loop_index in polygon.loop_indices:
                vertex = piece.data.vertices[piece.data.loops[loop_index].vertex_index]
                uv.data[loop_index].uv = (vertex.co[axes[0]] / scale * 4., vertex.co[axes[1]] / scale * 4.)
        group = piece.vertex_groups.new(name=joint)
        group.add(list(range(len(piece.data.vertices))), 1., 'REPLACE')
        modifier = piece.modifiers.new('Skeletal deformation', 'ARMATURE')
        modifier.object = rig
        piece.parent = rig
        piece['deform_bone'] = joint
    rig.animation_data_create()
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return scene, rig, pieces, scale


def pose(rig, scale, clip, seconds, duration):
    """Pose segmented limbs; all x/y root coordinates remain fixed at zero."""
    u = seconds / duration
    normalized = lambda p: Vector(p) * scale
    pbs = rig.pose.bones
    for pb in pbs:
        pb.matrix_basis = Matrix.Identity(4)
    matrices = {}
    def posed_matrix(pb):
        if pb.name in matrices:
            return matrices[pb.name]
        parent_matrix = posed_matrix(pb.parent) @ pb.parent.bone.matrix_local.inverted() if pb.parent else Matrix.Identity(4)
        return parent_matrix @ pb.bone.matrix_local @ pb.matrix_basis
    def set_matrix(pb, value):
        parent_matrix = posed_matrix(pb.parent) @ pb.parent.bone.matrix_local.inverted() if pb.parent else Matrix.Identity(4)
        pb.matrix_basis = (parent_matrix @ pb.bone.matrix_local).inverted() @ value
        matrices[pb.name] = value.copy()
    bob, tilt, turn, crouch = 0., 0., 0., 0.
    right = Vector((.38, -.28, 1.14))
    left = Vector((-.38, -.24, 1.12))
    foot_y = {'L': 0., 'R': 0.}
    foot_lift = {'L': 0., 'R': 0.}
    windup = 0.
    if clip == 'Idle':
        breath = math.sin(u * math.tau)
        tilt = .017 * breath
        right.z += .008 * breath
        left.z += .01 * breath
    elif clip == 'Walk':
        cycle = math.sin(u * math.tau)
        crouch = .028
        bob = -.007 * (1. - math.cos(u * 2. * math.tau))
        turn = .055 * cycle
        tilt = .04
        for suffix, sign in (('L', 1), ('R', -1)):
            phase = cycle * sign
            foot_y[suffix] = -.14 * phase
            foot_lift[suffix] = .11 * max(0., math.cos(u * math.tau) * sign) ** 2
        right.y += .10 * cycle
        left.y -= .10 * cycle
        right.z -= .045
        left.z -= .045
    elif clip == 'Thrust':
        strike = envelope(u, .20 / duration)
        tilt = .14 * strike
        turn = -.17 * strike
        crouch = .035 * strike
        right = right.lerp(Vector((.24, -.43, 1.25)), strike)
        left = left.lerp(Vector((-.18, -.35, 1.25)), strike)
    elif clip == 'Dodge':
        duck = math.sin(math.pi * u) ** 2
        crouch = .24 * duck
        tilt = .52 * duck
        turn = -.35 * duck
        right = right.lerp(Vector((.30, -.19, 1.02)), duck)
        left = left.lerp(Vector((-.31, -.15, 1.05)), duck)
    elif clip == 'Hit':
        recoil = envelope(u, .22)
        tilt = -.20 * recoil
        turn = .14 * recoil
        crouch = .055 * recoil
        right.z -= .09 * recoil
        left.z -= .09 * recoil
    elif clip in ('Windup', 'Slam', 'Recover'):
        windup = ease(u) if clip == 'Windup' else (1. - ease(u) if clip == 'Slam' else 0.)
        impact = ease(u) if clip == 'Slam' else (1. - ease(u) if clip == 'Recover' else 0.)
        tilt = -.10 * windup + .35 * impact
        crouch = .12 * impact
        right = right.lerp(Vector((.37, -.08, 1.71)), windup)
        left = left.lerp(Vector((-.37, -.08, 1.71)), windup)
        right = right.lerp(Vector((.28, -.41, .99)), impact)
        left = left.lerp(Vector((-.28, -.41, .99)), impact)
    elif clip == 'Death':
        collapse = ease(u)
        crouch = .47 * collapse
        tilt = 1.16 * collapse
        turn = .16 * collapse
        foot_y = {'L': .05 * collapse, 'R': .09 * collapse}
        right = right.lerp(Vector((.36, -.25, .99)), collapse)
        left = left.lerp(Vector((-.30, -.31, .95)), collapse)

    pelvis = pbs['Pelvis']
    pm = pelvis.bone.matrix_local.copy()
    pm.translation.z += (bob - crouch) * scale
    set_matrix(pelvis, pm)
    spine = pbs['Spine']
    spine_matrix = Matrix.Translation(normalized((0, 0, bob - crouch))) @ spine.bone.matrix_local
    spine_matrix = spine_matrix @ Quaternion((1, 0, 0), tilt).to_matrix().to_4x4()
    spine_matrix = spine_matrix @ Quaternion((0, 1, 0), turn).to_matrix().to_4x4()
    set_matrix(spine, spine_matrix)
    torso_delta = spine_matrix @ spine.bone.matrix_local.inverted()
    for suffix in ('L', 'R'):
        thigh, shin, foot = [pbs[n + '.' + suffix] for n in ('Thigh', 'Shin', 'Foot')]
        hip = thigh.bone.head_local + normalized((0, 0, bob - crouch))
        ankle = foot.bone.head_local + normalized((0, foot_y[suffix], foot_lift[suffix]))
        knee, ankle = two_bone(hip, ankle, thigh.bone.length, shin.bone.length, Vector((0, -1, 0)))
        set_matrix(thigh, transform(hip, knee, thigh.bone))
        set_matrix(shin, transform(knee, ankle, shin.bone))
        fm = foot.bone.matrix_local.copy()
        fm.translation = ankle
        set_matrix(foot, fm)
        for extra in (False, True):
            arm_name = 'UpperArm2.' if extra else 'UpperArm.'
            if arm_name + suffix not in pbs:
                continue
            upper = pbs[arm_name + suffix]
            fore = pbs[('Forearm2.' if extra else 'Forearm.') + suffix]
            hand = pbs[('Hand2.' if extra else 'Hand.') + suffix]
            shoulder = torso_delta @ upper.bone.head_local
            hand_target = right if suffix == 'R' else left
            if extra:
                sign = 1 if suffix == 'R' else -1
                hand_target = Vector((sign * (.72 - windup * .12), .08 - windup * .15, 1.68 + windup * .22))
                if clip == 'Walk':
                    hand_target.y += .035 * math.sin(u * math.tau + sign)
                if clip == 'Death':
                    hand_target = hand_target.lerp(Vector((sign * .60, -.22, 1.30)), ease(u))
            target = torso_delta @ normalized(hand_target)
            pole = Vector((1 if suffix == 'R' else -1, .16, -.12 if not extra else .3))
            elbow, target = two_bone(shoulder, target, upper.bone.length, fore.bone.length, pole)
            set_matrix(upper, transform(shoulder, elbow, upper.bone))
            set_matrix(fore, transform(elbow, target, fore.bone))
            hm = torso_delta @ hand.bone.matrix_local
            hm.translation = target
            set_matrix(hand, hm)
        tabard = pbs['Tabard.' + suffix]
        tabard.rotation_quaternion = Quaternion((1, 0, 0), -.22 * crouch / .24 + (foot_y[suffix] * .5))
    pbs['Head'].rotation_quaternion = Quaternion((1, 0, 0), -.22 * tilt)
    pbs['Cloak'].rotation_quaternion = Quaternion((1, 0, 0), .08 * math.sin(u * math.tau) if clip in ('Idle', 'Walk') else .13 * tilt)
    bpy.context.view_layer.update()


def bake_actions(name, scene, rig, pieces, scale):
    actions = {}
    for clip, duration in CLIPS[name].items():
        action = bpy.data.actions.new(name.title() + '_' + clip)
        action.use_fake_user = True
        action['loop'] = clip in ('Idle', 'Walk')
        action['duration_seconds'] = duration
        action['in_place'] = True
        rig.animation_data.action = action
        end = round(duration * FPS)
        # Sampling every 10 ms gives exact game timings and deterministic FBX bakes.
        for frame in range(end + 1):
            scene.frame_set(frame)
            pose(rig, scale, clip, frame / FPS, duration)
            for pb in rig.pose.bones:
                if pb.name == 'Root':
                    continue
                pb.keyframe_insert('location', frame=frame, group=pb.name)
                pb.keyframe_insert('rotation_quaternion', frame=frame, group=pb.name)
                pb.keyframe_insert('scale', frame=frame, group=pb.name)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        actions[clip] = action
        rig.animation_data.action = None
        track = rig.animation_data.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 0, action)
        strip.name = clip
        strip.action_frame_start = 0
        strip.action_frame_end = end
        strip.frame_start = 0
        strip.frame_end = end
        strip.extrapolation = 'NOTHING'
        track.mute = True
    # Measure the actual deformed mesh, including its rigid armor, at every
    # baked frame. Root never moves and there is no hidden runtime floor fix.
    floors = {}
    for clip, action in actions.items():
        rig.animation_data.action = action
        lowest, correction = math.inf, 0.
        floor_parts = [obj for obj in pieces if obj['deform_bone'].startswith(('Foot.', 'Shin.', 'Thigh.'))]
        for frame in range(round(CLIPS[name][clip] * FPS) + 1):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            floor = min((obj.matrix_world @ v.co).z for obj in floor_parts for v in obj.evaluated_get(depsgraph).data.vertices)
            lowest = min(lowest, floor)
            correction = max(correction, max(0., -floor))
        # The planted foot's geometry is analytically level; significant floor
        # errors indicate a rig bug and must not be hidden with whole-body lifts.
        assert lowest > -.002, (name, clip, lowest)
        floors[clip] = {'minimum_leg_vertex_z_m': round(lowest, 7), 'maximum_required_correction_m': round(correction, 7)}
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene.frame_set(0)
    return actions, floors


def export_character(name, scene, rig, pieces, actions, floors):
    bpy.context.window.scene = scene
    bpy.ops.object.select_all(action='DESELECT')
    copies = []
    for piece in pieces:
        obj = piece.copy()
        obj.data = piece.data.copy()
        scene.collection.objects.link(obj)
        obj.select_set(True)
        copies.append(obj)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = name.title() + 'Skin'
    triangulated = bmesh.new()
    triangulated.from_mesh(merged.data)
    bmesh.ops.dissolve_degenerate(triangulated, dist=1e-8, edges=list(triangulated.edges))
    bmesh.ops.triangulate(triangulated, faces=list(triangulated.faces))
    # The original bevelled halo rods can leave sub-millimetre sliver faces.
    # Their float32 UV determinant collapses and produces a zero tangent. Remove
    # those near-zero-area triangles before tangent generation, not afterwards.
    slivers = [face for face in triangulated.faces if face.calc_area() < 1e-7]
    if slivers:
        bmesh.ops.delete(triangulated, geom=slivers, context='FACES')
    triangulated.to_mesh(merged.data)
    triangulated.free()
    merged.data.update()
    for piece in pieces:
        piece.hide_render = True
        piece.hide_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = ART / 'exports' / (name + '-rigged.glb')
    # One character per scene and NLA track names prevent accidental action
    # sharing and give Three.AnimationMixer stable, unprefixed clip names.
    for track in rig.animation_data.nla_tracks:
        track.mute = False
    # glTF skinned meshes belong at scene root; skeleton transforms are already
    # supplied by joint matrices and inverse binds. Keep conventional parenting
    # for the separate FBX export below.
    world_transform = merged.matrix_world.copy()
    merged.parent = None
    merged.matrix_world = world_transform
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format='GLB', use_selection=True, use_active_scene=True,
        export_yup=True, export_apply=False, export_animations=True,
        export_animation_mode='NLA_TRACKS', export_nla_strips=True,
        export_force_sampling=True, export_frame_range=False,
        export_anim_slide_to_zero=True, export_anim_single_armature=False,
        export_skins=True, export_all_influences=False, export_def_bones=False,
        export_tangents=True,
        export_cameras=False, export_lights=False, export_extras=True,
    )
    merged.parent = rig
    merged.matrix_world = world_transform
    bpy.ops.export_scene.fbx(
        filepath=str(path.with_suffix('.fbx')), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Y', axis_up='Z',
        bake_anim=True, bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
        bake_anim_step=1., bake_anim_simplify_factor=0.,
        add_leaf_bones=False, use_armature_deform_only=False,
        mesh_smooth_type='FACE', path_mode='AUTO',
    )
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene.frame_set(0)
    doc = glb_document(path)
    exported = {clip['name']: clip for clip in doc.get('animations', [])}
    assert set(exported) == set(CLIPS[name]), (name, list(exported))
    assert len(doc.get('skins', [])) == 1
    clip_report = {}
    for clip, expected_duration in CLIPS[name].items():
        animation = exported[clip]
        starts = [doc['accessors'][sampler['input']]['min'][0] for sampler in animation['samplers']]
        ends = [doc['accessors'][sampler['input']]['max'][0] for sampler in animation['samplers']]
        duration = max(ends) - min(starts)
        assert abs(duration - expected_duration) < .00001, (name, clip, duration, expected_duration)
        clip_report[clip] = {
            'duration_seconds': expected_duration, 'loop': clip in ('Idle', 'Walk'),
            'channels': len(animation['channels']), 'in_place': True,
            **floors[clip],
        }
        if clip == 'Thrust':
            clip_report[clip]['contact_time_seconds'] = .20
    merged.data.calc_loop_triangles()
    result = {
        'armature': rig.name, 'mesh': merged.name, 'height_m': 1.8 if name == 'hero' else 6.,
        'skins': len(doc['skins']), 'bones': [bone.name for bone in rig.data.bones],
        'joints': len(doc['skins'][0]['joints']), 'vertices': len(merged.data.vertices),
        'triangles': len(merged.data.loop_triangles), 'clips': clip_report,
        'glb_bytes': path.stat().st_size, 'fbx_bytes': path.with_suffix('.fbx').stat().st_size,
        'weapon_socket': 'WeaponSocket', 'socket_local_forward': '+Y',
        'spear_grip_offset_local_y_m': -.65,
    }
    bpy.data.objects.remove(merged, do_unlink=True)
    for piece in pieces:
        piece.hide_render = False
        piece.hide_set(False)
    scene['clip_contract'] = json.dumps(CLIPS[name])
    scene['preview_instructions'] = 'Select armature; Action Editor actions Hero_* / Sentinel_*. NLA tracks are muted for clean single-action editing.'
    return result


characters = {}
manifest = {'generator': 'tools/blender/build_animation.py', 'blender_version': bpy.app.version_string,
            'units': 'meters', 'source_up': '+Z', 'source_character_forward': '-Y',
            'gltf_up': '+Y', 'gltf_character_forward': '+Z', 'fps': FPS, 'root_motion': False,
            'source': 'art/source/lost-temple.blend', 'license': 'MIT',
            'geometry_detail_pass': 'Curved engraved armor, layered lames, facial planes, articulated fingers, pleated silk',
            'metal_pbr_microstructure': HAS_PBR, 'pbr_license': 'CC0-1.0; see art/textures/sources.json' if HAS_PBR else None,
            'assets': {}}
for character in CLIPS:
    scene, rig, pieces, scale = make_character(character)
    actions, floors = bake_actions(character, scene, rig, pieces, scale)
    manifest['assets'][character] = export_character(character, scene, rig, pieces, actions, floors)
    characters[character] = (scene, rig, pieces, scale, actions)

# A separate preview scene preserves every editable original part and animation.
preview = bpy.data.scenes.new('Animation showcase')
bpy.context.window.scene = preview
preview.render.engine = 'BLENDER_EEVEE'
preview.eevee.use_gtao = True
preview.eevee.gtao_distance = 3
preview.eevee.use_bloom = True
preview.eevee.taa_render_samples = 64
preview.render.resolution_x = 1600
preview.render.resolution_y = 900
preview.render.resolution_percentage = 100
preview.render.image_settings.file_format = 'PNG'
preview.render.filepath = '//../renders/animation-preview.png'
preview.world = source_scene.world.copy()
preview.view_settings.view_transform = 'AgX'
preview.view_settings.look = 'AgX - Medium High Contrast'
preview.view_settings.exposure = -.25
preview.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .25
for character, (scene, rig, pieces, scale, actions) in characters.items():
    rig.animation_data.action = actions['Thrust' if character == 'hero' else 'Windup']
    # Linked objects keep the edit scenes useful; staging stays on collection
    # instances so the skinned export roots and animation data stay in place.
    collection = bpy.data.collections.new(character.title() + ' Preview Group')
    collection.objects.link(rig)
    for piece in pieces:
        collection.objects.link(piece)
    instance = bpy.data.objects.new(character.title() + ' Presentation', None)
    instance.instance_type = 'COLLECTION'
    instance.instance_collection = collection
    preview.collection.objects.link(instance)
    instance.location = (-2.0, -1., 0.) if character == 'hero' else (1.5, 1., 0.)
    instance.rotation_euler.z = -.25 if character == 'hero' else .2
preview.render.fps = FPS
preview.frame_set(20)
bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
floor.name = 'Showcase floor'
floor.data.materials.append(bpy.data.materials['Arena | basalt teal'])
for name, loc, energy, color, size in (
    ('Warm key', (-4, -6, 10), 2100, (1., .72, .44), 8),
    ('Blue fill', (5, -3, 6), 650, (.3, .65, 1.), 7),
    ('Gold rim', (0, 5, 8), 1600, (1., .45, .15), 6),
):
    data = bpy.data.lights.new(name, 'AREA')
    obj = bpy.data.objects.new(name, data)
    preview.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector((0, 0, 2.5)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.energy, data.color, data.size = energy, color, size
data = bpy.data.cameras.new('Animation showcase camera')
camera = bpy.data.objects.new('Animation showcase camera', data)
preview.collection.objects.link(camera)
camera.location = (9., -15., 8.)
camera.rotation_euler = (Vector((0, 0, 2.6)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
data.type = 'ORTHO'
data.ortho_scale = 13.5
preview.camera = camera
for scene in bpy.data.scenes:
    if scene != source_scene and scene != preview:
        scene.render.filepath = '//../renders/animation-preview.png'
    scene['animation_rebuild'] = 'blender --background --python tools/blender/build_animation.py -- --render'
bpy.ops.wm.save_as_mainfile(filepath=str(ART / 'source' / 'animated-characters.blend'), compress=True)
if args.render:
    bpy.ops.render.render(write_still=True)
(ART / 'exports' / 'animation-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('SHENJIN_ANIMATION_MANIFEST ' + json.dumps(manifest))
