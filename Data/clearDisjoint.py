
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Data.utils import *
from Data.Database_access.loadFromDb import *
from Data.BuildGraph import assignPointsData
import Data.KDtree as KDtree

def findParts(adj_list:AdjacencyList):
    visited = {node:False for node in adj_list.keys()}
    frontier = Queue()
    currentNode = adj_list.get_node_by_index(0)
    i=100
    while len(adj_list.neighbors(currentNode))<=1:
        i+=1
        print(f"{currentNode} has no neighbours")
        currentNode = adj_list.get_node_by_index(i)
    print(f"starting from {currentNode}")
    frontier.enqueue(currentNode)
    while (len(frontier)>0):
        expand(frontier,visited,adj_list)
    graph=[]
    for node,t in visited.items():
        if t:
            graph.append(node)
    return graph
    

def expand(frontier:Queue,visited,adj_list:AdjacencyList):
    node = frontier.dequeue()
    print(f"expanding {node}")
    print(f"Frontier lenght: {len(frontier)}")
    if visited[node]: return
    visited[node] = True
    neighbours = adj_list.neighbors(node)
    print(f"{node} has neighbours {neighbours}")
    for _ in range(len(neighbours)):
        _,neighbour = neighbours.pop()
        print(f"Trying to add {neighbour} to frontier")
        if not visited[neighbour]:
            print(f"successfully added {neighbour} to frontier")
            frontier.enqueue(neighbour)
            print(f"Frontier lenght: {len(frontier)}")

def addLabels(adj_list:AdjacencyList):
    labels = fetch_building_names("llyn_bygning_dtu")
    points = list(adj_list.keys())
    tree = KDtree.buildKDtree(points)
    labeledpoints = assignPointsData(tree,labels)
    for x in labeledpoints.items():
        print(x)
    savePointsDataToFile(labeledpoints,"Data/LabeledPointsNew.json")

def main():
    adj_list,_ = load_adjacency_list("Data/Data/Adjacency_list_ObstacleAwareGraph.json")
    part = findParts(adj_list)
    print(len(part))
    adj_list,_ = load_adjacency_list("Data/Data/Adjacency_list_ObstacleAwareGraph.json")
    nodes = list(adj_list.keys())
    for node in nodes:
        if node in part: continue
        adj_list.popPoint(node)
    save_adjacency_list(adj_list,"Data/Adjacency_List_pruned_disjoint.json")
    addLabels(adj_list)
    visualize_graph(adj_list)
    adj_list,_ = load_adjacency_list("Data/Data/Adjacency_list_ObstacleAwareGraph.json")
    visualize_graph(adj_list)

if __name__ == "__main__":
    main()