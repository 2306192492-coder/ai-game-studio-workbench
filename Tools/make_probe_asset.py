"""Deterministic small calibration prop for the Blender -> Unity import test."""
import bpy, math, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'AssetsSource'/'Blender';out.mkdir(parents=True,exist_ok=True)
unity=root/'Project'/'Assets'/'Studio'/'Models';unity.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials=[]
for name,color,metal in [('Walnut',(0.35,0.14,0.05,1),0),('Brass',(0.68,0.4,0.1,1),0.75)]:
 m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 p.inputs['Base Color'].default_value=color;p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.35
 materials.append(m)
def box(name,location,scale,material):
 bpy.ops.mesh.primitive_cube_add(size=1,location=location);o=bpy.context.object;o.name=name;o.scale=scale
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel=o.modifiers.new('Small edge bevel','BEVEL');bevel.width=.025;bevel.segments=3
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 o.data.materials.append(material)
 return o
box('Walnut_Platform',(0,0,.3),(1.2,.85,.6),materials[0])
for x in [-.48,.48]:box('Brass_Band', (x,0,.31),(.045,.87,.62),materials[1])
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.23,location=(0,0,.84))
o=bpy.context.object;o.name='Brass_CalibrationSphere';o.data.materials.append(materials[1]);bpy.ops.object.shade_smooth()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'calibration.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'calibration.glb'),export_format='GLB')
bpy.ops.export_scene.fbx(filepath=str(unity/'Calibration.fbx'),object_types={'MESH'},apply_unit_scale=True,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False)
(root/'Evidence'/'blender-production.json').write_text(json.dumps(dict(blender=bpy.app.version_string,objects=len(bpy.data.objects),meshes=len(bpy.data.meshes),exports=['AssetsSource/Blender/calibration.blend','AssetsSource/Blender/calibration.glb','Project/Assets/Studio/Models/Calibration.fbx'],purpose='Toolchain calibration fixture, not game artwork acceptance'),indent=2),encoding='utf-8')
