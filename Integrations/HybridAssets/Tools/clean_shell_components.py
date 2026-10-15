"""Prop-specific cleanup: retain largest connected shell, preserve untouched raw output."""
import sys,json,numpy as np,trimesh
from pathlib import Path
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
raw,out=map(Path,sys.argv[1:3]);mesh=trimesh.load(raw,force='mesh',process=False)
f=mesh.faces; edges=np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]))
graph=coo_matrix((np.ones(len(edges),dtype=bool),(edges[:,0],edges[:,1])),shape=(len(mesh.vertices),)*2).tocsr()
n,labels=connected_components(graph,directed=False)
counts=np.bincount(labels[f[:,0]],minlength=n);largest=int(counts.argmax())
keep=labels[f[:,0]]==largest;clean=mesh.submesh([np.where(keep)[0]],append=True,repair=False)
clean.export(out)
report={'scope':'Single solid sculpture only; not a generic assembly cleanup','components':int(n),'input_triangles':len(f),'retained_triangles':len(clean.faces),'retained_bounds':clean.bounds.tolist(),'discarded_components':'Detached floating reconstruction artifacts; raw preserved','watertight':bool(clean.is_watertight),'release_approval':False}
out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
