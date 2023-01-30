#! /usr/bin/env python3
import json
import time
import os
import threading
import sys

def add(v1, v2, f):
  if not isinstance(v1, list):
    return (v1 + v2 * f)
  result = []
  for i in range(0,len(v1)):
    result.append(v1[i]+v2[i]*f)
  return result  

def init_tot(v):
  if not isinstance(v, list):
    return 0
  return [ 0 for _ in range(len(v)) ]

def divide(tot, n):
  if not isinstance(tot, list):
    return tot/n
  return list(map(lambda x: x/n,tot))


class Controller:
  def __init__(self):
    self.nodes = {}
    self.aggregate = {}
    self.repost_aggregate = {}
    self.group_stats = {}
    self.average = {}
    self.poll_time = 10
    self.yield_time = 0.005
    self.progress_timeout = 30
    self.aggregation_timeout = 600
    self.registrations = {}
    self.lock = threading.Semaphore()
    self.status = {}
    self.seen = {}
    self.pending = {}

  def get_avg(self):
    avg = {}
    n = len(self.nodes)
    for node in self.nodes.keys():
      if not "coef" in avg:
        avg["coef"] = [0]*len(nodes[node]["coef"])
      for i in range(0,len(nodes[node]["coef"])):
        avg["coef"][i] += nodes[node]["coef"][i]
    for i in range(0, len(avg["coef"])):
      avg["coef"][i] = avg["coef"][i]/n
    return avg 

  def update_posted_status(self, node, group):
    self.status[group]["posted"][node] = time.time()

  def update_failed_status(self, node, group):
    self.status[group]["failed"][node] = time.time()

  def get_status(self, node, group, isPending):
    if not group in self.seen:
       self.seen[group] = {}
    if not group in self.pending:
       self.pending[group] = {}
    if node != -1:
      self.seen[group][node] =  time.time()
      self.pending[group][node] =  isPending
    result = {}
    if group in self.status:
      result = self.status[group]
    result["last_seen"] = self.seen[group]
    result["pending"] = self.pending[group]
    return result

  def init_average(self, group, initiator=1, repost=False):
    failed = {}
    if group in self.status and repost:
      failed = self.status[group]["failed"]
    self.status[group] = {"status": "initiated", "time": time.time(), "failed": failed, "posted": {}}
    self.average[group] = {"status": "initiated", "time": time.time(), "initiator": initiator}
    self.group_stats[group] = {"posted":0,"skipped":0}
    if group in self.aggregate:
      del self.aggregate[group]

  def get_posted(self,epoch):
    posted = 0
    with self.lock:
      for n in self.nodes.keys():
        if self.nodes[n]["epoch"] == epoch:
          posted += 1
    return posted

  def wait_for(self, total_nodes, epoch):
    posted = self.get_posted(epoch)
    while posted < total_nodes:
      posted = self.get_posted(epoch)
      time.sleep(0.01)

  def post_aggregate(self, aggregate, from_node, to_node, group=1):
    data = {"aggregate": aggregate, "from_node": from_node, "to_node": to_node, "group": group}
    with self.lock:
      if group in self.average and self.average[group]["initiator"] == from_node:
        self.init_average(group, from_node, repost=(to_node != (from_node + 1)))
      elif group not in self.average:
        self.init_average(group, from_node, False)
      self.update_posted_status(from_node, group)

      if not group in self.aggregate:
        self.aggregate[group] = {}
      self.aggregate[group][to_node] = {"aggregate": aggregate, "time": time.time(), "from_node": from_node}
      self.group_stats[group]["posted"] += 1
      if group not in self.repost_aggregate:
        self.repost_aggregate[group] = {}
      self.repost_aggregate[group][from_node] =  {"status": "consumed"}
      self.repost_aggregate[group][to_node] =  {"status": "empty"}
      return data

  def internal_check_aggregate(self, data):
    group = 1
    if "group" in data:
      group = data["group"]
    node = data["node"]
    result = {"status": "empty"}
    if group in self.repost_aggregate and node in self.repost_aggregate[group]:
      result = self.repost_aggregate[group][node] 
      del self.repost_aggregate[group][node]
    return result

  def poll_internal(self, data, func):
    empty = True
    start_time =  time.time()
    with self.lock:
      result = func(data)
    empty =  ("status" in result) and (result["status"] == "empty")
    while empty and (time.time() - start_time) < self.poll_time:
      time.sleep(self.yield_time)
      with self.lock:
        result = func(data)
        empty =  ("status" in result) and (result["status"] == "empty")
    return result

  def check_aggregate(self, node, group=1):
    data = {"node":node, "group":group} 
    result = self.poll_internal(data, self.internal_check_aggregate)
    return result

  def internal_get_aggregate(self, data):
    result = {"status": "empty"}
    group = 1
    if "group" in data:
      group = data["group"]
    if group in self.aggregate and data["node"] in self.aggregate[group]:
      result = {"status": "ok"}
      if "aggregate" in self.aggregate[group][data["node"]]:
        result["aggregate"] = self.aggregate[group][data["node"]]["aggregate"]
      if "from_node" in self.aggregate[group][data["node"]]:
        result["from_node"] = self.aggregate[group][data["node"]]["from_node"]
      del self.aggregate[group][data["node"]]
      result["posted"] = self.group_stats[group]["posted"] - self.group_stats[group]["skipped"] 
    return result

  def get_aggregate(self, node, group=1):
    data = {"node":node, "group":group} 
    result = self.poll_internal(data, self.internal_get_aggregate)
    return result

  def post_average(self, average, node=-1, group=1):
    data = {"average": average, "node": node, "group": group}
    with self.lock:
      self.average[group]["average"] = average
      self.average[group]["status"] = "posted"
      if group not in self.repost_aggregate:
        self.repost_aggregate[group] = {}
      if node != -1:
        self.repost_aggregate[group][node] =  {"status": "consumed"}
      return data

  def internal_get_average(self, data):
    group = data["group"]
    num_groups = len(self.registrations)
    result = {"status": "empty"}
    tot = None
    n = 0
    num_avgs = 0
    if not "average" in self.average[group]:
      return {"status": "empty"}    
    return {"average": self.average[group]["average"]}

  def get_average(self, group=1):
    result = self.poll_internal({"group":group}, self.internal_get_average)
    return result

  def check_progress(self):
    with self.lock:
      current_time = time.time()
      progress = []
      reposts = []
      for g in self.aggregate.keys():
       for n in self.aggregate[g].keys():
          elapsed = current_time -self.aggregate[g][n]["time"]  
          progress.append({"group": g, "node": n, "elapsed": elapsed}) 
          if elapsed > self.progress_timeout:
              reposts.append({"failed": n,"group":g,"node": self.aggregate[g][n]["from_node"], "repost": {"status": "repost", "repost_to": n+1}})
              print(f"Update Failed node {n} group {g}")
              self.update_failed_status(n, g)
      for repost in reposts:
        if repost["group"] not in self.repost_aggregate:
          self.repost_aggregate[repost["group"]] = {}
        self.repost_aggregate[repost["group"]][repost["failed"]] = repost["repost"]
        del self.aggregate[repost["group"]][repost["failed"]]
        self.group_stats[repost["group"]]["skipped"] += 1
      return {"progress":progress,"stats": self.group_stats}

  def remove_registration(self, pub_key, group=1):
    with self.lock:
      if group not in self.registrations:
        return None
      if pub_key in self.registrations[group]:
         reg = self.registrations[group][pub_key]
         remove_index = reg["index"]
      for reg_key in self.registrations[group].keys():
        if self.registrations[group][reg_key]["index"] > remove_index:
          self.registrations[group][reg_key]["index"] = self.registrations[group][reg_key]["index"]-1
      del self.registrations[group][pub_key]

 
  def register(self, pub_key, group=1):
    with self.lock:
      if group not in self.registrations:
        self.registrations[group] = {}
      if pub_key in self.registrations[group]:
        return self.registrations[group][pub_key]
      current_index = len(self.registrations[group]) + 1
      self.registrations[group][pub_key] = {"index": current_index}
      return self.registrations[group][pub_key]

  def get_registrations(self, group=1):
    with self.lock:
      registration_map = {}
      if group not in self.registrations:
        return registration_map
      for key in self.registrations[group].keys():
        registration_map[self.registrations[group][key]["index"]] = {"pub_key": key}
      return registration_map

  def get_registration(self, pub_key, group=1):
    with self.lock:
      registration = -1
      if group not in self.registrations:
        return registration
      if pub_key in self.registrations[group]:
        registration = self.registrations[group][pub_key]["index"]
      return registration
