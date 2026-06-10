import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Data.utils import *
from Data.Database_access.loadFromDb import *
import Data.KDtree as KDtree

def generateSearchLibrary(labels,filename):
    library = {}  # substring -> list of original strings
    for s in labels:
        for start in range(len(s)):
            for end in range(start, len(s)):
                substring = s[start:end+1]
                library.setdefault(substring, set()).add(s)
    serializable_library = {k: list(v) for k, v in library.items()}
    savePointsDataToFile(serializable_library,filename)

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
    # main("Data/ObbyMap32_pruned.json","Data/LabeledPoints.json")
    
    labels = fetch_building_names("llyn_bygning_dtu")
    labels = [label for _,label in labels]
    generateSearchLibrary(labels,"Data/SearchLibrary.json")
    pass