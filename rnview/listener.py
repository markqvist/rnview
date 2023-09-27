import os
import sys
import time
import queue
import threading
import RNS
import cv2

APP_NAME="rnview"

class Fetcher():
  DEFAULT_TIMEOUT = 3
  def __init__(self, config_directory, scratch_directory, remote, quality = None, width = None, height = None, output = None):
    self.config_directory = config_directory
    self.scratch_directory = scratch_directory
    self.quality = quality
    self.width = width
    self.height = height
    self.output = output
    self.timeout = None
    self.link = None
    self.remote = remote
    self.identity = self.get_identity()
    self.connected = False
    self.fetch_success = False
    self.fetch_result = None
    self.fetcher_raw = None

  def get_identity(self):
    identity = None
    identity_path = os.path.join(self.config_directory, "identity")
    if not os.path.isdir(self.config_directory):
      os.makedirs(self.config_directory)
    if not os.path.isfile(identity_path):
      RNS.log("Writing new identity to "+str(identity_path), RNS.LOG_DEBUG)
      identity = RNS.Identity()
      identity.to_file(identity_path)
    else:
      RNS.log("Loading identity from "+str(identity_path), RNS.LOG_DEBUG)
      identity = RNS.Identity.from_file(identity_path)

    return identity

  def fetch(self):
    self.connect()

  def connect(self):
    destination_hash = self.remote
    if not RNS.Transport.has_path(destination_hash):
        RNS.Transport.request_path(destination_hash)
        print("Path to "+RNS.prettyhexrep(destination_hash)+" requested  ", end=" ")
        sys.stdout.flush()

    _timeout = time.time() + (self.timeout or Fetcher.DEFAULT_TIMEOUT)
    i = 0
    syms = "⢄⢂⢁⡁⡈⡐⡠"
    while not RNS.Transport.has_path(destination_hash) and not time.time() > _timeout:
        time.sleep(0.1)
        print(("\b\b"+syms[i]+" "), end="")
        sys.stdout.flush()
        i = (i+1)%len(syms)

    if time.time() > _timeout:
        print("\r                                                          \rPath request timed out")
        exit(1)

    server_identity = RNS.Identity.recall(destination_hash)
    self.destination = RNS.Destination(server_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, APP_NAME, "remote")

    self.link = RNS.Link(self.destination)
    self.link.set_link_established_callback(self.link_established)
    self.link.set_link_closed_callback(self.link_closed)

  def link_established(self, link):
    RNS.log("Link established with server, identifying to remote peer...")
    link.identify(self.identity)
    self.connected = True
    self.get_frame()

  def get_frame(self):
    req_data = {}
    if self.quality: req_data["q"] = self.quality
    if self.width: req_data["w"] = self.width
    if self.height: req_data["h"] = self.height
    if len(req_data) == 0: req_data = None

    self.link.request(
        "/image",
        data = req_data,
        response_callback = self.image_response,
        failed_callback = self.request_failed
    )

  def image_response(self, request_receipt):
    tmp_file = os.path.join(self.scratch_directory, "incoming.webp")
    request_id = request_receipt.request_id
    response = request_receipt.response
    RNS.log("Got response for request "+RNS.prettyhexrep(request_id))
    self.fetcher_raw = response

    import numpy as np
    nparr = np.fromstring(response, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR) # cv2.IMREAD_COLOR in OpenCV 3.1

    self.fetch_result = frame
    self.fetch_success = True


  def request_failed(self, request_receipt):
    RNS.log("The request "+RNS.prettyhexrep(request_receipt.request_id)+" failed.")
    exit(2)

  def link_closed(self, link):
    self.connected = False
    if link.teardown_reason == RNS.Link.TIMEOUT:
        RNS.log("The link timed out, exiting now")
    elif link.teardown_reason == RNS.Link.DESTINATION_CLOSED:
        RNS.log("The link was closed by the server, exiting now")
    else:
        RNS.log("Link closed, exiting now")
    
    exit(1)


