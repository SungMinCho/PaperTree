import urllib.request
import os
import PyPDF2
import numpy as np
import re
import networkx as nx
import matplotlib.pyplot as plt
import traceback
import pandas as pd
import holoviews as hv
import networkx as nx
import json

ARXIV_ID_PREFIX = 'ax'

class Paper:
  def __init__(self, id):
    self.id = id
    self.filepath = os.path.join("paperobjs", self.id + '.npy')
    self.loaded = False
    try:
      self.load()
      self.loaded = True
    except Exception as e:
      traceback.print_exc()
  def get_title(self):
    if self.loaded:
      return self.title
    return "Unknown"
  def save(self):
    if self.loaded:
      d = {}
      d['title'] = self.title
      d['refs'] = self.refs
      np.save(self.filepath, d)
  def load(self):
    print('loading ' + self.id)
    if os.path.exists(self.filepath):
      d = np.load(self.filepath).item()
      self.title = d['title']
      self.refs = d['refs']
    else:
      self.download()
      self.save()
    print('loaded ', self.id)
  def download(self):
    # Override this method
    self.title = "Downloaded Title"
    self.refs = {}
  # doesn't return proper IDs
  def references(self, base):
    if self.loaded:
      return self.refs.get(base, [])
    return []
  # return proper IDs
  def references_ID(self, base=None):
    if self.loaded:
      if base == 'arxiv':
        return [ARXIV_ID_PREFIX+arxiv_id for arxiv_id in self.refs.get('arxiv', [])]
      # add other bases later
      # if base is None return from all bases
      elif base == None:
        ret = []
        for key in self.refs:
          ret.extend(self.references_ID(key))
        return ret
    return []

class ArxivPaper(Paper):
  def __init__(self, arxiv_id):
    id = ARXIV_ID_PREFIX + arxiv_id
    self.arxiv_id = arxiv_id
    super().__init__(id)

  def download(self):
    print('downloading ', self.id)
    dirpath = os.path.join('pdfs', self.id)
    pdfpath = os.path.join(dirpath, self.id + '.pdf')
    if not os.path.exists(dirpath):
      os.makedirs(dirpath)
    if not os.path.exists(pdfpath):
      url = "https://arxiv.org/pdf/" + self.arxiv_id
      print("downloading " + url)
      urllib.request.urlretrieve(url, pdfpath)
    pdfFile = open(pdfpath, 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFile)
    text = ""
    for i in range(pdfReader.numPages):
      text += pdfReader.getPage(i).extractText()
    text = ''.join(text.split())
    self.refs = {}
    self.refs['arxiv'] = re.findall('https?://arxiv.org/abs/([0-9]*.[0-9]*)', text)

    url = "https://arxiv.org/abs/" + self.arxiv_id
    title = urllib.request.urlopen(url).read().decode('utf8')
    title = re.findall("<title>([^<]*)</title>", title)[0]
    title = ' '.join(title.split()[1:])
    self.title = title

class Papers:
  def __init__(self, ps):
    self.papers = {} # id -> paper object
    for p in ps:
      self.papers[p.id] = p

  def add_arxiv_paper(self, arxiv_id):
    id = ARXIV_ID_PREFIX + arxiv_id
    if id not in self.papers:
      self.papers[id] = ArxivPaper(arxiv_id)
    return self.papers[id]

  def save(self):
    for p in self.papers.values():
      p.save()

  def step(self, paper):
    if paper.id not in self.papers:
      self.papers[paper.id] = paper

    # add arxiv references
    for r in paper.references('arxiv'):
      self.add_arxiv_paper(r)
    # add references from other bases later

  def step_all(self):
    for paper in list(self.papers.values()):
      self.step(paper)

  def __len__(self):
    return len(self.papers)

  def graph(self):
    G = nx.DiGraph()
    label_dict = {}
    for pid in self.papers:
      paper = self.papers[pid]
      G.add_node(pid, name=paper.get_title())
      label_dict[pid] = paper.get_title()
      for rid in paper.references_ID():
        G.add_edge(pid, rid)

    return G

  def export_graph_to_json(self, path="graph/graph.json"):
    #G = self.graph()
    #json_graph = nx.readwrite.json_graph.node_link_data(G)
    #with open(path, 'w') as f:
    #  json.dump(json_graph, f)
    d = {}
    nodes = []
    edges = []
    pid_to_id = {}
    id = -1
    def get_id(pid):
      if pid not in pid_to_id:
        id += 1
        pid_to_id[pid] = id
      return pid_to_id[pid]

    for pid in self.papers:
      id += 1
      pid_to_id[pid] = id
      node = {}
      node['id'] = id
      paper = self.papers[pid]
      node['label'] = paper.get_title()
      node['x'] = 0.0
      node['y'] = 0.0
      node['pid'] = pid

      nodes.append(node)

    for pid in self.papers:
      paper = self.papers[pid]
      for rid in paper.references_ID():
        edge = {}
        edge['from'] = pid_to_id[pid]
        if rid not in pid_to_id:
          id += 1
          pid_to_id[rid] = id
          node = {}
          node['id'] = id
          node['title'] = 'Unknown'
          node['x'] = 0.0
          node['y'] = 0.0
          node['pid'] = 'Unknown'

          nodes.append(node)
        edge['to'] = pid_to_id[rid]
        edges.append(edge)

    d['nodes'] = nodes
    d['edges'] = edges
    with open(path, 'w') as f:
      json.dump(d, f)
