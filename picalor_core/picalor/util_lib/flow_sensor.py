import math
import threading
import pigpio as io

class FlowSensorPulseType():
    """Evaluate output of a hardware flow sensor with pulse output
    attached to any GPIO input of the Raspberry Pi

    To acheive high precision and fast read-outs with low input pulse rate,
    this uses accurate interval timing of full cycles of input pulses.

    For invalid measurements, a NaN value is returned.
    """
    def __init__(self, pi, sensor_config):
        """Arguments:

        pi:             pigpio.pi() object
        sensor_config:  dictionary containing GPIO configuration and
                        calibration data as attributes:
                            sensor_config["GPIO"]
                            sensor_config["TIMEOUT_US"]
                            sensor_config["MIN_AVG_PERIOD_US"]
                            sensor_config["SENSITIVITY"]
        """
        self.pi = pi
        # Time in seconds for accumulating input pulses and calculating pulse rate
        self.MIN_AVG_PERIOD_US = sensor_config["MIN_AVG_PERIOD_US"]
        # Sensitivity of the flowmeter channel in pulses per liter
        self.SENSITIVITY = sensor_config["SENSITIVITY"]
        # Measurement is invalidated (NaN value) if no pulse within TIMEOUT
        self.TIMEOUT_US = sensor_config["TIMEOUT_US"]
        # Number of pulse/pause cycles counted in an averaging period.
        # This is initialised to -1 so that after the initial two pulses, the
        # correct number of one valid input cycle is reached.
        self._n_cycles = -1
        # Timestamp for first and last input transition in each averaging period:
        self._t_first = self.pi.get_current_tick()
        self._t_last = self._t_first
        self._timer_spinlock = threading.Lock()
        # Stored last valid result of input pulse rate in 1/sec
        self._cycles_sec = 0.0
        pi.set_mode(sensor_config["GPIO"], io.INPUT)
        pi.set_pull_up_down(sensor_config["GPIO"], io.PUD_UP)
        # Set up a callback function for handling GPIO input pulse timing
        self.timer_counter = pi.callback(sensor_config["GPIO"],
                                         io.FALLING_EDGE,
                                         self._gpio_timer_ctr_cb
                                         )
    
    def stop(self):
        self._timer_spinlock.acquire()
        self.timer_counter.cancel()
        self._timer_spinlock.release()

    def read_liter_sec(self):
        """Same as read_cycles_sec() but converted into flow rate
        in liters per second.

        This uses the configured SENSITIVITY constant in pulses per liter.
        """
        return self.read_cycles_sec() / self.SENSITIVITY

    def read_cycles_sec(self):
        """Returns the flow sensor output pulse rate in 1/sec.

        This averages the time of all pulses at the GPIO input
        occurring between calls to this function.

        When this is called before the configured MIN_AVG_PERIOD_US has passed,
        the last valid value is returned.

        When no pulses have been registered within the
        configurable TIMEOUT_US setting, a NaN value is returned.

        At start-up, before any input pulse period has completed, and if there
        was no timeout, an initial float zero (0.0) value is returned.
        """
        # 32-bit counters wrap around (72 minutes), integer arithmetic is needed
        diff_u32_ticks = (self.pi.get_current_tick() - self._t_last) & 0xFFFFFFFF
        # When no new input cycles were registered within TIMEOUT_US,
        # return NaN. (self._t_last is updated continuously on new input pulses)
        if diff_u32_ticks >= self.TIMEOUT_US:
            return math.nan
        # Access to state variables is not atomic, so we lock the timer callback.
        self._timer_spinlock.acquire()
        diff_u32_ticks = (self._t_last - self._t_first) & 0xFFFFFFFF
        if diff_u32_ticks < self.MIN_AVG_PERIOD_US:
            # While averaging time has not passed, return last valid value
            self._timer_spinlock.release()
            return self._cycles_sec
        # Minimum time has passed and at leat one full cycle was registered.
        self._cycles_sec = 1E6 * self._n_cycles / diff_u32_ticks
        # Reset counter.
        self._n_cycles = 0
        # The last timed pulse is re-used as the reference for the next
        self._t_first = self._t_last
        self._timer_spinlock.release()
        return self._cycles_sec

    # Callback for counting and timing flow sensor GPIO input pulses.
    def _gpio_timer_ctr_cb(self, gpio, level, tick):
        self._timer_spinlock.acquire()
        if self._n_cycles == -1:
            self._t_first = tick
        else:
            self._t_last = tick
        # Anyways:
        self._n_cycles += 1
        self._timer_spinlock.release()


class FlowSensorFixed():
    """Returns a fixed value when calling read_liter_sec()

    Value is set in config file.
    """
    def __init__(self, sensor_config):
        """Arguments:

        sensor_config:  dictionary containing the fixed read-out value:
                            sensor_config["FLOW_LITER_SEC"]
        """
        self.result = sensor_config["FLOW_LITER_SEC"]
    
    def stop(self):
        pass

    def read_liter_sec(self):
        """Returns the preset result value
        """
        return self.result

    def read_cycles_sec(self):
        """Returns a NaN value since there are no pulses
        """
        return math.nan