import threading
import logging
import json
import tomlkit
from datetime import datetime
from importlib.resources import files
from pathlib import Path

logger = logging.getLogger("picalor_state_store")
PACKAGE_NAME = "picalor"

class PicalorState():
    """Picalor application runtime state storage

    This is separated into configuration storage, results storage
    and related mutex locks.
    """
    def __init__(self):
        # Core application configuration store with a mapping of configuration
        # changing and application controlling actions.
        self.conf = PicalorConfig(self)
        # Measurement results are stored here and pushed to the view models
        self.results = PicalorResults(self, self.conf)
        # Threading locks for modification of the respecitve store items
        self.config_update_lock = threading.Lock()
        self.results_update_lock = threading.Lock()
        # Events notifying the measurement daemon to take action
        self.config_updated = threading.Event()
        self.config_updated_norestart = threading.Event()


class PicalorConfig():
    """Core configuration for Picalor application

    Saving to file must be triggered explicitly.
    """
    def __init__(self,
                 store,
                 filename="picalor_config.toml",
                 default_filename="picalor_default_config.toml"
                 ):
        self.store = store
        # When updating config while application is running, this is preset with
        # updated values and self.config_updated is set. Configuration is then updated
        # when self.commit_pending_updates is called from the application thread
        self.pending_config_updates = {}
        store_dir = Path.home().joinpath(f".{PACKAGE_NAME}")
        store_dir.mkdir(exist_ok=True)
        self.file_obj = store_dir.joinpath(filename)
        self.default_file_obj = files(PACKAGE_NAME).joinpath(default_filename)
        # When initializing new, we assume the main thread is not yet running,
        # no restarting of sensors needed..
        self.restore_from_file(initialize = True)
        self._save_to_file_requested = False

    # Not thread-safe!
    # Called from constructor with initialize = True, then directly
    # setting the state representation
    # TBD: implement reset-config button..
    def restore_from_file(self, initialize=False):
        logger.info(f"Reading config file: {str(self.file_obj)}")
        try:
            new_config = tomlkit.loads(self.file_obj.read_text())
        except FileNotFoundError:
            logger.warning(f'Config file not found. Restoring defaults.')
            new_config = tomlkit.loads(self.default_file_obj.read_text())
        # See above
        if initialize:
            self.tomlkit_doc = new_config
        else:
            self.store.config_update_lock.acquire()
            # Overwrites all previous changes
            self.pending_config_updates = new_config
            self.store.config_updated.set()
            self.store.config_update_lock.release()

    # Thread-safe, can be called any time
    def as_json(self):
        self.store.config_update_lock.acquire()
        json_str = json.dumps(self.tomlkit_doc).replace("NaN", "null")
        self.store.config_update_lock.release()
        return json_str

    # Thread-safe, called from API.
    # Sends notify response, also triggers send from measurement thread.
    # Compared to "set_config", this does not restart sensors.
    def set_norestart__config(self, new_config):
        self.store.config_update_lock.acquire()
        self.pending_config_updates.update(new_config)
        self.store.config_updated_norestart.set()
        self.store.config_update_lock.release()

    # Thread-safe, called from API.
    # Sends notify response, also triggers send from measurement thread.
    # This restarts all sensors.
    def set__config(self, new_config):
        # Assuming we want sampling to take place at integer second timestamps
        self.store.config_update_lock.acquire()
        # This attribute is always false on the Picalor core side
        self.pending_config_updates.update(new_config)
        self.store.config_updated.set()
        self.store.config_update_lock.release()

    # Thread-safe, called from API.
    # Same as set__config, but triggers a save to file from the measurement thread
    def set_save__config(self, new_config):
        self._save_to_file_requested = True
        self.set__config(new_config)

    # Not thread-safe - To be called from application thread ONLY!
    # Update all existing config items with values from pending_config_updates. 
    def measurement_thread_commit_pending_updates(self):
        logger.debug("Updating configuration from pending obj...")
        for key, value in self.pending_config_updates.items():
            if key in self.tomlkit_doc:
                self.tomlkit_doc[key] = value
            else:
                logger.error(f"Key not found in picalor configuration: {key}")
        self.pending_config_updates = {}
        if self._save_to_file_requested:
            self.measurement_thread_save_to_file()
            self._save_to_file_requested = False
            return True
        else:
            return False

    # Not thread-safe! Handled from mesurement thread
    def measurement_thread_save_to_file(self):
        logger.info(f"Saving config to file: {str(self.file_obj)}")
        textcontent = tomlkit.dumps(self.tomlkit_doc)
        try:
            self.file_obj.write_text(textcontent)
            return self.file_obj.name
        except OSError as e:
            logger.error(f"Could not write to file! Error: {str(e)}")
            raise

    # Direct element access is not thread safe - only used from mesurement thead
    def __getitem__(self, key):
        return self.tomlkit_doc[key]

    def __setitem__(self, key, value):
        self.tomlkit_doc[key] = value

    def __delitem__(self, key):
        del self.tomlkit_doc[key]


