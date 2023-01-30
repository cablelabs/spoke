#! /usr/bin/env python3
from flask import Flask, request, abort, send_file

import json
import threading
import sys
import os
import uuid
from safe import Controller
from poll_db import PollDB
from qr_helper import gen_qr

app = Flask(__name__)

controller = Controller()
db = PollDB()

auth_enabled = os.getenv("AUTH_ENABLED")
authorized_users = {}
if auth_enabled == "true":
  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../db/users.db") as f:
    for line in f:
      authorized_users[line.strip('\n')] = True

@app.route('/create_poll',methods=['POST'])
def create_poll():
  data = request.get_json(force=True)
  result = db.create(data["poll"], data["account"])
  gen_qr(result)
  return json.dumps({"poll_id":result})

@app.route('/qr/<poll>',methods=['GET'])
def get_qr(poll):
  dirname = os.path.dirname(os.path.realpath(__file__))
  filename = f"{dirname}/../qr/{poll}.png"
  return send_file(filename, mimetype='image/png')

@app.route('/pk/<pk>',methods=['GET'])
def get_pk(pk):
  dirname = os.path.dirname(os.path.realpath(__file__))
  filename = f"{dirname}/../pk/{pk}.pk"
  with open(filename) as f:
      result = f.read()
  return result

@app.route('/genpk',methods=['POST'])
def gen_pk():
  data = request.get_json(force=True)
  pk = data['pk']
  dirname = os.path.dirname(os.path.realpath(__file__))
  pk_path = f"{dirname}/../pk"
  if not os.path.exists(pk_path):
    os.makedirs(pk_path)
  pkid = "%s" % uuid.uuid4()
  filename = f"{dirname}/../pk/{pkid}.pk"
  with open(filename,'w') as f:
      result = f.write(pk)
  return pkid

@app.route('/get_poll',methods=['POST'])
def get_poll():
  data = request.get_json(force=True)
  result = db.load(data["poll_id"])
  if result is None:
    return json.dumps({"status":"NOTFOUND"})
  if "registrations" in result:
    for reg in result["registrations"]:
      controller.register(reg,group=data["poll_id"])
  return json.dumps({"poll":result, "poll_id": data["poll_id"]})

@app.route('/polls',methods=['POST'])
def polls():
  data = request.get_json(force=True)
  result = db.full_list(data["account"])
  return json.dumps({"polls":result})

@app.route('/list_polls',methods=['POST'])
def list_polls():
  data = request.get_json(force=True)
  result = db.list(data["account"])
  return json.dumps({"poll_ids":result})

@app.route('/remove_poll',methods=['POST'])
def remove_poll():
  data = request.get_json(force=True)
  db.remove(data["poll_id"],data["account"])
  return json.dumps({"poll_id":data["poll_id"]})

@app.route('/remove_registration',methods=['POST'])
def remove_registration():
  data = request.get_json(force=True)
  poll = db.load(data["poll_id"])
  poll["registrations"].remove(data["pub_key"])
  db.update(poll,data["poll_id"])
  controller.remove_registration(data["pub_key"], data["poll_id"])
  return json.dumps({"poll_id":data["poll_id"]})


@app.route('/register',methods=['POST'])
def register():
  data = request.get_json(force=True)
  poll = db.load(data["group"])
  if not "registrations" in poll:
    poll["registrations"] = []
  if data["pub_key"] not in poll["registrations"]:
    poll["registrations"].append(data["pub_key"])
    db.update(poll,data["group"])
  result = controller.register(data["pub_key"],group=data["group"])
  return json.dumps(result)

@app.route('/status',methods=['POST'])
def status():
  data = request.get_json(force=True)
  isPending = False
  if "pending" in data:
    isPending = data["pending"]
  result = controller.get_status(data["node"],data["group"],isPending)
  return json.dumps(result)

@app.route('/post_aggregate',methods=['POST'])
def post_aggregate():
  data = request.get_json(force=True)
  result = controller.post_aggregate(data["aggregate"],data["from_node"],data["to_node"],group=data["group"])
  return json.dumps(result)

@app.route('/check_aggregate',methods=['POST'])
def check_aggregate():
  data = request.get_json(force=True)
  result = controller.check_aggregate(data["node"],group=data["group"])
  return json.dumps(result)

@app.route('/get_aggregate',methods=['POST'])
def get_aggregate():
  data = request.get_json(force=True)
  result = controller.get_aggregate(data["node"],group=data["group"])
  return json.dumps(result)

@app.route('/get_average',methods=['POST'])
def get_average():
  data = request.get_json(force=True)
  result = controller.get_average(group=data["group"])
  return json.dumps(result)

@app.route('/post_average',methods=['POST'])
def post_agverage():
  data = request.get_json(force=True)
  result = controller.post_average(data["average"],node=data["node"],group=data["group"])
  return json.dumps(result)

@app.route('/get_registrations',methods=['POST'])
def get_registrations():
  data = request.get_json(force=True)
  result = controller.get_registrations(group=data["group"])
  return json.dumps(result)

@app.route('/get_registration',methods=['POST'])
def get_registration():
  data = request.get_json(force=True)
  result = controller.get_registration(data["pub_key"],group=data["group"])
  return json.dumps({"index":result})

@app.route("/scan",methods=["GET"])
def scan():
  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../web/scan.html") as f:
    html = f.read()
  return html

@app.route("/",methods=["GET"])
def index():
  auth_enabled = os.getenv("AUTH_ENABLED")
  if auth_enabled == "true":
    user = request.args.get('account')
    if user not in authorized_users:
      abort(401)

  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../web/index.html") as f:
    html = f.read()
  return html

@app.route("/js/<jsfile>",methods=["GET"])
def js(jsfile):
  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../web/js/{jsfile}") as f:
    html = f.read()
  return html

@app.route("/css/<cssfile>",methods=["GET"])
def css(cssfile):
  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../web/css/{cssfile}") as f:
    html = f.read()
  return html

@app.route("/poll/<pollid>",methods=["GET"])
def poll(pollid):
  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../web/poll.html") as f:
    html = f.read().replace("__POLL_ID__",pollid)
  return html

@app.route("/enc_test",methods=["GET"])
def enc_test():
  dirname = os.path.dirname(os.path.realpath(__file__))
  with open(f"{dirname}/../web/enc_test.html") as f:
    html = f.read()
  return html


def check_progress():
  controller.check_progress()
  threading.Timer(10,check_progress).start()


if __name__ == "__main__":
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    port = 8088
    if len(sys.argv) > 1:
       port = int(sys.argv[1])
    check_progress()
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)
 
