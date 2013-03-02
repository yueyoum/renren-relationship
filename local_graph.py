# -*- coding: utf-8 -*-

import random
import cPickle as pickle


import networkx as nx
import matplotlib.pyplot as plt

from renren import FriendsStore, RenRenRelationShip


RENREN_FILE = 'renren_data'

def _dump(data):
    with open(RENREN_FILE, 'w') as f:
        pickle.dump(data, f, 2)
        
        
def _load():
    try:
        with open(RENREN_FILE, 'r') as f:
            return pickle.load(f)
    except IOError:
        from utils import get_accounts
        r = RenRenRelationShip(*get_accounts())
        
        print 'collect friends'
        data = r.collect_friends(level=2)
        _dump(data)
        return data



class GraphAnalysis(object):
    def __init__(self):
        self.G = nx.Graph()
        self.min_node_size = 5
        self.max_node_size = 10

    def import_data(self, fs_list, min_keep=20):
        for fs in fs_list:
            self.G.add_node(fs.uid, lv=fs.level)
            if fs.friends:
                edges = [(fs.uid, u) for u in fs.friends]
                self.G.add_edges_from(edges)
                
                
        # 删掉level 2点，否则最后生成的图片点重叠在一起，看不清
        for n in self.G.nodes():
            if self.G.node[n]['lv'] == 2:
                self.G.remove_node(n)
                

        self.clear_nodes()
        self.degree = nx.degree(self.G)
        
        
        
    def _clear_nodes(self):
        need_clear = False
        for n in self.G.nodes():
            if self.G.degree(n) < 2:
                self.G.remove_node(n)
                need_clear = True
                
        return need_clear
    
    
    def clear_nodes(self):
        while self._clear_nodes():
            pass
                
                
                
    def one_node_size(self, n):
        d = self.degree[n] / 2
        if d < self.min_node_size:
            d = self.min_node_size
        elif d > self.max_node_size:
            d = self.max_node_size
        return d
                
    
    def get_node_size(self, nodes):
        return [self.one_node_size(n) for n in nodes]
    
    
    def get_node_color(self, nodes):
        middle_size = (self.min_node_size + self.max_node_size) / 2
        def _color(n):
            d = self.one_node_size(n)
            if d > middle_size:
                _range = [0.5, 0.8]
            else:
                _range = [0.8, 1.0]
                
            _make = lambda: random.uniform(*_range)
            
            return (_make(), _make(), _make())
        return [_color(n) for n in nodes]
            
        
        


    def save(self, f='result.png', it=55):
        pos = nx.spring_layout(self.G, iterations=it)
        
        nx.draw_networkx_edges(self.G, pos, alpha=0.1)
        
        nx.draw_networkx_nodes(
            self.G,
            pos,
            node_size = self.get_node_size(self.G.nodes()),
            node_color = self.get_node_color(self.G.nodes()),
            alpha = 0.8,
        )
        
        plt.axis('off')
        plt.savefig(f, dpi=200)
        plt.clf()



if __name__ == '__main__':
    data = _load()
    g = GraphAnalysis()
    g.import_data(data)
    g.save()

