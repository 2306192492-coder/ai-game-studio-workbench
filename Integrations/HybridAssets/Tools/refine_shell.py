"""Original shell lamp prototype: geometry repair, UVs, authored finish and connected base."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parent.parent
source=root/'Generated/shell-mini-v1/shell-component.glb';out=root/'Generated/shell-refined-v3';out.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
body=next(o for o in bpy.context.scene.objects if o.type=='MESH');body.name='Shell_Ceramic'
bpy.context.view_layer.objects.active=body;body.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
points=[body.matrix_world@Vector(c) for c in body.bound_box];lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)))
factor=.42/(hi.x-lo.x)
for v in body.data.vertices:v.co=(v.co-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z)))*factor+Vector((0,0,.083))
body.location=(0,0,0)
body.data.validate(clean_customdata=True);body.data.update();bpy.context.view_layer.update()
# Rebuild an ordered closed outer envelope instead of collapsing a densely folded raw field.
# This prop is a solid star-shaped sculpture, so radial retopology is appropriate here.
# It is deliberately not a generic character or multi-part asset operation.
bvh=BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons],all_triangles=True)
center=Vector((-.045,0,.24))
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5,radius=1);retopo=bpy.context.object;misses=0
for v in retopo.data.vertices:
 direction=v.co.normalized();hit,normal,index,distance=bvh.ray_cast(center+direction*2,-direction,2.5)
 if hit is None:
  misses+=1;hit=bvh.find_nearest(center+direction*.16)[0]
 v.co=hit
print('Radial envelope missed rays',misses,'of',len(retopo.data.vertices),flush=True)
if misses/len(retopo.data.vertices)>.05:raise RuntimeError('Source is not sufficiently star-shaped for this repair')
newmesh=retopo.data.copy();bpy.data.objects.remove(retopo,do_unlink=True);body.data=newmesh
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
smooth=body.modifiers.new('Envelope surface refinement','SMOOTH');smooth.factor=.6;smooth.iterations=3;bpy.ops.object.modifier_apply(modifier=smooth.name)
body.data.validate(clean_customdata=True);body.data.update()
def mat(name,color,metal=0,rough=.3):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
ceramic=mat('SeafoamCeramic',(.12,.52,.47),rough=.24)
body.data.materials.clear();body.data.materials.append(ceramic)
ivory=mat('IvorySpiral',(.82,.73,.52),rough=.29)
# Restore the GPT design's ivory spiral as authored geometry, seated on the rebuilt surface.
surface=BVHTree.FromPolygons([v.co.copy() for v in body.data.vertices],[tuple(p.vertices) for p in body.data.polygons],all_triangles=True)
curve=bpy.data.curves.new('Ivory spiral relief','CURVE');curve.dimensions='3D';curve.bevel_depth=.0018;curve.bevel_resolution=2
path=curve.splines.new('POLY');path.points.add(239)
for i,p in enumerate(path.points):
 t=i/239*math.pi*4.3;r=.006+.0093*t;x=-.065+r*math.cos(t);z=.242+r*math.sin(t)
 hit,normal,index,distance=surface.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)
 if hit is None:raise RuntimeError('Spiral relief misses surface')
 p.co=(hit.x,hit.y-.0011,hit.z,1)
spiral=bpy.data.objects.new('Ivory_Spiral',curve);bpy.context.collection.objects.link(spiral);spiral.data.materials.append(ivory)
bpy.ops.object.select_all(action='DESELECT');spiral.select_set(True);bpy.context.view_layer.objects.active=spiral;bpy.ops.object.convert(target='MESH')
brass=mat('BrushedBrass',(.61,.37,.095),metal=.85,rough=.28)
dark=mat('DeepMarine',(.035,.085,.092),metal=.35,rough=.3)
diffuser=mat('WarmDiffuser',(.95,.71,.30),rough=.38)
bs=diffuser.node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.55,.16,1);bs.inputs['Emission Strength'].default_value=.9
def cylinder(name,radius,depth,z,material):
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,location=(0,0,z));o=bpy.context.object;o.name=name;o.data.materials.append(material)
 bevel=o.modifiers.new('Rounded machined rim','BEVEL');bevel.width=.003;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name);return o
cylinder('Brass_Base',.13,.018,.009,brass)
cylinder('Luminous_Band',.116,.02,.028,diffuser)
cylinder('Marine_Foot',.116,.042,.059,dark)
cylinder('Brass_Saddle',.10,.018,.080,brass)
for obj in list(bpy.context.scene.objects):
 if obj.type!='MESH':continue
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 for p in obj.data.polygons:p.use_smooth=True
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
# Bake authored subtle glaze variation to a portable image; GPT remains the original design source.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
nodes=ceramic.node_tree.nodes;links=ceramic.node_tree.links;bs=nodes.get('Principled BSDF');output=nodes.get('Material Output')
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=75;noise.inputs['Detail'].default_value=2
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.085,.44,.40,1);ramp.color_ramp.elements[1].color=(.145,.56,.505,1);links.new(noise.outputs['Fac'],ramp.inputs[0])
emit=nodes.new('ShaderNodeEmission');links.new(ramp.outputs['Color'],emit.inputs['Color']);links.new(emit.outputs[0],output.inputs[0])
img=bpy.data.images.new('shell-glaze',1024,1024);tex=nodes.new('ShaderNodeTexImage');tex.image=img;nodes.active=tex
bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=1;bpy.context.scene.cycles.device='CPU';bpy.ops.object.bake(type='EMIT',margin=8)
img.filepath_raw=str(out/'shell-glaze.png');img.file_format='PNG';img.save();links.new(bs.outputs[0],output.inputs[0]);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
bpy.ops.object.select_all(action='SELECT');bpy.ops.wm.save_as_mainfile(filepath=str(out/'ShellLamp.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'ShellLamp.glb'),export_format='GLB',use_selection=True,export_yup=True)
bpy.ops.export_scene.fbx(filepath=str(out/'ShellLamp.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False)
report={'raw_component_triangles':1892618,'method':'ordered radial outer-envelope retopology of Hunyuan source; GPT-referenced authored ivory spiral relief; private local prototype','shell_triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'total_triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH'),'width_m':.42,'materials':'Authored ceramic, brass, dark marine foot, ivory, luminous band; GPT colors are reference, not automated Hunyuan texture','uv':'Smart UV and Blender baked ceramic variation','license_holds':['EU','UK','South Korea'],'stage':'refined local prototype pending import and visual review'}
(out/'refinement.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
