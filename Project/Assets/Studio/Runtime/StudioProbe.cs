using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

namespace AIStudio
{
    public class StudioProbe : MonoBehaviour
    {
        public Animator character;
        public Rigidbody physicsProbe;
        public Camera captureCamera;
        public Texture2D generatedTexture;
        public string status = "AI STUDIO / LOCAL TOOLCHAIN";
        [Serializable] public class Result
        {
            public string utc, unity, device, renderPipeline, scope, imageProvider, textureName;
            public int textureWidth, textureHeight;
            public bool passed, animationAdvanced, skinnedMeshDeformed, physicsSettled, generatedTextureLoaded;
            public int frames, errors;
            public float duration, animationTimeDelta, deformationDelta, physicsHeight;
            public string[] screenshots, messages;
        }
        readonly List<string> errors = new List<string>();
        void Awake(){Application.runInBackground=true;Application.targetFrameRate=60;}
        IEnumerator Start()
        {
            if(!Array.Exists(Environment.GetCommandLineArgs(), x=>x=="--studio-qa")) yield break;
            AudioListener.volume=0;
            Application.logMessageReceived+=(message,stack,type)=>{if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert) errors.Add(message);};
            string destination=GetArgument("--evidence-root");
            if(string.IsNullOrWhiteSpace(destination)) destination=Path.Combine(Application.persistentDataPath,"AIStudioValidation");
            Directory.CreateDirectory(destination);
            int firstFrame=Time.frameCount;float start=Time.realtimeSinceStartup;
            yield return null;yield return null;
            var skin=character.GetComponentInChildren<SkinnedMeshRenderer>();
            var meshA=new Mesh();skin.BakeMesh(meshA);var verticesA=meshA.vertices;
            float firstAnimation=character.GetCurrentAnimatorStateInfo(0).normalizedTime;
            var shots=new List<string>();
            for(int index=0;index<3;index++)
            {
                yield return new WaitForSeconds(.23f);
                string path=Path.Combine(destination,"runtime-"+index+".png");
                Capture(captureCamera,path);shots.Add(path);
            }
            var meshB=new Mesh();skin.BakeMesh(meshB);var verticesB=meshB.vertices;
            float deformation=0;
            for(int i=0;i<Math.Min(verticesA.Length,verticesB.Length);i++)deformation=Mathf.Max(deformation,Vector3.Distance(verticesA[i],verticesB[i]));
            float delta=character.GetCurrentAnimatorStateInfo(0).normalizedTime-firstAnimation;
            yield return new WaitForSeconds(1.5f);
            var report=new Result{
                utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,device=SystemInfo.graphicsDeviceName,
                renderPipeline=GraphicsSettings.currentRenderPipeline?GraphicsSettings.currentRenderPipeline.GetType().Name:"BuiltIn",
                scope="Actual Windows player, autonomous animation/physics/rendering. No physical keyboard/mouse or manual playtest claim.",
                animationAdvanced=delta>.1f,animationTimeDelta=delta,skinnedMeshDeformed=deformation>.001f,deformationDelta=deformation,
                physicsSettled=Mathf.Abs(physicsProbe.position.y-.25f)<.09f,physicsHeight=physicsProbe.position.y,
                imageProvider="GPT built-in imagegen",textureName=generatedTexture?generatedTexture.name:"missing",textureWidth=generatedTexture?generatedTexture.width:0,textureHeight=generatedTexture?generatedTexture.height:0,
                generatedTextureLoaded=generatedTexture && generatedTexture.name=="GPT-primary-landscape" && generatedTexture.width==1254 && generatedTexture.height==1254,
                frames=Time.frameCount-firstFrame,duration=Time.realtimeSinceStartup-start,errors=errors.Count,screenshots=shots.ToArray(),messages=errors.ToArray()
            };
            report.passed=report.animationAdvanced&&report.skinnedMeshDeformed&&report.physicsSettled&&report.generatedTextureLoaded&&report.errors==0&&report.frames>30;
            File.WriteAllText(Path.Combine(destination,"runtime-verdict.json"),JsonUtility.ToJson(report,true));
            Destroy(meshA);Destroy(meshB);Application.Quit(report.passed?0:2);
        }
        static string GetArgument(string key){var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,key);return i>=0&&i+1<args.Length?args[i+1]:null;}
        public static void Capture(Camera camera,string path)
        {
            var rt=RenderTexture.GetTemporary(1280,720,24,RenderTextureFormat.ARGB32);
            var before=camera.targetTexture;var active=RenderTexture.active;
            camera.targetTexture=rt;
            var request=new RenderPipeline.StandardRequest{destination=rt};
            if(RenderPipeline.SupportsRenderRequest(camera,request))RenderPipeline.SubmitRenderRequest(camera,request);else camera.Render();
            RenderTexture.active=rt;
            var pixels=new Texture2D(1280,720,TextureFormat.RGB24,false);
            pixels.ReadPixels(new Rect(0,0,1280,720),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());
            camera.targetTexture=before;RenderTexture.active=active;RenderTexture.ReleaseTemporary(rt);DestroyImmediate(pixels);
        }
    }
}
