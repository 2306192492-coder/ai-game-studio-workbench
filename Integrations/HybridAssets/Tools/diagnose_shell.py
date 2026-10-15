import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent.parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(root/'Generated/shell-mini-v1/shell-component.glb'))
o=bpy.context.object;bpy.context.view_layer.objects.active=o
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
o.data.validate();o.data.update()
o.scale=Vector((.23,.23,.23));bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
out=root/'Evidence/shell-diagnostic';out.mkdir(exist_ok=True)
def state(name):
 print(name,len(o.data.vertices),len(o.data.polygons),'tri',sum(len(p.vertices)-2 for p in o.data.polygons),flush=True)
 o.data.validate(clean_customdata=True);o.data.update();bpy.ops.export_scene.gltf(filepath=str(out/(name+'.glb')),use_selection=True)
state('import')
v=o.modifiers.new('voxel','REMESH');v.mode='VOXEL';v.voxel_size=.0045;v.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=v.name);state('voxel')
s=o.modifiers.new('smooth','SMOOTH');s.factor=.6;s.iterations=3;bpy.ops.object.modifier_apply(modifier=s.name);state('smooth')
d=o.modifiers.new('dec','DECIMATE');d.ratio=.6;d.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=d.name);state('decimate')
