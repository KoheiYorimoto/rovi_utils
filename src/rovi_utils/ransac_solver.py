#!/usr/bin/python

import numpy as np
import open3d as o3
import copy
import time

Param={
  "normal_max_nn":20,
  "normal_radius":0.01,
  "feature_max_nn":200,
  "feature_radius":0.025,
  'distance_threshold':0.001,
  'icp_threshold':0.0015
}

modFtArray=[]
modPcArray=[]
scnFtArray=[]
scnPcArray=[]

def toNumpy(pcd):
  return np.reshape(np.asarray(pcd.points),(-1,3))

def fromNumpy(dat):
  d=dat.astype(np.float32)
  pc=o3.geometry.PointCloud()
  pc.points=o3.utility.Vector3dVector(d)
  return pc

def _get_features(cloud):
  cloud.estimate_normals(o3.geometry.KDTreeSearchParamHybrid(radius=Param["normal_radius"],max_nn=Param["normal_max_nn"]))
  return o3.registration.compute_fpfh_feature(cloud, o3.geometry.KDTreeSearchParamHybrid(radius=Param["feature_radius"],max_nn=Param["feature_max_nn"]))

def learn(datArray,prm):
  global modFtArray,modPcArray,Param
  Param.update(prm)
  modFtArray=[]
  modPcArray=[]
  for dat in datArray:
    pc=fromNumpy(dat)
    modPcArray.append(pc)
    modFtArray.append(_get_features(pc))
  return

def solve(datArray,prm):
  global scnFtArray,scnPcArray,Param
  Param.update(prm)
  scnFtArray=[]
  scnPcArray=[]
  for dat in datArray:
    pc=fromNumpy(dat)
    scnPcArray.append(pc)
    scnFtArray.append(_get_features(pc))
  t1=time.time()
  resft=o3.registration.registration_ransac_based_on_feature_matching(
    modPcArray[0],scnPcArray[0],modFtArray[0],scnFtArray[0],
    Param["distance_threshold"],o3.registration.TransformationEstimationPointToPoint(False),4,
    [o3.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
    o3.registration.CorrespondenceCheckerBasedOnDistance(Param["distance_threshold"])],
    o3.registration.RANSACConvergenceCriteria(2000000, 500))
  print "time for feature matching",time.time()-t1
  print "feature matching\n",resft.transformation,resft.fitness
  resicp=o3.registration.registration_icp(
    modPcArray[0],scnPcArray[0],
    Param["icp_threshold"],
    resft.transformation,o3.registration.TransformationEstimationPointToPlane())
  return {"transform":[resicp.transformation],"fitness":[resicp.fitness],"rmse":[resicp.inlier_rmse]}        

if __name__ == '__main__':
  print "Prepare model"
  model=o3.io.read_point_cloud("../data/model.ply")
  learn([toNumpy(model)],{})
  scene=o3.io.read_point_cloud("../data/sample.ply")
  result=solve([toNumpy(scene)],{})
  Tmat=result["transform"]
  score=result["fitness"]
  print "feature matching result",Tmat[0],score[0]

  P=copy.deepcopy(toNumpy(modPcArray[0]))
  P=np.dot(Tmat[0][:3],np.vstack((P.T,np.ones((1,len(P)))))).T
  source=fromNumpy(P)
  target=scnPcArray[0]
  source.paint_uniform_color([1, 0.706, 0])
  target.paint_uniform_color([0, 0.651, 0.929])
  o3.visualization.draw_geometries([source, target])
