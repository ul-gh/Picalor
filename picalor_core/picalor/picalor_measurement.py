import logging
import json
import numpy as np
from picalor.util_lib.pt1000_sensor import (
    ptRTD_temperature, wheatstone, wheatstone_factor
)
from pipyadc import ADS1256_definitions as adc_def

logger = logging.getLogger("Measurement")


class Measurement():
    """One channel of the calorimetric power measurement.

    This performs two differential resistance measurements of the Pt1000
    sensors at the input and output port of the measured object and an
    absolute measurement of the voltage of the resistance reference.

    The thermal fluid flow rate is then read from the configured flow sensor.
    
    Heat flow is finally calculated based on temperature difference, flow rate
    and temperature-dependent heat capacity and density of the thermal fluid. 

    Three ADC channels and the AINCOM reference pin are utilised, where the two
    Pt1000 sensors and one resistance reference are configured in a three-leg
    wheatstone-bridge and read in succession via three of the ADC inputs.
    
    For the resistance reference channel, AINCOM is used as absolute reference.
    For the pt1000 upstream channel, r_ref is used as the reference.
    For the pt1000 downstream channel, the upstream sensor is the reference.

        rs_ref, rs_up, rs_dn:   Bridge high-side resistors (10 kOhms for Pt1000)
        r_ref:   Bridge resistance reference resistor (1.1 kOhms for 25°C)
              _______________________
             |           |           |
           rs_ref      rs_up       rs_dn
             |           |           |
             |ADC_IN     |ADC_IN     |ADC_IN
             |           |           |
           r_ref     pt1000_up    pt1000_dn
             |           |           |
              _______________________ ADC_AINCOM (0V)
    """
    def __init__(self, state, measurement_index, adc_obj, flow_sensor, fluid):
        self.state = state
        self.adc_obj = adc_obj
        self.flow_sensor = flow_sensor
        self.fluid = fluid
        # These are only short-cuts to the config items
        # Average this number of measurements
        self.FILTER_SIZE = state.conf["measurements"]["FILTER_SIZE"]
        # Measurement configuration for this measurement channel (!= ADC channel!)
        self.own_conf = state.conf["measurements"]["chs"][measurement_index]
        self.adc_key = self.own_conf["adc_device"]
        logger.info(f"Configuring measurement channel: {self.own_conf['info']}")
        self.temp_ch_up = self.own_conf["temp_ch_up"]
        self.temp_ch_dn = self.own_conf["temp_ch_dn"]
        self.flow_sensor_temp_ch = self.own_conf["flow_sensor_temp_ch"]
        adc_conf = state.conf["adcs"][self.adc_key]
        self.adc_temp_chs = adc_conf["temp_chs"]
        # Reference channel resistance ratio
        self.N_REF = adc_conf["r_ref"]["r_s"] / adc_conf["r_ref"]["r_ref"]
        self.adc_mux_seq = [
            # Resistance reference channel  first,
              getattr(adc_def, adc_conf["r_ref"]["mux"]) << 4
            | getattr(adc_def, adc_conf["aincom"]["mux"]),
            # followed by the upstream temperature sensor, and
              getattr(adc_def, self.adc_temp_chs[self.temp_ch_up]["mux"]) << 4
            | getattr(adc_def, adc_conf["r_ref"]["mux"]),
            # completed by the downstream sensor for the current acquisition
              getattr(adc_def, self.adc_temp_chs[self.temp_ch_dn]["mux"]) << 4
            | getattr(adc_def, self.adc_temp_chs[self.temp_ch_up]["mux"]),
        ]
        # ADC raw channel offset values. (Likely unnecessary, should be zero)
        self.adc_offsets = np.array([
            adc_conf["r_ref"]["adc_offset"],
            self.adc_temp_chs[self.temp_ch_up]["adc_offset"],
            self.adc_temp_chs[self.temp_ch_dn]["adc_offset"],
        ])
        # Measurement channel series (bridge high-side) resistance value
        self.r_s_up = self.adc_temp_chs[self.temp_ch_up]["r_s"]
        self.r_s_dn = self.adc_temp_chs[self.temp_ch_dn]["r_s"]
        # Resistance offset from instrument calibration
        self.r_offset_up = self.adc_temp_chs[self.temp_ch_up]["r_offset"]
        self.r_offset_dn = self.adc_temp_chs[self.temp_ch_dn]["r_offset"]
        # Platinum RTD base (0°C) resistance calibration values
        self.r_0_up = self.own_conf["r_0_up"]
        self.r_0_dn = self.own_conf["r_0_dn"]
        # Resistance offset for wiring resistance
        self.r_wires_up = self.own_conf["r_wires_up"]
        self.r_wires_dn = self.own_conf["r_wires_dn"]
        # Results
        self.results_meas = state.results["measurements"]["chs"][measurement_index]
        self.results_adc = state.results["adcs"][self.adc_key]
        self.results_adc_temp_chs = state.results["adcs"][self.adc_key]["temp_chs"]
        self.results_log = state.results["data_log"]
        # Buffer for raw input samples.
        # For each measurement channel, three samples are acquired in succession:
        # resistance reference -> upstream Pt1000 sensor -> downstream Pt1000 sensor
        self.adc_buf = np.zeros((self.FILTER_SIZE, 3), dtype=int)

    def scan_sensors(self):
        # To be called repeatedly to update adc_buf with new ADC samples and
        # calculate results with averaged data.
        self.adc_obj.read_sequence(self.adc_mux_seq, self.adc_buf[0])
        for j in range(1, self.FILTER_SIZE):
            # Do the data acquisition of the multiplexed input channels
            self.adc_obj.read_continue(self.adc_mux_seq, self.adc_buf[j])
    
        # Average of input samples without offset correction
        adc_avg = np.average(self.adc_buf, axis=0)
        # Elementwise operation (np.array):
        adc_unscaled = adc_avg - self.adc_offsets

        # Calculate resistances for multi-leg wheatstone bridge setup
        # starting with upstream (cold inlet) sensor resistance value
        r_upstream_w_offset = wheatstone(
            adc_unscaled[1],
            adc_unscaled[0],
            self.N_REF,
            self.r_s_up
        )
        r_upstream = r_upstream_w_offset - self.r_offset_up - self.r_wires_up

        # Downstream sensor uses the upstream sensor as reference bridge leg
        # Differential measurement must be added to absolute measurement
        # to calculate the reference voltage for the second bridge setup.
        r_downstream = wheatstone(
            adc_unscaled[2],
            adc_unscaled[1] + adc_unscaled[0],
            self.r_s_up / r_upstream_w_offset,
            self.r_s_dn
        ) - self.r_offset_dn - self.r_wires_dn
        # Write results to state
        self.results_adc["r_ref"]["adc_unscaled"] = adc_unscaled[0]
        self.results_adc_temp_chs[self.temp_ch_up]["adc_unscaled"] = adc_unscaled[1]
        self.results_adc_temp_chs[self.temp_ch_dn]["adc_unscaled"] = adc_unscaled[2]
        self.results_adc_temp_chs[self.temp_ch_up]["resistance"] = r_upstream
        self.results_adc_temp_chs[self.temp_ch_dn]["resistance"] = r_downstream
        # Calculate temperatures from Pt1000 sensor resistances
        # Inverted H.L.Callendar equation for Pt1000 temperatures:
        t_upstream = ptRTD_temperature(r_upstream, r_0=self.r_0_up)
        t_downstream = ptRTD_temperature(r_downstream, r_0=self.r_0_dn)
        self.results_adc_temp_chs[self.temp_ch_up]["temperature"] = t_upstream
        self.results_adc_temp_chs[self.temp_ch_dn]["temperature"] = t_downstream
        self.results_meas["t_upstream"] = t_upstream
        self.results_meas["t_downstream"] = t_downstream
    
    def calculate_power(self):
        t_upstream = self.results_meas["t_upstream"]
        t_downstream = self.results_meas["t_downstream"]
        # Flow sensor temperature might be on another channel
        t_flow = self.results_adc_temp_chs[self.flow_sensor_temp_ch]["temperature"]
        # Own calibration values
        power_offset = self.own_conf["power_offset"]
        power_gain = self.own_conf["power_gain"]
        # Calculate power
        t_avg = 0.5 * (t_upstream + t_downstream)
        c_th = self.fluid.get_c_th(t_avg)
        t_diff = t_downstream - t_upstream
        flow_liter_sec = self.flow_sensor.read_liter_sec()
        flow_kg_sec = flow_liter_sec * self.fluid.get_density(t_flow)
        # Write results back to application state
        power = power_gain * flow_kg_sec * c_th * t_diff - power_offset
        self.results_meas["flow_kg_sec"] = flow_kg_sec
        self.results_meas["power_w"] = power

    def set_power_offset(self, offset):
        self.own_conf["power_offset"] = offset

    def set_power_gain(self, gain):
        self.own_conf["power_gain"] = gain

    def tare_power(self):
        logger.debug("Performing Zero-Calibration for measurement:\n"
                     f"{self.own_conf['info']}")
        power = self.results_meas["power_w"]
        self.own_conf["power_offset"] += power
        logger.debug(f"New offset:    {self.own_conf['power_offset']: 12.3f}")