class RemoteView():
  def __init__(self, config_directory, scratch_directory, capture_source=0, quality=35, allowed=[], resx = None, resy = None):
    self.res_x = resx or 1280
    self.res_y = resy or 720
    self.output_width = self.res_x
    self.output_height = self.res_y
    self.cam = None
    self.cam_ready = False
    self.last_frame = None
    self.quality = quality
    self.config_directory = config_directory
    self.scratch_directory = scratch_directory
    self.frame_queue = queue.Queue()

    self.identity = self.get_identity()
    self.allowed_identities = allowed

    self.destination = RNS.Destination(self.identity, RNS.Destination.IN, RNS.Destination.SINGLE, APP_NAME, "remote")
    self.destination.set_link_established_callback(self.client_connected)

    self.destination.register_request_handler(
        "/image",
        response_generator = self.image_request,
        allow = RNS.Destination.ALLOW_LIST,
        allowed_list = self.allowed_identities
    )
    
    RNS.log("rnview listening on "+RNS.prettyhexrep(self.destination.hash))
    self.destination.announce()

  def image_request(self, path, data, request_id, link_id, remote_identity, requested_at):
    try:
      RNS.log("Returning frame...")
      self.output_width = self.res_x
      self.output_height = self.res_y
      if data and "q" in data:
        self.quality = int(data["q"])
        RNS.log("Setting quality to "+str(self.quality))
      if data and "w" in data:
        self.output_width = int(data["w"])
        RNS.log("Setting width to "+str(self.output_width))
      if data and "h" in data:
        self.output_height = int(data["h"])
        RNS.log("Setting height to "+str(self.output_height))

      self.update_frame()
      self.write_frame()
      image_data = self.load_frame()
      RNS.log("Returning "+RNS.prettysize(len(image_data))+" image")
      return image_data
    except Exception as e:
      RNS.log("Error ocurred while updating frame: "+str(e), RNS.LOG_ERROR)
    
    return None

  def get_identity(self):
    identity = None
    identity_path = os.path.join(self.config_directory, "identity")
    if not os.path.isdir(self.config_directory):
      os.makedirs(self.config_directory)
    if not os.path.isfile(identity_path):
      RNS.log("Writing new identity to "+str(identity_path), RNS.LOG_DEBUG)
      identity = RNS.Identity()
      identity.to_file(identity_path)
    else:
      RNS.log("Loading identity from "+str(identity_path), RNS.LOG_DEBUG)
      identity = RNS.Identity.from_file(identity_path)

    return identity

  def client_connected(self, link):
      global latest_client_link
      RNS.log("Client connected")
      link.set_link_closed_callback(self.client_disconnected)
      link.set_remote_identified_callback(self.remote_identified)
      latest_client_link = link

  def client_disconnected(self, link):
      RNS.log("Client disconnected")

  def remote_identified(self, link, identity):
      RNS.log("Remote identified as: "+str(identity))

  def release_cam(self):
    try:
      self.cam.release()
    except:
      pass  
    self.cam = None
    self.cam_ready = False

  def reader(self):
    self.cam = cv2.VideoCapture(0)
    self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.res_x)
    self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.res_y)
    while True:
      ret, frame = self.cam.read()
      self.cam_ready = True
      if not ret:
        self.cam_ready = False
        break
      if not self.frame_queue.empty():
        try:
          self.frame_queue.get_nowait()
        except queue.Empty:
          pass
      self.frame_queue.put(frame)

    self.release_cam()
    

  def start_reading(self):
    threading.Thread(target=self.reader, daemon=True).start()

  def update_frame(self):
    if not self.cam:
      self.start_reading()
      while not self.cam_ready:
        time.sleep(0.2)
      
    retval, frame = self.cam.read()
    
    if not retval:
      RNS.log("Could not update frame", RNS.LOG_ERROR)
    else:
      self.last_frame = frame
      
  def write_frame(self, quality=None):
    if not quality: quality = self.quality
    cv2.imwrite(os.path.join(self.scratch_directory, "latest_capture.webp"), cv2.resize(self.last_frame, (self.output_width, self.output_height)), [int(cv2.IMWRITE_WEBP_QUALITY), quality])

  def load_frame(self):
    path = os.path.join(self.scratch_directory, "latest_capture.webp")
    with open(path, "rb") as file:
      data = file.read()
    try:
      os.unlink(path)
    except:
      pass
    return data

  def show_frame(self):
    cv2.imshow("Capture", self.last_frame)
    cv2.waitKey()

  def show_frames(self):
    while True:
      self.update_frame()
      cv2.imshow("Capture", self.last_frame)
      cv2.waitKey()