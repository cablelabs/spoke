#! /usr/bin/env python3

import pyqrcode
import png
from pyqrcode import QRCode
import os

def gen_qr(poll_id):
 dirname = os.path.dirname(os.path.realpath(__file__))
 qr_path = f"{dirname}/../qr"
 if not os.path.exists(qr_path):
   os.makedirs(qr_path) 
 base_url = os.getenv("BASE_URL")
 url = base_url + "/poll/" + poll_id
 qr = pyqrcode.create(url)
 qr.png(qr_path + '/' + poll_id + '.png', scale = 6)
if __name__ == "__main__":
  import sys
  gen_qr(sys.argv[1])

