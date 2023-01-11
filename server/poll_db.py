#! /usr/bin/env python3
import os
import json
import string
import random

class PollDB:
  def __init__(self):
    dirname = os.path.dirname(os.path.realpath(__file__))
    self.db_path = f"{dirname}/../db"
    if not os.path.exists(self.db_path):
      os.makedirs(self.db_path)
  def save(self,poll,poll_id, account):
    with open(f"{self.db_path}/{poll_id}.json","w") as f:
     f.write(json.dumps(poll))
    with open(f"{self.db_path}/{account}.idx","a+") as f:
     f.write(f"{poll_id}\n")
  def update(self,poll,poll_id):
    with open(f"{self.db_path}/{poll_id}.json","w") as f:
     f.write(json.dumps(poll))

  def list(self,account):  
    ids = []
    if not os.path.exists(f"{self.db_path}/{account}.idx"):
      return ids
    with open(f"{self.db_path}/{account}.idx","r") as f:
       for line in f:
         poll_id = line.strip("\n")
         ids.append(poll_id)
    return ids
  def full_list(self,account):  
    polls = []
    for poll_id in self.list(account):
      polls.append({"poll_id": poll_id, "poll":self.load(poll_id)})
    return polls
  def load(self,poll_id):
    if not os.path.exists(f"{self.db_path}/{poll_id}.json"):
      return None
    with open(f"{self.db_path}/{poll_id}.json","r") as f:
     return json.loads(f.read())
  def remove(self, poll_id, account):
    os.remove(f"{self.db_path}/{poll_id}.json")
    new_list = []
    with open(f"{self.db_path}/{account}.idx","r") as f:
      for line in f:
        pid = line.strip("\n")
        if pid != poll_id: 
          new_list.append(pid)
    with open(f"{self.db_path}/{account}.idx","w") as f:
      for poll in new_list:
        f.write(f"{poll}\n")
  def create(self,poll, account):
    letters = string.ascii_lowercase
    poll_id = ''.join(random.choice(letters) for i in range(20))
    while os.path.exists(f"{self.db_path}/{poll_id}.json"):
      poll_id = ''.join(random.choice(letters) for i in range(20))
    self.save(poll,poll_id, account)
    return poll_id


    
