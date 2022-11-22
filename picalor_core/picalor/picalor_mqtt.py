import time
import logging
import json
import paho.mqtt.client as mqtt_client

logger = logging.getLogger("picalor_mqtt")

class PicalorMqtt():
    """Picalor MQTT API frontend / remote client interface

    2022-08-21 Ulrich Lukas
    """
    def __init__(self, api, conf):
        self.api = api
        self.conf = conf
        self.data_topic = conf["CORE_DATA_TOPIC"]
        self.cmd_req_topic = conf["CORE_CMD_REQ_TOPIC"]
        self.cmd_resp_topic = conf["CORE_CMD_RESP_TOPIC"]
        # paho.mqtt.client
        self.backend = mqtt_client.Client()
        self.backend.on_connect = self._on_connect
        self.backend.on_message = self._on_message
    
    def push_data_json(self, key, json_str):
        self.backend.publish(f"{self.data_topic}/{key}", json_str)

    def push_error_str(self, message_str):
        self.backend.publish(f"{self.data_topic}/errors", message_str)

    def send_response(self, cmd, response="", success=True):
        topic = (
            f"{self.cmd_resp_topic}/ok/{cmd}" if success else
            f"{self.cmd_resp_topic}/err/{cmd}"
        )
        self.backend.publish(topic, response)

    def launch_client_thread(self):
        logger.info("Connecting to MQTT broker... ")
        self.backend.connect(str(self.conf["BROKER_HOST"]),
                             int(self.conf["MQTT_PORT"])
                             )
        self.backend.loop_start()
        ctr = 0
        while not self.backend.is_connected():
            ctr += 1
            time.sleep(1)
            if ctr > 30:
                self.backend.loop_stop()
                raise ConnectionError("Timeout while trying to connect! Is MQTT running?")
        logger.info("OK: Picalor MQTT client is running.")

    def stop_client_thread(self, timeout):
        self.backend.loop_stop()

    def _on_connect(self, client, _userdata, _flags, rc):
        logger.info(f"OK, Picalor MQTT connection established.")
        client.subscribe(f"{self.cmd_req_topic}/+")
        if rc == 0:
            pass
        else:
            raise IOError("Could not subscribe to MQTT command input topic")

    # We only subscribe to command topic, so this is only called for commands
    def _on_message(self, _client, _userdata, msg):
        try:
            # Last part of cmd topic is the actual command
            cmd = msg.topic.split("/")[-1]
            value = json.loads(msg.payload)
            logger.debug(f"Received cmd: {cmd} with value: {str(value)[:35]} (...)")
        except Exception as e:
            msg = f"MQTT error decoding msg topic or message content. Details:\n{e}"
            logger.exception(msg)
        # API call handles exceptions internally
        self.api.dispatch_cmd(cmd, value)