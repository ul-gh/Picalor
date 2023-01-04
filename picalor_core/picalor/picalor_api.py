import logging
import json
from typing import Callable
from picalor.picalor_mqtt import PicalorMqtt

logger = logging.getLogger("picalor_api")

class PicalorActions():
    def __init__(self, api, core, state):
        self.api = api
        self.core = core
        self.state = state
        # Automatically populate the actions dictionary below
        # using the method names defined in this class
        def is_method(name):
            attr = getattr(self, name)
            return callable(attr) and not name.startswith("__")
        action_names = filter(is_method, dir(self))
        # Dictionary containing the methods from this class
        self.actions = {key: getattr(self, key) for key in action_names}

    # Actions are callables mapped by indexing the instance of this class:
    # action = picalor_actions[action_name]
    # response = action(value)
    def __getitem__(self, cmd: str) -> Callable:
        return self.actions[cmd]

    # Action definitions
    def get__config(self, _):
        return self.state.conf.as_json()

    # API response with new config will be sent from measurement thread
    def upload_norestart__config(self, config):
        self.state.conf.set_norestart__config(config)

    # API response with new config will be sent from measurement thread
    def upload__config(self, config):
        self.state.conf.set__config(config)

    # API response with new config will be sent from measurement thread
    def upload_save__config(self, config):
        self.state.conf.set_save__config(config)
    
    def set__power_offset(self, values_list):
        for ch_idx, power in values_list:
            self.core.measurement_daemon.set_power_offset(ch_idx, power)
        return json.dumps(values_list)
    
    def set__power_gain(self, values_list):
        for ch_idx, power in values_list:
            self.core.measurement_daemon.set_power_gain(ch_idx, power)
        return json.dumps(values_list)
    
    def set__datalog_enabled(self, value):
        self.core.measurement_daemon.set_datalog_enabled(value)
        return json.dumps(value)

    def clear__datalog(self, _):
        self.core.measurement_daemon.clear_datalog()
        return json.dumps(True)
    
    def tare__power(self, ch_idx):
        self.core.measurement_daemon.tare_power(ch_idx)
        return json.dumps(ch_idx)
    
    def calibrate__temp_channel(self, cal_args):
        self.core.measurement_daemon.calibrator.calibrate_channel(
            cal_args["adc_key"],
            cal_args["temp_ch_idx"],
            cal_args["value_key"],
            cal_args["cal_resistance"]
        )
        return json.dumps(self.state.conf.adcs)
    
    # Saves and responds immediately as save__results is a blocking call
    # (waits only very briefly for spinlock)
    def save__results(self, _):
        return json.dumps(self.state.results.save_to_file())
    
    def poweroff(self, value):
        if value is True:
            logger.warning("Poweroff requested...")
            self.api.send_response("poweroff")
            self.core.poweroff()
        else:
            raise ValueError('Power OFF: Send "true" value to power off')


class PicalorApi():
    def __init__(self, core, state):
        self.core = core
        self.state = state
        self.actions = PicalorActions(self, core, state)
        # For the time being, there is only an MQTT remote API.
        self.frontends = [
            PicalorMqtt(self, state.conf["mqtt"]),
            # PicalorHttp(self, state),
            # PicalorCmdline(self, state),
            # PicalorXlsxExporter(self, state),
            # PicalorCsvExporter(self, state),
        ]

    # Called from frontend
    def dispatch_cmd(self, cmd, value):
        try:
            action = self.actions[cmd]
            response_json = action(value)
            if response_json is not None:
                self.send_response(cmd, response_json)
        except Exception as e:
            msg = f"Error in API command handler.\nError details: {e}"
            logger.exception(msg)
            # String returned is valid JSON
            self.send_response(cmd, f'"Core: {msg}"', success=False)

    # "push" means publishing on the data topic channel
    def push_live_data(self):
        json_str = self.state.results.as_json()
        for frontend in self.frontends:
            frontend.push_data_json("results", json_str)

    # "push" means publishing on the data topic channel
    def push_error_str(self, message):
        for frontend in self.frontends:
            frontend.push_error_str(json.dumps(message))

    # Response to a query command from the connected frontends
    def send_response(self, cmd_name, response_json="true", success=True):
        for frontend in self.frontends:
            frontend.send_response(cmd_name, response_json, success)

    def start_frontends(self):
        for frontend in self.frontends:
            try:
                frontend.launch_client_thread()
            except Exception as e:
                msg = f"Failed to launch frontend: {str(frontend)}\nError: {e}"
                logger.exception(msg)
                raise

    def stop_frontends(self):
        for frontend in self.frontends:
            try:
                # This is supposed to be a blocking call with a timeout
                frontend.stop_client_thread(10)
            except Exception as e:
                msg = f"Error stopping frontend: {str(frontend)}\nError: {e}"
                logger.exception(msg)