class PicalorResults():
    """Measurement state representation for Picalor application, with a
    list of all views.

    Data is generated in the core application.
    A push to the views is triggered from there.
    """
    def __init__(self,
                 store,
                 conf,
                 filename_base="picalor_measurement_results"
                 ):
        self.store = store
        self.conf = conf
        self.filename_base = filename_base
        self.save_dir = Path.home().joinpath(f".{PACKAGE_NAME}/savedata")
        self.save_dir.mkdir(exist_ok=True)
        # While application is running, this is continuously updated with
        # calculated values from ADC and other measurements.
        # Reading this directly is not thread-safe!
        # This is instantaneous results
        self.data = {}
        self.initialize_new()

    # This is thread-safe and can be called any time
    def as_json(self):
        self.store.results_update_lock.acquire()
        json_str = json.dumps(self.data).replace("NaN", "null")
        self.store.results_update_lock.release()
        return json_str

    # Not thread-safe!
    def initialize_from_file(self, filename):
        logger.info(f"Looking for previous measurements in savefile: {filename}")
        try:
            file_obj = Path(filename)
            self.store.results_update_lock.acquire()
            restored = json.loads(file_obj.read_text())
            self.data.update(restored)
            logger.info(f'Restored previous measurements: {restored["title"]}')
            return True
        except FileNotFoundError:
            logger.info(f'No savefile found. Initializing Picalor with clean state')
            return False
        finally:
            self.store.results_update_lock.release()

    # This is thread-safe and can be called any time
    def save_to_file(self):
        date_time_string = datetime.now().isoformat("_", "seconds")
        filename = f"{self.filename_base}_{date_time_string}.json"
        file_obj = self.save_dir.joinpath(filename)
        logger.info(f"Saving Picalor measurements to file: {str(file_obj)}")
        try:
            file_obj.write_text(self.as_json())
            return file_obj.name
        except OSError as e:
            logger.error(f"Could not write to file! Error: {str(e)}")
            raise

    # Not thread-safe!
    def initialize_new(self):
        logger.debug("Initializing result storage..")
        conf = self.conf
        data = {
            "title": "Picalor Measurement Results",
            "measurements": {
                "idx": 0,
                "chs": [],
            },
            "adcs": {},
            "flow_sensors": [],
            "data_log": None
        }
        for ch_conf in conf["measurements"]["chs"]:
            data["measurements"]["chs"].append({
                "info": ch_conf["info"],
                "t_upstream": None,
                "t_downstream": None,
                "flow_kg_sec": None,
                "power_w": None,
            })
        for adc in conf["adcs"].keys():
            # ADC raw data
            data["adcs"][adc] = {
                "r_ref": {"adc_unscaled": None},
                "temp_chs": []
            }
            for _ in conf["adcs"][adc]["temp_chs"]:
                data["adcs"][adc]["temp_chs"].append({
                    "adc_unscaled": None,
                    "resistance": None,
                    "temperature": None,
                })
        for sensor_config in conf["flow_sensors"]:
            if sensor_config["type"] == "fixed":
                flow = sensor_config["FLOW_LITER_SEC"]
            else:
                flow = None
            data["flow_sensors"].append({
                "info": sensor_config["info"],
                "liter_sec": flow,
            })
        self.data = data

    # Not thread-safe!
    def measurement_thread_initialize_datalog(self):
        conf = self.conf
        log = {
            "start_time": None,
            "scan_interval_s": conf["measurements"]["scan_interval_s"],
            "info": [],
            "time_s": [],
            "t_upstream": [],
            "t_downstream": [],
            "flow_kg_sec": [],
            "power_w": [],
        }
        for ch_conf in conf["measurements"]["chs"]:
            log["info"].append(ch_conf["info"])
            log["t_upstream"].append([])
            log["t_downstream"].append([])
            log["flow_kg_sec"].append([])
            log["power_w"].append([])
        now = datetime.now().isoformat(" ", "seconds")
        log["start_time"] = now
        self.data["data_log"] = log

    # Direct element access is not thread-safe!
    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def __delitem__(self, key):
        del self.data[key]