import threading
import time
import math
import logging
from pipyadc import ADS1256, ADS1256_definitions, ADS1256_default_config
from picalor.picalor_measurement import Fluid, Measurement, Calibrator
from picalor.util_lib.flow_sensor import FlowSensorPulseType, FlowSensorFixed

logger = logging.getLogger("measurement_daemon")

class PicalorMeasurementDaemon():
    def __init__(self, pi, state, api):
        self.pi = pi
        self.state = state
        self.api = api
        # Will be set from _configure_and_start_sensors()
        self.adc_objs = {}
        self.flow_sensors = []
        # Will be set from _configure_measurements_enable_acquisition()
        self.measurements = []
        # Could be a subclass of this class but using composition
        self.calibrator = Calibrator(self, state, api)
        # Events controlling the measurement thread operation
        self.calibration_mode_enabled = threading.Event()
        self._datalog_enabled = threading.Event()
        self._clear_datalog_requested = threading.Event()
        self._acquisition_enabled = threading.Event()
        self.cal_data_ready = threading.Event()
        # Shutdown flag makes thread loop exit
        self._shutdown_requested = threading.Event()
        self._thread_obj = threading.Thread(
            target=self._measurement_thread,
            name="Measurement Thread",
            args=()
        )
        self._thread_obj.setDaemon(True)
        self._log_start_time = None
        self._log_time_digits = None

    def start(self):
        self._configure_and_start_sensors()
        self._configure_measurements_enable_acquisition()
        self._thread_obj.start()

    def stop(self):
        timeout = 12
        try:
            timeout += self.state.conf["measurements"]["scan_interval_s"]
        except (AttributeError, TypeError):
            pass
        self._shutdown_requested.set()
        if self._thread_obj is not None:
            self._thread_obj.join(timeout)
        self._stop_sensors_stop_acquisition()

    def set_power_offset(self, ch_idx, value):
        self.measurements[ch_idx].set_power_offset(value)

    def set_power_gain(self, ch_idx, value):
        self.measurements[ch_idx].set_power_gain(value)

    def tare_power(self, ch_idx):
        self.measurements[ch_idx].tare_power()
    
    # This clears the log when enabling the log (if not already enabled)
    def set_datalog_enabled(self, value):
        self.state.conf["measurements"]["datalog_enabled"] = value
        if value:
            self._datalog_enabled.set()
        else:
            self._datalog_enabled.clear()
    
    def clear_datalog(self):
        self._clear_datalog_requested.set()

    # When sensors are re-configured, the measurements also have to be
    # re-configured. This is why acquisition_enabled is cleared but not reset here.
    def _configure_and_start_sensors(self):
        logger.debug("_configure_and_start_sensors called from thread ID: "
                     f"{threading.current_thread().name}")
        # Initialise the ADCs and add instances here
        self.adc_objs = {}
        for key in self.state.conf["adcs"].keys():
            logger.info(f"Configuring ADC: {key}")
            adc_hw_conf = self._get_adc_hw_conf(key)
            logger.debug(f"adc_hw_conf.adcon: {adc_hw_conf.adcon}")
            logger.debug(f"adc_hw_conf.drate: {adc_hw_conf.drate}")
            adc_obj = ADS1256(adc_hw_conf, self.pi)
            adc_obj.cal_self()
            self.adc_objs[key] = adc_obj
        # Flow Sensors
        self.flow_sensors = []
        for i, conf in enumerate(self.state.conf["flow_sensors"]):
            sns_type = conf['type']
            logger.info(f"Configuring flow sensor {i} of type: {sns_type}")
            if sns_type == "pulse":
                self.flow_sensors.append(FlowSensorPulseType(self.pi, conf))
            elif sns_type == "fixed":
                self.flow_sensors.append(FlowSensorFixed(conf))

    def _stop_sensors_stop_acquisition(self):
        logger.debug("Stopping ADC and flow sensors")
        self._acquisition_enabled.clear()
        for adc in self.adc_objs.values():
            adc.stop()
        self.adc_objs = {}
        for sensor in self.flow_sensors:
            sensor.stop()
        self.flow_sensors = []

    def _get_adc_hw_conf(self, key):
        conf_dict = vars(ADS1256_default_config).copy()
        ads1256_config = self.state.conf["adcs"][key]["ads1256_config"]
        conf_dict.update(ads1256_config)
        # String configuration items must be converted to int flags
        # as defined in ADS1256_definitions
        conf_dict["drate"] = getattr(ADS1256_definitions, ads1256_config["drate"])
        adcon = 0x00
        for flag in ads1256_config["adcon"]:
            adcon |= getattr(ADS1256_definitions, flag)
        conf_dict["adcon"] = adcon
        # Using a type object allows accessing the dict items as attributes
        return type("adc_hw_config", (), conf_dict)

    # Setup arbitrary number of configured measurements - these can
    # be later re-configured, so this is a separate function
    def _configure_measurements_enable_acquisition(self):
        name = threading.current_thread().name
        logger.debug(f"_configure_measurements called from thread: {name}")

        try:
            n = len(self.state.conf["measurements"]["chs"])
            logger.info(f"Number of heat measurement channels configured: {n}")
            n = self.state.conf["measurements"]["FILTER_SIZE"]
            logger.info(f"Output values averaged over {n} ADC samples.")
            # Setup fluid objects
            f_conf = self.state.conf["fluids"]
            self.fluids = {key: Fluid(f_conf[key]) for key in f_conf.keys()}
            # Setup measurement objects
            self.measurements = []
            for i, ch_conf in enumerate(self.state.conf["measurements"]["chs"]):
                try:
                    adc_obj = self.adc_objs[ch_conf["adc_device"]]
                    flow_sensor = self.flow_sensors[ch_conf["flow_sensor"]]
                    fluid = self.fluids[ch_conf["fluid"]]
                except Exception as e:
                    msg = f"Configuration error configuring measurement {i}"
                    logger.exception(msg)
                    self.api.push_error_str(msg)
                    self._acquisition_enabled.clear()
                    return
                m = Measurement(self.state, i, adc_obj, flow_sensor, fluid)
                self.measurements.append(m)

        except Exception as e:
            msg = f"Error configuring measurements!\nError: {e}"
            logger.exception(msg)
            self.api.push_error_str(msg)
            self._acquisition_enabled.clear()
            return
        self.set_datalog_enabled(self.state.conf["measurements"]["datalog_enabled"])
        self._acquisition_enabled.set()

    def _acquire_measurement_data(self):
        # The flow meter channel for each power measurement can use a different
        # temperature measurement channel, while extra ADC acquisiton cycles
        # only for the flow meter would be wasteful.
        # This is why first, all temperature channels have to be acquired
        for measurement in self.measurements:
            measurement.scan_sensors()
        # Flow sensor read-out is non-blocking, we read all
        for i, sensor in enumerate(self.flow_sensors):
            flow = sensor.read_liter_sec()
            self.state.results["flow_sensors"][i]["liter_sec"] = flow
        # Afterwards we can calculate and publish the interdependent results
        for measurement in self.measurements:
            measurement.calculate_power()
        if self._datalog_enabled.is_set():
            if (self._clear_datalog_requested.is_set()
                or self.state.results["data_log"] is None
                ):
                self._clear_datalog_requested.clear()
                self.state.results.measurement_thread_initialize_datalog()
                self._log_start_time = time.time()
                self.api.send_response("clear__datalog")
            log = self.state.results["data_log"]
            t = round(time.time() - self._log_start_time, self._log_time_digits)
            log["time_s"].append(t)

            for ch, data in enumerate(self.state.results["measurements"]["chs"]):
                log["t_upstream"][ch].append(data["t_upstream"])
                log["t_downstream"][ch].append(data["t_downstream"])
                log["flow_kg_sec"][ch].append(data["flow_kg_sec"])
                log["power_w"][ch].append(data["power_w"])



    def _measurement_thread(self):
        logger.debug(f"Measurement thread: {threading.current_thread().name}")
        scan_interval_s = int(self.state.conf["measurements"]["scan_interval_s"])
        self._log_time_digits = -int(math.log10(scan_interval_s))
        t_next_sample = 1 + int(time.time()) + scan_interval_s
        while True:
            if self._shutdown_requested.is_set():
                return
            self._measurement_thread_time = time.time()
            delta_t = t_next_sample - self._measurement_thread_time
            t_next_sample += scan_interval_s
            if delta_t > 0.0:
                time.sleep(delta_t)
            else:
                logger.warning("Timeout occurred - beware of missing data!")
            # Check for configuration updates and apply if needed.
            # This is supposed to be a re-configuration without adding or
            # removal of channels and without the need to restart all sensors.
            if self.state.config_updated_norestart.is_set():
                self.state.config_update_lock.acquire()
                self.state.config_updated_norestart.clear()
                # Writes pending updates to state.conf
                self.state.conf.measurement_thread_commit_pending_updates()
                self.state.config_update_lock.release()
                self.api.send_response("upload_norestart__config", self.state.conf.as_json())
            # If the base configuration has been changed, ADC and flow sensors
            # must be restarted and measurements must be set up new 
            if self.state.config_updated.is_set():
                self._stop_sensors_stop_acquisition()
                self.state.config_update_lock.acquire()
                self.state.config_updated.clear()
                # Writes pending updates to state.conf
                did_save = self.state.conf.measurement_thread_commit_pending_updates()
                self.state.config_update_lock.release()
                self.state.results.initialize_new()
                self._clear_datalog_requested.set()
                self._configure_and_start_sensors()
                self._configure_measurements_enable_acquisition()
                if did_save:
                    self.api.send_response("upload_save__config", self.state.conf.as_json())
                else:
                    self.api.send_response("upload__config", self.state.conf.as_json())
            # Flag set by Calibrator instance
            if self.calibration_mode_enabled.is_set():
                self.state.config_update_lock.acquire()
                self.calibrator.measurement_thread_acquire_cal_data()
                self.state.config_update_lock.release()
                self.calibration_mode_enabled.clear()
                # Waited for by Calibrator instance
                self.cal_data_ready.set()
            # Main operation mode of measurement daemon
            elif self._acquisition_enabled.is_set():
                self.state.results_update_lock.acquire()
                self._acquire_measurement_data()
                self.state.results_update_lock.release()
                self.api.push_live_data()