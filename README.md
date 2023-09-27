### Remote View Utility

Remote image capture and transfer over Reticulum. Super early, very hacky, but functional prototype. Requires OpenCV bindings for python; install via `pip install opencv-python`, or on systems like Raspberry Pi with `sudo apt install python3-opencv`.

### Usage

```bash
usage: rnview.py [-h] [--config CONFIG] [--rnsconfig RNSCONFIG] [-l] [-a allowed_hash] [-b ANNOUNCE] [-q QUALITY] [-W WIDTH] [-H HEIGHT] [-o OUTPUT] [--version] [destination_hash]

Remote View Utility

positional arguments:
  destination_hash      hexadecimal hash of the destination

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to alternative rnview config directory
  --rnsconfig RNSCONFIG
                        path to alternative Reticulum config directory
  -l, --listen          listen for incoming connections
  -a allowed_hash       accept from this identity
  -b ANNOUNCE, --announce ANNOUNCE
                        announce interval in seconds
  -q QUALITY, --quality QUALITY
                        image quality (0-100)
  -W WIDTH, --width WIDTH
                        width in pixels
  -H HEIGHT, --height HEIGHT
                        height in pixels
  -o OUTPUT, --output OUTPUT
                        write output to file instead of displaying
  --version             show program's version number and exit
```