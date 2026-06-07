import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Data.utils import *
from Data.Database_access.loadFromDb import *
import Data.KDtree as KDtree

def assignPointsData(tree,data):
    labeled = {}
    for p,d in data:
        hits = KDtree.KNN_KDtree(tree,p,5)
        labeled[d] = []
        while True:
            hit = hits.extractMax()
            if hit is None: break
            _,p = hit
            labeled.get(d).append(p)
    return labeled

def main(graphFile,labeledPointsFile):
    adjacencyList,_ = load_adjacency_list(graphFile)
    points = adjacencyList.keys()
    labels = fetch_building_names("llyn_bygning_dtu")
    tree = KDtree.buildKDtree(points)
    labeledpoints = assignPointsData(tree,labels)
    for x in labeledpoints.items():
        print(x)
    savePointsDataToFile(labeledpoints,labeledPointsFile)

if __name__ == "__main__":
    main("Data/ObbyMap32_pruned.json","Data/LabeledPoints.json")
    pass