/* MQTT over websockets client for Picalor app
 *
 * See also Paho MQTT Javascript client documentation at:
 * https://www.eclipse.org/paho/files/jsdoc/Paho.MQTT.Client.html
 * 
 * MQTT channel/topic setup:
 *   # Last part is comand name/key: "cmd/picalor/core/req/[cmd-name]"
 *   CORE_CMD_REQ_TOPIC = "cmd/picalor/core/req"
 *   
 *   # This is divided further into:
 *   # "cmd/picalor/core/resp/ok/[cmd-name]" for command success responses and
 *   # "cmd/picalor/core/resp/err/[cmd-name]" for command error responses.
 *   CORE_CMD_RESP_TOPIC = "cmd/picalor/core/resp"
 *   
 *   # Telemetry data. Last part is data subkey: "data/picalor/core/[data-key]"
 *   CORE_DATA_TOPIC = "data/picalor/core"
 * 
 * Ulrich Lukas 2022-11-11
 */
import Paho from "paho-mqtt"

export default class MqttWebsocketsApi {
    constructor(api_conf) {
        this.id = `picalor_gui_${Math.random().toString(0xF).slice(2, 8)}`;
        this.api_conf = api_conf;
        // Empty containers for API user callbacks
        this._cmd_resp_cbs = {};
        this._data_cbs = {};
        this._on_connected_cbs = [];
        this._on_connection_lost_cbs = [];
        // Initialize MQTT client and set client callbacks
        this.client = new Paho.Client(
            api_conf.hosts[0],
            api_conf.ports[0],
            api_conf.path,
            this.id
        );
        this.client.onMessageArrived = this._on_message.bind(this);
        this.client.onConnected = this._on_connected.bind(this);
        this.client.onConnectionLost = this._on_connection_lost.bind(this);
    }

    async query(cmd, value=true) {
        return new Promise((resolve, reject) => {
            let timer_id = null;
            const resolver = (value, success) => {
                clearTimeout(timer_id);
                if (success) {
                    resolve(value);
                } else {
                    reject(value);
                }
            };
            const cb_idx = this.register_cmd_resp_cb(cmd, resolver);
            timer_id = setTimeout(
                () => {
                    this.remove_cmd_resp_cb(cmd, cb_idx);
                    reject(`Timeout occurred for command: ${cmd}`);
                },
                this.api_conf.timeout * 1000
            )
            this.send(cmd, value);
        });
    }

    send(cmd, value=true) {
        const topic = `${this.api_conf.cmd_req_topic}/${cmd}`;
        const payload = JSON.stringify(value);
        this.client.send(topic, payload);
    }

    async reconnect() {
        await this.disconnect();
        return this.connect();
    }

    connect() {
        const on_connect = async (all_resolve, all_reject) => {
            const subscribe_topics = [
                `${this.api_conf.data_topic}/+`,
                `${this.api_conf.cmd_resp_topic}/+/+`
            ];
            const subscription_promises = Array.from(
                subscribe_topics,
                topic => new Promise(
                    (resolve, reject) => {
                        const callbacks = {
                            onSuccess: () => {
                                console.log(`Subscribed to: ${topic}`);
                                resolve();
                            },
                            onFailure: ({errorMessage: msg}) => {
                                console.error(
                                    `While subscribing to topic: ${topic}\n`
                                    + `Received MQTT error: ${msg}`
                                );
                                reject({topic, msg});
                            }
                        };
                        this.client.subscribe(topic, callbacks);
                    }
                )
            );
            try {
                await Promise.all(subscription_promises);
                all_resolve();
            } catch {
                all_reject();
            }

        };
        const on_failure = (reject, msg) => {
            console.error(msg);
            reject("Could not connect to MQTT broker");
        };
        return new Promise((resolve, reject) => {
            const connect_options = {
                hosts: this.api_conf.hosts,
                ports: this.api_conf.ports,
                useSSL: this.api_conf.useSSL,
                timeout: this.api_conf.timeout,
                reconnect: true,
                onSuccess: () => on_connect(resolve, reject),
                onFailure: ({errorMessage: msg}) => on_failure(reject, msg),
            };
            this.client.connect(connect_options);
        });
    }

