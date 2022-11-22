#!/usr/bin/env python3
import sys
import time
import threading
import subprocess
import logging
import atexit
import pigpio
from picalor.picalor_state import PicalorState
from picalor.picalor_api import PicalorApi
from picalor.picalor_measurement_daemon import PicalorMeasurementDaemon

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("picalor_core")

class Picalor():
    """Picalor - Multi-Channel Heat Flow Calorimetry on the Raspberry Pi

    Thermal power (or heat flow) measurement of one segmented or multiple
    individual liquid-cooled or liquid-heated systems under the assumption that
    the enthalpy difference of the fluid entering and exiting each system per
    unit of time is equal to the energy dissipated or released by the system.

    Quasi-isothermal condition can be achieved by using a sufficiently high
    flow rate. Accurate heat flow measurements under these conditions
    require very sensitive and robust differential temperature sensing.

    This is implemented by the Picalor hardware using platinum resistive
    temperature sensors in a deflection-type bridge configuration connected
    to a multi-channel, high-precision delta-sigma ADC system.

    When performing the measurement with fluid temperatures set nearly at
    environmental temperature level, convection and radiation heat loss
    can be made negligible e.g. for power loss measurements in electronics.

    For applications in chemistry, the multi-channel hardware can be useful
    for Constant Flux Calorimetry or segmented Continuous Reaction Calorimters.

    Supported hardware:

    * Picalor OSHW Raspberry Pi add-on circuit board featuring:
        - 16-channel analog frontend for Pt 1000 sensors
        - 4x pulse-timing flow sensor inputs
        - 2x ADS1256 24-Bit 8-ch ADC
    * Waveshare "High Precision AD/DA board"

    Ulrich Lukas 2022-08-17
    """
    def __init__(self, pi, interactive=False):
        logger.debug(f"Invocation thread: {threading.current_thread().name}")
        # pigpio library is used for interfacing GPIOs and SPI communication
        if not pi.connected:
            raise IOError("Could not connect to hardware via pigpio library")
        self.interactive = interactive
        self.app_running = False
        atexit.register(self.stop_app)
        # Global events, controlling all threads if needed
        self.app_stop_requested = threading.Event()
        self.poweroff_requested = threading.Event()
        # Store object representing the view- / API-facing application state
        self.state = PicalorState()
        self.api = PicalorApi(self, self.state)
        self.measurement_daemon = PicalorMeasurementDaemon(pi, self.state, self.api)

    def run_app(self):
        logger.debug("run_app() called")
        if self.app_running:
            logger.warning("Already running!")
            return
        self.app_running = True
        self.poweroff_requested.clear()
        self.app_stop_requested.clear()
        self.measurement_daemon.start()
        self.api.start_frontends()
        # Return to interpreter CLI while app keeps running
        if self.interactive:
            return
        # If this is not run from an interpreter loop, sleep forever
        try:
            while True:
                time.sleep(1e9)
        except (KeyboardInterrupt, SystemExit):
            logger.info(
                "\x1B[J\n"
                "Exit requested. Terminating Picalor app.\n\x1B[?25h"
            )
            self.stop_app()

    def stop_app(self):
        logger.debug("stop_app() called")
        if not self.app_running:
            logger.warning("Not running!")
            return
        self.app_running = False
        if self.app_stop_requested.is_set():
            logger.debug("App stop already in process")
            return
        self.app_stop_requested.set()
        self.measurement_daemon.stop()
        self.api.stop_frontends()
        if self.interactive:
            return
        if self.poweroff_requested.is_set():
            subprocess.call(["sudo", "shutdown", "-h", "now"])
        else:
            sys.exit(0)
    
    def poweroff(self):
        self.poweroff_requested.set()
        self.stop_app()

def main():
    print("\x1B[2J\x1B[H\n" # Clear screen
          f"{Picalor.__doc__}\n\x1B[J\n"
          "Press CTRL-C to exit.\n"
          )
    try:
        pi = pigpio.pi()
        pc = Picalor(pi)
        pc.run_app()
    finally:
        pi.stop()

if __name__ == "__main__":
    main()