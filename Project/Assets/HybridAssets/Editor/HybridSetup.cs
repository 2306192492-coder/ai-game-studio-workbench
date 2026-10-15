using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AIStudio.Hybrid {
public static class HybridSetup {
 public const string ScenePath="Assets/HybridAssets/HybridAssetLab.unity";
 public static string Root=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../Integrations/HybridAssets"));
 const string FabRoot="Assets/Harbor Props Pack vol.1/";const string Dest="Assets/HybridAssets/";
 static Material Mat(string name,Color color,float metal=0){string p=Dest+"Materials/"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(p);if(!m){m=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(m,p);}m.color=color;m.SetFloat("_Metallic",metal);m.SetFloat("_Smoothness",.3f);return m;}
 static GameObject Cube(string name,Vector3 pos,Vector3 scale,Material mat){var g=GameObject.CreatePrimitive(PrimitiveType.Cube);g.name=name;g.transform.position=pos;g.transform.localScale=scale;g.GetComponent<Renderer>().sharedMaterial=mat;return g;}
 static Bounds Bounds(GameObject g){var rs=g.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs.Skip(1))b.Encapsulate(r.bounds);return b;}
 static void Text(string s,Vector3 pos,float size,Color color){var g=new GameObject(s);g.transform.position=pos;var tm=g.AddComponent<TextMesh>();tm.text=s;tm.anchor=TextAnchor.MiddleCenter;tm.fontSize=80;tm.characterSize=size;tm.color=color;}
 [Serializable] class ModelCheck{public string asset,dimensions;public int triangles,vertices;public bool uv,materialsSupported;}
 [Serializable] class Report{public string unity,scope;public List<ModelCheck> assets=new List<ModelCheck>();public bool passed;}
 public static string Create(){
  Directory.CreateDirectory(Dest+"Materials");AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
  foreach(var id in AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset")){var p=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(id));var so=new SerializedObject(p);var gpu=so.FindProperty("m_GPUResidentDrawerMode");if(gpu!=null&&gpu.intValue!=0)throw new Exception("Use the existing verified non-GPU-resident configuration");}
  var report=new Report{unity=Application.unityVersion,scope="New Fab art and original prototype only; private isolated scene; legacy scenes and build list preserved"};
  foreach(string file in Directory.GetFiles(FabRoot+"Models","*.fbx").Concat(new[]{Dest+"Models/ShellLamp.fbx"})){
   var imp=(ModelImporter)AssetImporter.GetAtPath(file);imp.isReadable=true;imp.importAnimation=false;imp.SaveAndReimport();var source=AssetDatabase.LoadAssetAtPath<GameObject>(file);if(!source)throw new Exception("Import failed "+file);var ms=source.GetComponentsInChildren<MeshFilter>().Select(x=>x.sharedMesh).ToArray();report.assets.Add(new ModelCheck{asset=file,triangles=ms.Sum(m=>m.triangles.Length/3),vertices=ms.Sum(m=>m.vertexCount),uv=ms.All(m=>m.uv.Length==m.vertexCount),dimensions=Bounds(source).size.ToString("F4"),materialsSupported=source.GetComponentsInChildren<Renderer>().All(r=>r.sharedMaterials.All(m=>m&&m.shader&&m.shader.isSupported&&m.shader.name.StartsWith("Universal Render Pipeline/")))});
  }
  var previous=SceneManager.GetActiveScene();var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);SceneManager.SetActiveScene(scene);
  var stage=Mat("Stage",new Color(.055f,.10f,.115f));var rim=Mat("Rim",new Color(.35f,.48f,.46f),.65f);var deck=Mat("Display",new Color(.14f,.20f,.215f));
  Cube("Floor",new Vector3(0,-.16f,0),new Vector3(10,.3f,5.7f),stage);Cube("RearWall",new Vector3(0,1.7f,2.3f),new Vector3(10,3.5f,.12f),stage);
  var props=new List<GameObject>();var names=new[]{"anchor","bollard","chain","chain_hook","mooring_cleat","rope","ships_searchlights","single_post","linked_posts"};
  for(int i=0;i<names.Length;i++){
   var source=AssetDatabase.LoadAssetAtPath<GameObject>(FabRoot+"Prefabs/"+names[i]+".prefab");var g=(GameObject)PrefabUtility.InstantiatePrefab(source,scene);g.name="Fab_"+names[i];float x=-3.6f+(i%3)*1.55f,z=-1.3f+(i/3)*1.2f;var b=Bounds(g);g.transform.localScale*=.8f/Mathf.Max(b.size.x,Mathf.Max(b.size.y,b.size.z));b=Bounds(g);g.transform.position+=new Vector3(x-b.center.x,.16f-b.min.y,z-b.center.z);props.Add(g);
   Cube("Plinth_"+names[i],new Vector3(x,.075f,z),new Vector3(1.15f,.15f,.9f),deck);Text(names[i].Replace('_',' '),new Vector3(x,.18f,z-.48f),.013f,new Color(.72f,.85f,.82f));
   foreach(var r in g.GetComponentsInChildren<Renderer>())foreach(var m in r.sharedMaterials)if(!m||!m.shader.isSupported||m.shader.name!="Universal Render Pipeline/Lit")throw new Exception("Fab URP material failed "+names[i]);
  }
  var original=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(Dest+"Models/ShellLamp.fbx"));original.name="Original_ShellLamp";original.transform.position=new Vector3(2.9f,.76f,0);original.transform.localScale=Vector3.one*1.5f;original.transform.rotation=Quaternion.Euler(0,180,0);
  var ceramic=Mat("SeafoamCeramic",Color.white);ceramic.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Dest+"Textures/shell-glaze.png"));ceramic.SetFloat("_Smoothness",.64f);
  var brass=Mat("BrushedBrass",new Color(.72f,.48f,.16f),.86f);var marine=Mat("DeepMarine",new Color(.055f,.13f,.14f),.4f);var glow=Mat("WarmDiffuser",new Color(.98f,.79f,.42f));glow.EnableKeyword("_EMISSION");glow.SetColor("_EmissionColor",new Color(1,.55f,.16f)*1.2f);
  var ivory=Mat("IvorySpiral",new Color(.82f,.75f,.57f));foreach(var r in original.GetComponentsInChildren<Renderer>())r.sharedMaterial=r.name=="Shell_Ceramic"?ceramic:r.name.Contains("Brass")?brass:r.name=="Luminous_Band"?glow:r.name=="Ivory_Spiral"?ivory:marine;
  var ob=Bounds(original);var bc=original.AddComponent<BoxCollider>();bc.center=original.transform.InverseTransformPoint(ob.center);bc.size=ob.size/1.5f;
  Cube("OriginalPlinth",new Vector3(2.9f,.36f,0),new Vector3(1.65f,.72f,1.5f),deck);Cube("OriginalRim",new Vector3(2.9f,.738f,0),new Vector3(1.7f,.035f,1.55f),rim);
  Text("ASSET WORKSHOP",new Vector3(.1f,2.9f,2.16f),.075f,new Color(.74f,.89f,.85f));Text("FAB  /  READY-MADE PROPS",new Vector3(-2,2.35f,2.15f),.023f,new Color(.76f,.85f,.83f));Text("ORIGINAL  /  SHELL LAMP",new Vector3(2.9f,1.8f,.5f),.022f,new Color(.76f,.85f,.83f));Text("GPT > HUNYUAN3D-2 > BLENDER",new Vector3(2.9f,1.58f,.5f),.013f,new Color(.76f,.85f,.83f));Text("PRIVATE LOCAL VALIDATION",new Vector3(.1f,.42f,-2.4f),.018f,new Color(.59f,.76f,.74f));
  RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.4f,.43f,.46f);RenderSettings.skybox=null;
  var sun=new GameObject("Key").AddComponent<Light>();sun.type=LightType.Directional;sun.intensity=2.1f;sun.shadows=LightShadows.Soft;sun.transform.rotation=Quaternion.Euler(46,-28,0);
  var fill=new GameObject("CoolFill").AddComponent<Light>();fill.type=LightType.Point;fill.range=12;fill.intensity=18;fill.color=new Color(.45f,.76f,1);fill.transform.position=new Vector3(-3,3,-2);
  var camera=new GameObject("LabCamera").AddComponent<Camera>();camera.tag="MainCamera";camera.transform.position=new Vector3(2.5f,4.6f,-11.3f);camera.transform.LookAt(new Vector3(0,.95f,0));camera.fieldOfView=43;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.052f,.065f);camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;camera.gameObject.AddComponent<AudioListener>();
  var profile=ScriptableObject.CreateInstance<VolumeProfile>();profile.Add<Tonemapping>().mode.Override(TonemappingMode.ACES);var vp=Dest+"LabGrade.asset";var existing=AssetDatabase.LoadAssetAtPath<VolumeProfile>(vp);if(existing){UnityEngine.Object.DestroyImmediate(profile);profile=existing;}else AssetDatabase.CreateAsset(profile,vp);var volume=new GameObject("Grade").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=profile;
  var probe=new GameObject("HybridProbe").AddComponent<HybridProbe>();probe.captureCamera=camera;probe.originalProp=original;probe.matureProps=props.ToArray();
  EditorSceneManager.SaveScene(scene,ScenePath);EditorSceneManager.CloseScene(scene,true);SceneManager.SetActiveScene(previous);AssetDatabase.SaveAssets();report.passed=report.assets.Count==9&&report.assets.All(a=>a.uv&&a.triangles>0);File.WriteAllText(Path.Combine(Root,"Evidence","unity-import-report.json"),JsonUtility.ToJson(report,true));if(!report.passed)throw new Exception("Import gates failed");return "Saved separate hybrid scene; 8 mature meshes / 9 prefabs + original prop imported";
 }
 public static string Build(){var oldPreloaded=PlayerSettings.GetPreloadedAssets();HybridReleaseGuard.LocalValidation=true;try{Directory.CreateDirectory(Path.Combine(Root,"Builds/Windows"));var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},target=BuildTarget.StandaloneWindows64,locationPathName=Path.Combine(Root,"Builds/Windows/HybridAssetLab.exe"),options=BuildOptions.Development});var s=report.summary;File.WriteAllText(Path.Combine(Root,"Evidence/build-report.json"),JsonUtility.ToJson(new BuildRecord{result=s.result.ToString(),errors=s.totalErrors,warnings=s.totalWarnings,bytes=s.totalSize,scope="Private local validation only"},true));if(s.result!=BuildResult.Succeeded)throw new Exception("Hybrid build failed");return s.result.ToString();}finally{HybridReleaseGuard.LocalValidation=false;PlayerSettings.SetPreloadedAssets(oldPreloaded);}}
 [Serializable]class BuildRecord{public string result,scope;public int errors,warnings;public ulong bytes;}
}
public class HybridReleaseGuard:IProcessSceneWithReport {
 public static bool LocalValidation;public int callbackOrder=>-200;
 public void OnProcessScene(Scene scene,BuildReport report){if(report!=null&&!LocalValidation)CheckScene(scene);}
 public static void CheckScene(Scene scene){var paths=scene.GetRootGameObjects().SelectMany(g=>g.GetComponentsInChildren<MeshFilter>(true)).Where(m=>m.sharedMesh).Select(m=>AssetDatabase.GetAssetPath(m.sharedMesh));if(paths.Contains("Assets/HybridAssets/Models/ShellLamp.fbx"))throw new BuildFailedException("Hunyuan-derived shell carries EU/UK/South Korea territory restrictions. Use HybridSetup.Build for private local validation; public release requires cleared scope and written review.");}
}}
