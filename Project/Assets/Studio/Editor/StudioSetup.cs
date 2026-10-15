using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace AIStudio
{
    public static class StudioSetup
    {
        public const string CharacterPath="Assets/ThirdParty/Mixamo/XBot-Walking.fbx";
        public const string ScenePath="Assets/Studio/StudioValidation.unity";
        public static string Root=>Directory.GetParent(Application.dataPath).Parent.FullName;
        static Material Material(string name,Color color,float metallic=0,Texture texture=null)
        {
            string path="Assets/Studio/Materials/"+name+".mat";
            var material=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!material){material=new Material(Shader.Find("Universal Render Pipeline/Lit"));AssetDatabase.CreateAsset(material,path);}
            material.color=color;material.SetFloat("_Metallic",metallic);material.SetFloat("_Smoothness",.38f);
            if(texture)material.SetTexture("_BaseMap",texture);
            return material;
        }
        static GameObject Primitive(string name,PrimitiveType type,Vector3 pos,Vector3 scale,Material material)
        {var go=GameObject.CreatePrimitive(type);go.name=name;go.transform.position=pos;go.transform.localScale=scale;go.GetComponent<Renderer>().sharedMaterial=material;return go;}
        static void Label(string text,Vector3 pos,float size,Color color)
        {var go=new GameObject(text);go.transform.position=pos;go.transform.rotation=Quaternion.identity;var tm=go.AddComponent<TextMesh>();tm.text=text;tm.fontSize=80;tm.characterSize=size;tm.anchor=TextAnchor.MiddleCenter;tm.color=color;}
        public static string Create(bool allowTransportFixture=false)
        {
            Directory.CreateDirectory("Assets/Studio/Materials");AssetDatabase.Refresh();
            // GPU Resident Drawer leaked material state on this D3D11 render-request path.
            // Keep regular SRP batching; disable only that GPU-driven submission mode.
            foreach(var id in AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset")){
                var pipeline=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(id));
                var settings=new SerializedObject(pipeline);
                var gpuDrawer=settings.FindProperty("m_GPUResidentDrawerMode");
                if(gpuDrawer!=null)gpuDrawer.intValue=0;
                settings.ApplyModifiedProperties();pipeline.useSRPBatcher=true;EditorUtility.SetDirty(pipeline);
            }
            var importer=AssetImporter.GetAtPath(CharacterPath) as ModelImporter;
            if(!importer)throw new Exception("Mixamo FBX missing");
            importer.animationType=ModelImporterAnimationType.Human;importer.avatarSetup=ModelImporterAvatarSetup.CreateFromThisModel;
            importer.importAnimation=true;importer.materialImportMode=ModelImporterMaterialImportMode.None;
            var clips=importer.defaultClipAnimations;foreach(var clip in clips){clip.loopTime=true;clip.loopPose=true;clip.lockRootPositionXZ=true;clip.lockRootHeightY=true;}
            importer.clipAnimations=clips;importer.SaveAndReimport();
            var source=AssetDatabase.LoadAssetAtPath<GameObject>(CharacterPath);
            var clipAsset=AssetDatabase.LoadAllAssetsAtPath(CharacterPath).OfType<AnimationClip>().First(c=>!c.name.StartsWith("__preview__"));
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.30f,.35f,.43f);RenderSettings.skybox=null;
            var neutral=Material("Stage",new Color(.09f,.13f,.16f));
            var ivory=Material("RobotIvory",new Color(.74f,.81f,.83f),.25f);
            var brass=Material("Brass",new Color(.74f,.40f,.10f),.72f);
            var woodPath=AssetDatabase.FindAssets("american_walnut_veneer_diffuse_1k t:Texture2D").Select(AssetDatabase.GUIDToAssetPath).FirstOrDefault();
            var wood=Material("PolyHavenWalnut",Color.white,0,AssetDatabase.LoadAssetAtPath<Texture2D>(woodPath));
            const string artPath="Assets/Studio/Textures/GPT-primary-landscape.png";
            var artImporter=AssetImporter.GetAtPath(artPath) as TextureImporter;
            if(artImporter){artImporter.npotScale=TextureImporterNPOTScale.None;artImporter.maxTextureSize=2048;artImporter.textureCompression=TextureImporterCompression.Uncompressed;artImporter.SaveAndReimport();}
            var art=AssetDatabase.LoadAssetAtPath<Texture2D>(artPath);
            if(!art&&allowTransportFixture)art=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Studio/Textures/Pipeline-preview.png");
            if(!art)throw new Exception("GPT primary generated texture missing");
            var generated=Material("GPTArtwork",Color.white,0,art);
            Primitive("Floor",PrimitiveType.Cube,new Vector3(0,-.2f,0),new Vector3(10,.4f,8),neutral);
            var robot=(GameObject)PrefabUtility.InstantiatePrefab(source);robot.name="Mixamo_XBot_Walking";robot.transform.position=new Vector3(-1.3f,0,0);robot.transform.rotation=Quaternion.Euler(0,180,0);
            foreach(var render in robot.GetComponentsInChildren<Renderer>())render.sharedMaterials=Enumerable.Repeat(ivory,render.sharedMaterials.Length).ToArray();
            var animator=robot.GetComponent<Animator>();animator.cullingMode=AnimatorCullingMode.AlwaysAnimate;animator.applyRootMotion=false;
            string controllerPath="Assets/Studio/Walking.controller";
            var controller=AssetDatabase.LoadAssetAtPath<AnimatorController>(controllerPath);
            if(!controller){controller=AnimatorController.CreateAnimatorControllerAtPath(controllerPath);var state=controller.layers[0].stateMachine.AddState("Walking");state.motion=clipAsset;controller.layers[0].stateMachine.defaultState=state;}
            animator.runtimeAnimatorController=controller;
            var propSource=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Studio/Models/Calibration.fbx");
            var prop=(GameObject)PrefabUtility.InstantiatePrefab(propSource);prop.name="Blender_Calibration";prop.transform.position=new Vector3(1.4f,0,0);
            foreach(var render in prop.GetComponentsInChildren<Renderer>())render.sharedMaterial=render.name.Contains("Walnut")?wood:brass;
            Primitive("ArtworkFrame",PrimitiveType.Cube,new Vector3(1.4f,1.6f,1.4f),new Vector3(1.94f,1.94f,.1f),brass);
            Primitive("GPT_Artwork",PrimitiveType.Quad,new Vector3(1.4f,1.6f,1.33f),new Vector3(1.82f,1.82f,1),generated);
            var cube=Primitive("PhysicsProbe",PrimitiveType.Cube,new Vector3(-2.7f,2,0),Vector3.one*.5f,brass);var body=cube.AddComponent<Rigidbody>();body.mass=1;
            var lightObj=new GameObject("KeyLight");var light=lightObj.AddComponent<Light>();light.type=LightType.Directional;light.intensity=2.1f;light.color=new Color(1,.88f,.71f);light.shadows=LightShadows.Soft;lightObj.transform.rotation=Quaternion.Euler(45,-35,0);
            var cameraObj=new GameObject("StudioCamera");cameraObj.tag="MainCamera";var camera=cameraObj.AddComponent<Camera>();cameraObj.transform.position=new Vector3(5,3.2f,-7.8f);cameraObj.transform.LookAt(new Vector3(0,.95f,.3f));camera.fieldOfView=42;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.028f,.047f,.063f);
            cameraObj.AddComponent<AudioListener>();camera.GetUniversalAdditionalCameraData().renderPostProcessing=true;
            var volume=new GameObject("StudioGrade").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=ScriptableObject.CreateInstance<VolumeProfile>();var tone=volume.sharedProfile.Add<Tonemapping>();tone.mode.Override(TonemappingMode.ACES);AssetDatabase.CreateAsset(volume.sharedProfile,AssetDatabase.GenerateUniqueAssetPath("Assets/Studio/StudioGrade.asset"));
            Label("AI STUDIO",new Vector3(0,3.1f,1.6f),.06f,new Color(.76f,.89f,.89f));
            var probe=new GameObject("StudioValidation").AddComponent<StudioProbe>();probe.character=animator;probe.captureCamera=camera;probe.physicsProbe=body;probe.generatedTexture=art;
            PlayerSettings.companyName="LocalAIStudio";PlayerSettings.productName="AIStudioValidation";PlayerSettings.runInBackground=true;PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.defaultScreenWidth=1280;PlayerSettings.defaultScreenHeight=720;PlayerSettings.SplashScreen.show=false;
            EditorSceneManager.SaveScene(scene,ScenePath);EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true)};AssetDatabase.SaveAssets();
            return "Studio scene saved; avatar valid="+animator.avatar.isValid+" human="+animator.avatar.isHuman+" clip="+clipAsset.length;
        }
        [Serializable] public class BuildResult{public string result,output,utc;public int errors,warnings;public ulong bytes;}
        public static string Build()
        {
            Directory.CreateDirectory(Path.Combine(Root,"Builds","Windows"));
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath},locationPathName=Path.Combine(Root,"Builds","Windows","AIStudioValidation.exe"),target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
            var summary=report.summary;
            var result=new BuildResult{result=summary.result.ToString(),output=summary.outputPath,utc=DateTime.UtcNow.ToString("o"),errors=summary.totalErrors,warnings=summary.totalWarnings,bytes=summary.totalSize};
            File.WriteAllText(Path.Combine(Root,"Evidence","build-verdict.json"),JsonUtility.ToJson(result,true));
            if(summary.result!=UnityEditor.Build.Reporting.BuildResult.Succeeded)throw new Exception("Windows build failed");
            return result.result;
        }
    }
}
