#!/usr/bin/env python3

from ._version import __version__

import RNS
import os
import time
import argparse
import cv2
from rnview.listener import RemoteView, Fetcher

reticulum = None

def program_setup(configdir, rnsconfigdir, listen, destination_hash = None, allowed = None, quality = None, width = None, height = None, output = None, announce = None):
    global reticulum
    reticulum = RNS.Reticulum()

    if listen:
        allowed_list = []
        if allowed:
            for a in allowed:
                allowed_list.append(bytes.fromhex(a))

        remote = RemoteView(os.path.expanduser(configdir), "/tmp", allowed = allowed_list)
        remote.update_frame()
        if announce != None:
            remote.announce()

        min_interval = 60
        should_announce = False
        if announce != None and announce > 0:
            should_announce = True
        if announce != None and announce < min_interval:
            announce = min_interval
        sleep = announce or min_interval
        while True:
            time.sleep(sleep)
            if should_announce:
                remote.announce()
    else:
        dest = bytes.fromhex(destination_hash)
        fetcher = Fetcher(os.path.expanduser(configdir), "/tmp", dest, quality = quality, width = width, height = height, output = output)
        fetcher.fetch()
        while fetcher.fetch_success == False:
            time.sleep(0.25)

        if output == None:
            cv2.imshow("Capture", fetcher.fetch_result)
            cv2.waitKey()
        else:
            path = os.path.expanduser(output)
            RNS.log("Writing frame to "+str(path)+"...")
            with open(path, "wb") as of:
                of.write(fetcher.fetcher_raw)

def main():
    try:
        parser = argparse.ArgumentParser(description="Remote View Utility")
        parser.add_argument("--config", action="store", default=None, help="path to alternative rnview config directory", type=str)
        parser.add_argument("--rnsconfig", action="store", default=None, help="path to alternative Reticulum config directory", type=str)
        parser.add_argument("-l", "--listen", action="store_true", default=False, help="listen for incoming connections")
        parser.add_argument('-a', metavar="allowed_hash", dest="allowed", action='append', help="accept from this identity", type=str)
        parser.add_argument("-b", "--announce", action="store", default=None, help="announce interval in seconds", type=int)
        parser.add_argument("-q", "--quality", action="store", default=None, help="image quality (0-100)", type=int)
        parser.add_argument("-W", "--width", action="store", default=None, help="width in pixels", type=int)
        parser.add_argument("-H", "--height", action="store", default=None, help="height in pixels", type=int)
        parser.add_argument("-o", "--output", action="store", default=None, help="write output to file instead of displaying", type=str)
        parser.add_argument("--version", action="version", version="rnview {version}".format(version=__version__))
        parser.add_argument("destination_hash", nargs="?", default=None, help="hexadecimal hash of the destination", type=str)
        
        args = parser.parse_args()

        if args.config:
            configarg = args.config
        else:
            configarg = "~/.config/rnview"

        if args.rnsconfig:
            rnsconfigarg = args.rnsconfig
        else:
            rnsconfigarg = None

        program_setup(configarg, rnsconfigarg, args.listen, args.destination_hash, allowed=args.allowed, quality=args.quality, width=args.width, height=args.height, output=args.output, announce=args.announce)

    except KeyboardInterrupt:
        print("")
        exit()

if __name__ == "__main__":
    main()