    // We do not want to trigger reconnects, so the error callbacks are not
    // called from this function
    disconnect() {
        return new Promise((resolve) => {
            const callbacks = {
                onSuccess: () => {
                    this.client.disconnect();
                    console.log("MQTT client disconnected");
                    resolve();
                },
                onFailure: () => {
                    console.warn("MQTT unsubscribe error");
                    this.client.disconnect();
                    resolve();
                }
            };
            try {
                this.client.unsubscribe("#", callbacks);
            } catch {
                // client.unsubscribe fails when client is already disconnected.
                // client.disconnect also fails when already disconnected.
                // These are only warnings, no need to take any further actions.
                console.warn("Already disconnected");
                resolve();
            }
        });
    }

    // Adds a callback for the telemetry data topic under "data_subtopic" endpoint
    // Callback signature is: data_cb(value).
    // Returns callback id number (cb_id)
    register_data_cb(data_subtopic, cb) {
        if (Object.hasOwn(this._data_cbs, data_subtopic)) {
            return this._data_cbs[data_subtopic].push(cb) - 1;
        } else {
            this._data_cbs[data_subtopic] = [cb];
            return 0;
        }
    }
    remove_data_cb(data_subtopic, cb_id) {
        if (Object.hasOwn(this._data_cbs, data_subtopic)) {
            this._data_cbs[data_subtopic].splice(cb_id, 1);
            if (this._data_cbs[data_subtopic].length === 0) {
                delete this._data_cbs[data_subtopic];
            }
        }
    }

    // This adds a callback for a single command response.
    // Callback signature is: cmd_resp_cb(success, value).
    // Returns callback id number (cb_id)
    register_cmd_resp_cb(cmd_name, cb) {
      if (Object.hasOwn(this._cmd_resp_cbs, cmd_name)) {
          return this._cmd_resp_cbs[cmd_name].push(cb) - 1;
      } else {
          this._cmd_resp_cbs[cmd_name] = [cb];
          return 0;
      }
    }
    remove_cmd_resp_cb(cmd_name, cb_id) {
        if (Object.hasOwn(this._cmd_resp_cbs, cmd_name)) {
            this._cmd_resp_cbs[cmd_name].splice(cb_id, 1);
            if (this._cmd_resp_cbs[cmd_name].length === 0) {
                delete this._cmd_resp_cbs[cmd_name];
            }
        }
    }

    register_on_connected_cb(cb) {
        return this._on_connected_cbs.push(cb) - 1;
    }

    register_on_connection_lost_cb(cb) {
        return this._on_connection_lost_cbs.push(cb) - 1;
    }

    _on_connected(reconnected, uri) {
        if (reconnected) {
            console.warn("MQTT reconnected!");
        }
        console.log(`Connected to MQTT host: ${uri}`);
        try {
            for (const cb of this._on_connected_cbs) {
                cb();
            }
        } catch (e) {
            console.error(e);
        }
    }

    _on_connection_lost({errorMessage}) {
        console.warn(`MQTT connection lost: ${errorMessage}`);
        try {
            for (const cb of this._on_connection_lost_cbs) {
                cb();
            }
        } catch (e) {
            console.error("Foooo");
            console.error(e);
        }
    }

    _on_message({destinationName: topic, payloadString: payload}) {
        try {
            const parts = topic.split('/');
            const key = parts.at(-1);
            const value = JSON.parse(payload.replaceAll("NaN", "null"));
            // "data/picalor/core/+"
            if (topic.startsWith(this.api_conf.data_topic)) {
                // For topic: "data/picalor/core/foo_bar":
                // calls "foo_bar" callbacks with payload value as parameter
                if (Object.hasOwn(this._data_cbs, key)) {
                    for (const data_cb of this._data_cbs[key]) {
                        data_cb(value);
                    }
                }
            // "cmd/picalor/core/resp/+/+"
            } else if (topic.startsWith(this.api_conf.cmd_resp_topic)) {
                // Check if this is a command success
                const success = parts.at(-2) === "ok";
                // Calls "foo_bar" callbacks with payload value and success=true
                // as parameters if topic is "cmd/picalor/core/resp/ok/foo_bar".
                // Same for "cmd/picalor/core/resp/err/foo_bar" but success=false.
                if (Object.hasOwn(this._cmd_resp_cbs, key)) {
                    for (const cmd_resp_cb of this._cmd_resp_cbs[key]) {
                        cmd_resp_cb(value, success);
                    }
                }
            }
        } catch (e) {
            console.error(e);
        }
    }
}