class Fluid():
    def __init__(self, fluid_conf):
        self.conf = fluid_conf

    # Fluid density depending on temperature in degrees celsius
    def get_density(self, t_celsius):
        if self.conf["density_use_polynomial"]:
            d_num = np.poly1d(self.conf["density_numerator"])
            d_denom = np.poly1d(self.conf["density_denominator"])
            return d_num(t_celsius) / d_denom(t_celsius)
        else:
            d_t_ref = self.conf["density_t_ref"]
            d_values = self.conf["density_values"]
            return np.interp(t_celsius, d_t_ref, d_values)

    # Specific heat capacity
    def get_c_th(self, t_celsius):
        if self.conf["c_th_use_polynomial"]:
            c_num = np.poly1d(self.conf["c_th_numerator"])
            c_denom = np.poly1d(self.conf["c_th_denominator"])
            return c_num(t_celsius) / c_denom(t_celsius)
        else:
            c_t_ref = self.conf["c_th_t_ref"]
            c_values = self.conf["c_th_values"]
            return np.interp(t_celsius, c_t_ref, c_values)


class Calibrator():
    """Calibration for one resistance input channel

        rs_ref, rs_up:   Bridge high-side resistor (10 kOhms for Pt1000)
        r_ref:   Bridge resistance reference resistor (1.1 kOhms for 25°C)
              ___________
             |           |
           rs_ref      rs_up
             |           |
             |ADC_IN     |ADC_IN
             |           |
           r_ref     pt1000_up
             |           |
              ___________ ADC_AINCOM (0V)
    """
    def __init__(self, meas_daemon, state, api):
        self.meas_daemon = meas_daemon
        self.state = state
        self.api = api
        self.FILTER_SIZE = state.conf["measurements"]["FILTER_SIZE"]
        # Buffer for raw input samples. First, resistance reference is sampled,
        # then, the attached calibration standard is sampled
        self.adc_buf = np.zeros((self.FILTER_SIZE, 2), dtype=int)
    
    # This is called from the API.
    # calibration data for the requested temperature channel has been acquired
    # and calibration results have been written back to state.conf.
    def calibrate_channel(self, adc_key, temp_ch_idx, value_key, cal_resistance):
        msg = ""
        if cal_resistance < 0.0 or value > 10000.0:
            msg = f"Cal resistance must be between 0.0 and 10000.0!"
        if not value_key in ("cal_r_a", "cal_r_b"):
            msg = f"Invalid resistance value key: {value_key}"
        if not adc_key in self.state.conf["adcs"].keys():
            msg = f"Invalid ADC key: {adc_key}"
        if not temp_ch_idx in range(7):
            msg = f"Invalid temp channel index: {temp_ch_idx}"
        if self.meas_daemon.calibration_mode_enabled.is_set():
            msg = "Calibration already in process. Please wait!"
        if msg:
            logger.error(msg)
            self.api.send_response("calibrate_temp_channel", msg, False)
            self.api.push_error_str(msg)
            return
        # Instance data required by measurement_thread_acquire_cal_data()
        self.adc_key = adc_key
        self.temp_ch_idx = temp_ch_idx
        self.value_key = value_key
        # Get calibration resistor value and current calibration state
        # from config. Config must be populated with resistance value in advance.
        self.state.config_update_lock.acquire()
        temp_ch_conf = self.state.conf["adcs"][adc_key]["temp_chs"][temp_ch_idx]
        temp_ch_conf[value_key] = cal_resistance
        wh_a = temp_ch_conf["cal_wh_a"]
        wh_b = temp_ch_conf["cal_wh_b"]
        # If both channels have previous calibration results,
        # first invalidate old calibration.
        # Zero would evaluate as false, so no direct comparison
        if False not in (wh_a, wh_b):
            temp_ch_conf["cal_wh_a"] = False
            temp_ch_conf["cal_wh_b"] = False
        self.state.config_update_lock.release()
        logger.debug(f"Got current calibration values: {wh_a} and {wh_b}")
        # If both channels have previous calibration results,
        # first invalidate old calibration
        logger.info(
            f"Acquiring calibration data for resistance value: {cal_resistance}\n"
            f"ADC: ({adc_key},  temp channel: {temp_ch_idx}, value: {value_key})"
        )
        # This blocks until data is acquired.
        # Makes the measurement deamon thread acquire data and
        # write cal_wh_a and cal_wh_b directly into state.conf.
        self._trigger_acquisition_wait_for_data()
        # Read newly acquired data values
        self.state.config_update_lock.acquire()
        wh_a = temp_ch_conf["cal_wh_a"]
        wh_b = temp_ch_conf["cal_wh_b"]
        self.state.config_update_lock.release()
        # Calculate calibration results and write to state.conf
        logger.info(f"New calibration values: {wh_a} and {wh_b}")
        if False in (wh_a, wh_b):
            logger.info(f"Need second calibration result for channel")
            self.api.send_response("calibrate__temp_channel",
                                    json.dumps(self.state.conf["adcs"])
                                    )
            return
        # If this is the second calibration point for the calibration procedure
        try:
            self.state.config_update_lock.acquire()
            r_a = temp_ch_conf["cal_r_a"]
            r_b = temp_ch_conf["cal_r_b"]
            r_s = (r_a - r_b) / (wh_a - wh_b)
            r_offset = r_s * wh_a - r_a
            temp_ch_conf["r_s"] = r_s
            temp_ch_conf["r_offset"] = r_offset
            self.state.config_update_lock.release()
            logger.debug(f"r_s: {r_s},  r_offset: {r_offset}")
            self.api.send_response("calibrate__temp_channel",
                                    json.dumps(self.state.conf["adcs"])
                                    )
        except Exception as e:
            self.state.config_update_lock.release()
            logger.exception(e)
            self.api.send_response("calibrate__temp_channel",
                                   json.dumps(str(e)),
                                   False
                                   )

    # Called from measurement thread when its self.calibration_mode_enabled is set.
    def measurement_thread_acquire_cal_data(self):
        logger.debug(f"{self.adc_key},  {self.temp_ch_idx},  {self.value_key}:  "
                     "Acquiring calibration data"
                     )
        adc_obj = self.meas_daemon.adc_objs[self.adc_key]
        adc_conf = self.state.conf["adcs"][self.adc_key]
        adc_temp_ch_conf = adc_conf["temp_chs"][self.temp_ch_idx]
        N_REF = adc_conf["r_ref"]["r_s"] / adc_conf["r_ref"]["r_ref"]
        adc_mux_seq = [
            # Resistance reference channel  first,
              getattr(adc_def, adc_conf["r_ref"]["mux"]) << 4
            | getattr(adc_def, adc_conf["aincom"]["mux"]),
            # followed by the temperature sensor channel
              getattr(adc_def, adc_temp_ch_conf["mux"]) << 4
            | getattr(adc_def, adc_conf["r_ref"]["mux"]),
        ]
        adc_offsets = np.array([
            adc_conf["r_ref"]["adc_offset"],
            adc_temp_ch_conf["adc_offset"]
        ])
        # From now, update adc_buf cyclically with new ADC samples and
        # calculate results with averaged data.
        adc_obj.read_sequence(adc_mux_seq, self.adc_buf[0])
        for j in range(1, self.FILTER_SIZE):
            # Do the data acquisition of the multiplexed input channels
            adc_obj.read_continue(adc_mux_seq, self.adc_buf[j])
        # Average of input samples without offset correction
        adc_avg = np.average(self.adc_buf, axis=0)
        # Elementwise operation (np.array):
        adc_unscaled = adc_avg - adc_offsets
        # Calculate resistances for wheatstone bridge setup
        wh_factor = wheatstone_factor(adc_unscaled[1], adc_unscaled[0], N_REF)
        if self.value_key == "cal_r_a":
            logger.debug(f"Setting wheatstone factor cal_wh_a: {wh_factor}")
            adc_temp_ch_conf["cal_wh_a"] = wh_factor
        else:
            logger.debug(f"Setting wheatstone factor cal_wh_b: {wh_factor}")
            adc_temp_ch_conf["cal_wh_b"] = wh_factor

    def _trigger_acquisition_wait_for_data(self):
        self.meas_daemon.cal_data_ready.clear()
        self.meas_daemon.calibration_mode_enabled.set()
        if not self.meas_daemon.cal_data_ready.wait(timeout=30):
            logger.error("Timeout in _trigger_acquisition_wait_for_data!")
        # meas_daemon.calibration_mode_enabled is cleared in mesurement thread