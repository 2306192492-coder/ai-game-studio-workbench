// Invoke Unity's own Package Manager service for the explicitly approved free product.
var assembly=typeof(UnityEditor.Editor).Assembly;
var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.FlattenHierarchy;
var container=assembly.GetType("UnityEditor.PackageManager.UI.Internal.ServicesContainer");
var managerType=assembly.GetType("UnityEditor.PackageManager.UI.Internal.AssetStoreDownloadManager");
var instance=container.GetProperty("instance",flags).GetValue(null);
var resolve=container.GetMethods().First(m=>m.Name=="Resolve"&&m.IsGenericMethodDefinition&&m.GetParameters().Length==0);
var manager=resolve.MakeGenericMethod(managerType).Invoke(instance,null);
var download=managerType.GetMethod("Download",new[]{typeof(System.Collections.Generic.IEnumerable<long>)});
return new {productId=372864L,accepted=download.Invoke(manager,new object[]{new long[]{372864L}})};
