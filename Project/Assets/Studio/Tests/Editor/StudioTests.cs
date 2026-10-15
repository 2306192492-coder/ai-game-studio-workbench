using System.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
namespace AIStudio.Tests
{
 public class StudioTests
 {
  [SetUp]public void LoadScene(){EditorSceneManager.OpenScene(StudioSetup.ScenePath);}
  [Test]public void UsesURP(){Assert.That(GraphicsSettings.currentRenderPipeline.GetType().Name,Does.Contain("Universal"));}
  [Test]public void MixamoHasValidHumanoidAndAnimation(){var a=GameObject.Find("Mixamo_XBot_Walking").GetComponent<Animator>();Assert.That(a.avatar.isValid&&a.avatar.isHuman);Assert.That(a.runtimeAnimatorController.animationClips.Any(c=>c.length>.5f));}
  [Test]public void BlenderExportHasImportedMeshes(){var go=GameObject.Find("Blender_Calibration");Assert.That(go.GetComponentsInChildren<MeshFilter>().Sum(m=>m.sharedMesh.vertexCount),Is.GreaterThan(500));}
  [Test]public void GPTPrimaryImageIsImportedAndBound(){var image=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Studio/Textures/GPT-primary-landscape.png");Assert.That(image,Is.Not.Null);Assert.That(image.width,Is.EqualTo(1254));Assert.That(image.height,Is.EqualTo(1254));Assert.That(GameObject.Find("GPT_Artwork").GetComponent<Renderer>().sharedMaterial.GetTexture("_BaseMap"),Is.SameAs(image));}
  [Test]public void PolyHavenMaterialHasTexture(){var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/Studio/Materials/PolyHavenWalnut.mat");Assert.That(material.GetTexture("_BaseMap"),Is.Not.Null);}
  [Test]public void RenderersHaveSupportedMaterials(){foreach(var r in Object.FindObjectsByType<Renderer>())foreach(var m in r.sharedMaterials){Assert.That(m,Is.Not.Null);Assert.That(m.shader.isSupported,Is.True,m.name);}}
 }
}
