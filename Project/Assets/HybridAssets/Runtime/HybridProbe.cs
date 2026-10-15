using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

namespace AIStudio.Hybrid {
public class HybridProbe:MonoBehaviour {
 public Camera captureCamera; public GameObject originalProp; public GameObject[] matureProps;
 readonly List<string> errors=new List<string>(); bool qa; Vector3 target=new Vector3(0,.8f,0); float yaw=12,pitch=27,distance=12;
 [Serializable] public class Result {public string scope,unity,pipeline,device;public bool passed,originalUV,originalTexture,materialsSupported,collisionHit; public int matureProps,renderers,triangles,errors;public string[] messages,screenshots;}
 void Awake(){Application.runInBackground=true;Application.targetFrameRate=60;qa=Environment.GetCommandLineArgs().Contains("--hybrid-qa");Application.logMessageReceived+=(m,s,t)=>{if(t==LogType.Error||t==LogType.Exception||t==LogType.Assert)errors.Add(m);};}
 void Update(){if(qa)return; var mouse=Mouse.current;if(mouse!=null){if(mouse.rightButton.isPressed){var d=mouse.delta.ReadValue();yaw+=d.x*.16f;pitch=Mathf.Clamp(pitch-d.y*.16f,8,70);}distance=Mathf.Clamp(distance-mouse.scroll.ReadValue().y*.005f,4,18);}if(Keyboard.current?.escapeKey.wasPressedThisFrame==true)Application.Quit();captureCamera.transform.position=target+Quaternion.Euler(pitch,yaw,0)*new Vector3(0,0,-distance);captureCamera.transform.LookAt(target);}
 IEnumerator Start(){if(!qa)yield break;AudioListener.volume=0;var args=Environment.GetCommandLineArgs();int ix=Array.IndexOf(args,"--evidence-root");string root=ix>=0?args[ix+1]:Path.Combine(Application.persistentDataPath,"HybridQA");Directory.CreateDirectory(root);yield return new WaitForSeconds(1);
  var r=new Result{scope="Private local Windows URP static asset import/material/UV/collision/render proof. Not a game acceptance or redistribution approval.",unity=Application.unityVersion,pipeline=GraphicsSettings.currentRenderPipeline?.GetType().Name,device=SystemInfo.graphicsDeviceName,matureProps=matureProps.Length};
  var all=matureProps.Concat(new[]{originalProp}).SelectMany(g=>g.GetComponentsInChildren<Renderer>()).ToArray();r.renderers=all.Length;r.materialsSupported=all.All(x=>x.sharedMaterials.All(m=>m&&m.shader&&m.shader.isSupported&&m.shader.name.StartsWith("Universal Render Pipeline/")));
  // Index metadata remains available after static batching; CPU triangle arrays do not.
  foreach(var mesh in matureProps.Concat(new[]{originalProp}).SelectMany(g=>g.GetComponentsInChildren<MeshFilter>()).Select(m=>m.sharedMesh).Distinct())for(int s=0;s<mesh.subMeshCount;s++)r.triangles+=(int)mesh.GetIndexCount(s)/3;
  var shell=originalProp.GetComponentsInChildren<MeshFilter>().First(x=>x.name=="Shell_Ceramic");r.originalUV=shell.sharedMesh.uv.Length==shell.sharedMesh.vertexCount;r.originalTexture=shell.GetComponent<Renderer>().sharedMaterial.GetTexture("_BaseMap")!=null;
  Physics.SyncTransforms();var collider=originalProp.GetComponent<BoxCollider>();r.collisionHit=collider&&collider.Raycast(new Ray(collider.bounds.center+Vector3.back*3,Vector3.forward),out var hit,6);
  var shots=new List<string>();AIStudio.StudioProbe.Capture(captureCamera,Path.Combine(root,"hybrid-overview.png"));shots.Add("hybrid-overview.png");
  captureCamera.transform.position=new Vector3(3.4f,1.45f,-2.1f);captureCamera.transform.LookAt(new Vector3(2.9f,1.10f,0));yield return new WaitForSeconds(.2f);AIStudio.StudioProbe.Capture(captureCamera,Path.Combine(root,"original-closeup.png"));shots.Add("original-closeup.png");
  captureCamera.transform.position=new Vector3(-3.3f,2.7f,-4.2f);captureCamera.transform.LookAt(new Vector3(-1.5f,.5f,0));yield return new WaitForSeconds(.2f);AIStudio.StudioProbe.Capture(captureCamera,Path.Combine(root,"fab-closeup.png"));shots.Add("fab-closeup.png");
  r.errors=errors.Count;r.messages=errors.ToArray();r.screenshots=shots.ToArray();r.passed=r.matureProps==9&&r.renderers>=14&&r.materialsSupported&&r.originalUV&&r.originalTexture&&r.collisionHit&&r.errors==0&&r.pipeline=="UniversalRenderPipelineAsset";File.WriteAllText(Path.Combine(root,"runtime-verdict.json"),JsonUtility.ToJson(r,true));Application.Quit(r.passed?0:2);
 }
}}
