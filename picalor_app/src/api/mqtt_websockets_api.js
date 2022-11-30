import Paho from "paho-mqtt"

/** # Async Query-Response Web API using MQTT over Websockets
 *
 * See also Paho MQTT Javascript client documentation at:
 * https://www.eclipse.org/paho/files/jsdoc/Paho.MQTT.Client.html
 * 
 * 
 * ### MQTT host/connection and channel/topic setup:
 * 
 * All settings are configured by passing a mandatory configuration object
 * to the constructor, with the following fields:
 * 
 * @code 
 * const api_conf = {
 *     hosts: ["picalor.local", "169.254.207.204"],
 *     ports: [9001, 9001],
 *     path: "/mqtt",
 *     useSSL: false,
 *     timeout: 15,
 *     data_topic: "data/picalor/core",
 *     cmd_req_topic: "cmd/picalor/core/req",
 *     cmd_resp_topic: "cmd/picalor/core/resp",
 *     id_prefix: "picalor_gui_",
 * };
 * @endcode
 * 
 * * Requests are sent using the command name as endpoint: "{cmd_req_topic}/{cmd-name}"  
 * Example topic for requests: <b>"cmd/picalor/core/req/{cmd-name}"</b>
 *   
 * * Responses arrive under an "ok" or "err" subtopic for success or failure results:
 * "{cmd_resp_topic}/ok/{cmd-name}" for command success responses and
 * "{cmd_resp_topic}/err/{cmd-name}" for command error responses.  
 * Example topic for responses:  <b>"cmd/picalor/core/resp/ok/{cmd-name}"</b>
 *   
 * * For async or streaming results like telemetry data, callbacks can be registered
 * on the data_topic channel, extended with a data subkey as endpoint:
 * "{data_topic}/{data-key}"  
 * Example topic for telemetry data:  <b>"data/picalor/core/{data-key}"</b>
 * 
 * Ulrich Lukas 2022-11-11
 */
export default class MqttWebsocketsApi {
/// @publicsection
    /** Constructor.
     * @param api_conf See class documentation for structure of the api_conf object
     */
    constructor(api_conf) {
        this.api_conf = api_conf;
        this.id = `${api_conf.id_prefix}${Math.random().toString(0xF).slice(2, 8)}`;
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

    /** Send a cmd-value query to the message broker and resolve with the response
     *
     * The query is published on the {cmd_req_topic}/{cmd-name} topic,
     * with a payload consisting of the value argument as a JSON string.
     * 
     * Each query is supposed to be answered or acknowledged with a
     * response on the topic channel, i.e:
     * {cmd_resp_topic}/ok/{cmd-name} or {cmd_resp_topic}/err/{cmd-name}.
     * 
     * The response is supposed to contain a non-empty JSON string as payload.
     * 
     * @param cmd String name of the command
     * @param value Any Javascript object which can be sent as a JSON string
     * @return Promise resolving with the payload parsed as a Javascript object
     */
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

    /** Send a command to the broker <i>without</i> expecting return data.
     * @param cmd String name of the command
     * @param value Any Javascript object which can be sent as a JSON string
     */
    send(cmd, value=true) {
        const topic = `${this.api_conf.cmd_req_topic}/${cmd}`;
        const payload = JSON.stringify(value);
        this.client.send(topic, payload);
    }

    /** Disconnect followed by reconnection to MQTT broker
     *
     * @return Promise resolving with an array of all subscribed topics
     */
    async reconnect() {
        await this.disconnect();
        return this.connect();
    }

    /** Connect to confitured MQTT broker
     * 
     * @return Promise resolving with an array of all subscribed topics
     */
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
                                resolve(topic);
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

    /** Disconnect from MQTT broker.
     *
     * Here, we do not want to trigger reconnects, so this does not reject
     * or raise exceptions and error callbacks are not called.
     *
     * @return Promise with empty resolution
     */
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

    /** Add a generic callback for messages arriving on {data_topic}
     * 
     * Multiple callbacks can be registered for any data topic, these are
     * identified by a numeric ID, which is only valid for the data_cb registry.
     * 
     * @param data_subtopic String key value identifying the data. Used as topic endpoint.
     * @param cb Callback function. Signature is: data_cb(value)
     * @return Callback ID number (needed to un-register the cb)
     */
    register_data_cb(data_subtopic, cb) {
        if (Object.hasOwn(this._data_cbs, data_subtopic)) {
            return this._data_cbs[data_subtopic].push(cb) - 1;
        } else {
            this._data_cbs[data_subtopic] = [cb];
            return 0;
        }
    }
    /** Remove callback for data topic
     * 
     * @param data_subtopic String key value as used for registration of the CB
     * @param cb_id Callback ID number as returned by register_data_cb()
     */
    remove_data_cb(data_subtopic, cb_id) {
        if (Object.hasOwn(this._data_cbs, data_subtopic)) {
            this._data_cbs[data_subtopic].splice(cb_id, 1);
            if (this._data_cbs[data_subtopic].length === 0) {
                delete this._data_cbs[data_subtopic];
            }
        }
    }

    /** Add a callback for a single command response
     * 
     * Multiple callbacks can be registered for any data topic, these are
     * identified by a numeric ID, which is only valid for the cmd_resp_cb registry.
     * 
     * @param cmd_name String name of the command. Used as topic endpoint.
     * @param cb Callback function. Signature is: cmd_resp_cb(success, value)
     * @return Callback id number
     */
    register_cmd_resp_cb(cmd_name, cb) {
      if (Object.hasOwn(this._cmd_resp_cbs, cmd_name)) {
          return this._cmd_resp_cbs[cmd_name].push(cb) - 1;
      } else {
          this._cmd_resp_cbs[cmd_name] = [cb];
          return 0;
      }
    }
    /** Remove callback for command response topic
     * 
     * @param cmd_name String name as used for registration of the CB
     * @param cb_id Callback ID number as returned by register_cmd_resp_cb()
     */
    remove_cmd_resp_cb(cmd_name, cb_id) {
        if (Object.hasOwn(this._cmd_resp_cbs, cmd_name)) {
            this._cmd_resp_cbs[cmd_name].splice(cb_id, 1);
            if (this._cmd_resp_cbs[cmd_name].length === 0) {
                delete this._cmd_resp_cbs[cmd_name];
            }
        }
    }

    /** Register callback executed when connected to MQTT broker
     * 
     * @param cb Callback function, called without arguments 
     * @return Callback id number
     */
    register_on_connected_cb(cb) {
        return this._on_connected_cbs.push(cb) - 1;
    }

    /** Register callback executed when MQTT connection is lost
     * 
     * @param cb Callback function, called without arguments 
     * @return Callback id number
     */
    register_on_connection_lost_cb(cb) {
        return this._on_connection_lost_cbs.push(cb) - 1;
    }

/// @privatesection
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