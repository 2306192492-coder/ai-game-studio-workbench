"""Executed by UE's embedded Python, never by the system Python interpreter."""
import json
import os
from pathlib import Path
import re
import traceback
import unreal


def run(request):
    checks = []

    def check(name, condition, detail=''):
        checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
        if not condition:
            raise RuntimeError(name + ': ' + detail)

    report = {'runId': request['runId'], 'action': request['action'],
              'passed': False, 'checks': checks, 'engineVersion': unreal.SystemLibrary.get_engine_version(),
              'scope': 'Editor asset/map data under NullRHI; no rendering or gameplay acceptance'}
    try:
        project_dir = Path(unreal.Paths.project_dir()).resolve()
        check('correct-project', project_dir == Path(request['project']).resolve().parent)
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        if request['action'] == 'import':
            destination = request['destination']
            name = re.sub(r'[^A-Za-z0-9_]', '_', Path(request['source']).stem)
            existing = assets.list_assets(destination, recursive=True)
            check('destination-name-unused', not any(p.rsplit('/', 1)[-1].split('.')[0].casefold() == name.casefold() for p in existing), name)
            task = unreal.AssetImportTask()
            task.set_editor_property('filename', request['source'])
            task.set_editor_property('destination_path', destination)
            task.set_editor_property('destination_name', name)
            task.set_editor_property('automated', True)
            task.set_editor_property('replace_existing', False)
            task.set_editor_property('save', True)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            paths = list(task.get_editor_property('imported_object_paths'))
            check('assets-imported', bool(paths))
            for path in paths:
                check('imported-asset-loads', assets.load_asset(path) is not None, path)
            report['imported'] = paths
        else:
            map_path = request['map']
            exists = assets.does_asset_exist(map_path)
            if request['action'] == 'prepare' and not exists:
                check('new-map-created', levels.new_level(map_path))
                cube = assets.load_asset('/Engine/BasicShapes/Cube.Cube')
                check('engine-cube-loaded', cube is not None)

                def mesh(label, position, scale):
                    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*position))
                    actor.set_actor_label(label)
                    actor.static_mesh_component.set_static_mesh(cube)
                    actor.set_actor_scale3d(unreal.Vector(*scale))
                    return actor

                mesh('AIStudio_Floor', (0, 0, -50), (12, 12, 1))
                mesh('AIStudio_Cube', (0, 0, 75), (1.5, 1.5, 1.5))
                light = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500))
                light.set_actor_label('AIStudio_KeyLight')
                light.set_actor_rotation(unreal.Rotator(-45, 45, 0), False)
                camera = actors.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(-800, -800, 550))
                camera.set_actor_label('AIStudio_Camera')
                camera.set_actor_rotation(unreal.Rotator(-20, 45, 0), False)
                start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, -300, 120))
                start.set_actor_label('AIStudio_PlayerStart')
                check('map-saved', levels.save_current_level())
                report['created'] = True
            else:
                check('map-present', exists, 'Run prepare first; no existing map will be replaced')
                report['created'] = False
            # Reload saved data instead of trusting the newly created in-memory objects.
            check('saved-map-loads', levels.load_level(map_path))
            by_label = {actor.get_actor_label(): actor for actor in actors.get_all_level_actors()}
            for name in ('AIStudio_Floor', 'AIStudio_Cube', 'AIStudio_KeyLight',
                         'AIStudio_Camera', 'AIStudio_PlayerStart'):
                check('actor-present-' + name, name in by_label)
            cube_actor = by_label['AIStudio_Cube']
            check('cube-static-mesh-bound', cube_actor.static_mesh_component.static_mesh is not None)
            check('cube-scale-persisted', abs(cube_actor.get_actor_scale3d().x - 1.5) < 0.001)
            report['actorCount'] = len(by_label)
            report['map'] = map_path
        report['passed'] = all(c['passed'] for c in checks)
    except Exception:
        report['error'] = traceback.format_exc()
        unreal.log_error(report['error'])
    Path(request['report']).write_text(json.dumps(report, indent=2), encoding='utf8')
    if not report['passed']:
        raise RuntimeError('AIStudio UE task failed; see editor-report.json')


request_path = os.environ.get('AISTUDIO_UE_REQUEST')
if not request_path:
    raise RuntimeError('Run this script through Tools/unreal_adapter.py')
run(json.loads(Path(request_path).read_text(encoding='utf-8-sig')))
