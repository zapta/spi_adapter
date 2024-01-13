#!python

# Build the platformio targets and copy their firmware images to ../release.

import subprocess
import os
import sys
import re
from typing import List
import shutil
import glob

# TODO: Add command flag for dry run without updating release.
# TODO: Add a command flag for not cleaning before building.
# TODO: Add a command flag build just a single environment
# TODO: Add a command flag for verbose build.

# Path to the platformio command.
bin_dir = "Scripts" if os.name == 'nt' else "bin"
pio = os.path.join(os.path.expanduser("~user"), f".platformio/penv/{bin_dir}/pio")


def get_platformio_envs() -> List[str]:
    """Fetch the list of envs in this platformio project file."""
    print(f"Fetching platformio's environment names.", flush=True)
    lines = subprocess.run(
        [pio, "run", "--list-targets"], text=True, stdout=subprocess.PIPE, check=True
    ).stdout.splitlines()
    pattern = re.compile("^([^\\s]+)[\\s]+Platform[\\s].*$")
    envs = []
    for line in lines:
        m = pattern.match(line)
        if m:
            env = m.group(1)
            envs.append(env)
    envs.sort()
    return envs


# --- Main

# Clean platformio builds.
subprocess.run([pio, "run", "--target", "fullclean"], check=True)

# Delete all release files.
for f in glob.glob("../release/*.uf2"):
    os.remove(f)

# For each env, built and copy its .uf2 file to release directory.
envs = get_platformio_envs()
log = []
for env in envs:
    print(f"Building env: {env}", flush=True)
    subprocess.run([pio, "run", "--environment", env], check=True)
    src = f".pio/build/{env}/firmware.uf2"
    dst = f"../release/{env}.uf2"
    shutil.copy(src, dst)
    log.append(f"  {dst:42} {os.path.getsize(dst):5} Bytes")

# All done.
print(f"\nRelease files:", flush=True)
print("\n".join(log), flush=True)
print(flush=True)
