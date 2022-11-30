/** @file useStoreApi.js
 *
 * MQTT API implementation for Picalor application
 */

//import { reactive, ref, watch } from "vue";
import Vue from 'vue'

/** @brief Returns initialized state object and dispatch function in a wrapper object
 *
 * Foo
 */
export default function useStoreApi(api) {
  const debug_state_updates = false;
  //const state = reactive({
  const state = Vue.observable({
    loading: false,
    errors_highlighted: false,
    // Set to false on first reception of config update from the backend
    config_stale: true,
    api_connected: false,
    // State of snackbar message element for global notification display
    snack_note_visible: false,
    snack_note_text: "Message...",
    error_log: [],
    state_log: [],
    // Picalor measurement results
    results: {
      measurements: {
        chs: [
          {
            "info": "M1 (ADC1)",
            "t_upstream": 0.47116119813317886,
            "t_downstream": 8.086074947616833,
            "flow_kg_sec": 0.010965994129450277,
            "power_w": 255.11321167889957
          },
        ],
      },
      adcs: {
        adc_1: {
          r_ref: {
              adc_unscaled: 3324042.5
          },
          temp_chs: [
              {
                  adc_unscaled: -269363.0,
                  resistance: 1001.8413111097782,
                  temperature: 0.47116119813317886
              },
          ]
        },
      },
      flow_sensors: [
        {
          "info": "Fixed Flow 1",
          "liter_sec": 0.01
        },
      ],
      data_log: {
        start_time: null,
        scan_interval_s: 10,
        info: [],
        time_s: [],
        t_upstream: [],
        t_downstream: [],
        flow_kg_sec: [],
        power_w: [],
      },
    },
    config: {
      display_settings: {
        power_chart_min_w: 0,
        power_chart_max_w: 150,
      }, // end of display_settings
      fluids: {
        glycol_60: {},
        water: {},
      },
      measurements: {
        scan_interval_s: 10,
        datalog_enabled: false,
        FILTER_SIZE: 2,
        default_ch: {
          info: "M1 (ADC1)",
          active: true,
          adc_device: "adc_1",
          // Upstream and downstream Hardware temperature sensing channels
          temp_ch_up: 0,
          temp_ch_dn: 1,
          // Platinum RTD base (0°C) resistance values, upstream and downstream sensor
          // r_0_up, r_0_dn: 1000.000,
          r_0_up: 1000.000,
          r_0_dn: 1000.000,
          // Resistance offset for external wiring resistance upstream and downstream
          r_wires_up: 0.000,
          r_wires_dn: 0.000,
          flow_sensor: 0,
          // This ADC channel is used for fluid density calculation.
          // This ADC channel must be configured in at least one of all measurements
          // as the flow meter temperature channel is not individually scanned.
          flow_sensor_temp_ch: 0,
          fluid: "glycol_60",
          power_offset: 0.0,
          power_gain: 1.0,
        },
        chs: [
          {
            info: "M1 (ADC1)",
            active: true,
            adc_device: "adc_1",
            // Upstream and downstream Hardware temperature sensing channels
            temp_ch_up: 0,
            temp_ch_dn: 1,
            // Platinum RTD base (0°C) resistance values, upstream and downstream sensor
            // r_0_up, r_0_dn: 1000.000,
            r_0_up: 1000.000,
            r_0_dn: 1000.000,
            // Resistance offset for external wiring resistance upstream and downstream
            r_wires_up: 0.000,
            r_wires_dn: 0.000,
            flow_sensor: 0,
            // This ADC channel is used for fluid density calculation.
            // This ADC channel must be configured in at least one of all measurements
            // as the flow meter temperature channel is not individually scanned.
            flow_sensor_temp_ch: 0,
            fluid: "glycol_60",
            power_offset: 0.0,
            power_gain: 1.0,
          },
        ]
      },
      flow_sensors: [],
      adcs: {
        adc_1: {
          ads1256_config: {},
          aincom: {},
          r_ref: {},
          temp_chs: [
            {
              info: "Cold Inlet",
              mux: "NEG_AIN1",
              adc_offset: 0,
              // Series resistance (bridge high-side) of Pt1000 sensor channels in Ohms
              // r_s: 9962.59,
              r_s: 9962.00,
              // Resistance offset for HW channel calibration.
              r_offset: 0.000,
              // Two-point-calibration known resistances (calibration standards)
              cal_r_a: 1098.5,
              cal_r_b: 2191.1,
              // Corresponding internal read-out values (wheatstone factor)
              cal_wh_a: 1.0,
              cal_wh_b: 1.0,
            },
          ]
        },
      },
    mqtt: {},
    }, // end of config
  }); // end of state

  const actions = {
    async load__config() {
      try {
        const new_config = await api.query("get__config");
        _update_config(new_config);
        return true;
      } catch (e) {
        _log_error(`Error loading configuation: ${e}!\n`
                   + "Is Picalor hardware connected and core module running?");
        return false;
      }
    },
    async activate__datalog(value) {
      state.loading = true;
      let success = false;
      try {
        success = await api.query("set__datalog_enabled", value);
        _show_success("Data log enabled on device!");
        state.loading = false;
      } catch (e) {
        _log_error(e);
      }
      return success;
    },
    set__config_measurements_chs(value) {
      state.config_stale = true;
      state.config.measurements.chs = value;
      // FIXME: Trigger watchers. There is a better way..
      state.config.measurements = Object.assign({}, state.config.measurements);
    },
    set__config_adcs(value) {
      state.config_stale = true;
      state.config.adcs = value;
      // FIXME: Trigger watchers. There is a better way..
      state.config.adcs = Object.assign({}, state.config.adcs);
    },
    set__config(value) {
      state.config_stale = true;
      state.config = value;
    },
    async set_upload_norestart__config_adcs(value) {
      state.config_stale = true;
      try {
        state.config.adcs = value;
        // FIXME: Trigger watchers. There is a better way..
        state.config.adcs = Object.assign({}, state.config.adcs);
        const new_conf = await api.query("upload_norestart__config", state.config);
        _update_config(new_conf);
      } catch (e) {
        _log_error(`Error setting configuation: ${e}!`);
      }
    },
    async set_upload_norestart__config(value) {
      state.config_stale = true;
      try {
        state.config = value;
        const new_conf = await api.query("upload_norestart__config", state.config);
        _update_config(new_conf);
      } catch (e) {
        _log_error(`Error setting configuation: ${e}!`);
      }
    },
    async set_upload_norestart__measurements_active(value) {
      state.config_stale = true;
      for (const [i, v] of value.entries()) {
        state.config.measurements.chs[i].active = v;
      }
      try {
        // FIXME: Trigger watchers. There is a better way..
        state.config.measurements = Object.assign({}, state.config.measurements);
        const new_conf = await api.query("upload_norestart__config", state.config);
        _update_config(new_conf);
      } catch (e) {
        _log_error(`Error setting configuation: ${e}!`);
      }
    },
    async upload__config() {
      state.loading = true;
      try {
        const new_conf = await api.query("upload__config", state.config);
        _update_config(new_conf);
        _show_success("Config uploaded to device!");
        state.loading = false;
      } catch (e) {
        _log_error(`Error setting configuation: ${e}!`);
      }
    },
    async upload_save__config() {
      state.loading = true;
      try {
        const new_conf = await api.query("upload_save__config", state.config);
        _update_config(new_conf);
        _show_success("Config saved on device!");
        state.loading = false;
      } catch (e) {
        _log_error(`Error setting configuation: ${e}!`);
      }
    },
    async save__results() {
      state.loading = true;
      let filename = "";
      try {
        filename = await api.query("save__results");
        const msg = `Results saved to:    ${filename}\nDownload is ready!`;
        _show_success(msg);
        state.loading = false;
      } catch (e) {
        _log_error(`Error saving file: ${e}!`);
      }
      return filename;
    },
    async clear__datalog() {
      state.loading = true;
      let success = false;
      try {
        success = await api.query("clear__datalog");
        _show_success("Datalog deleted!");
        state.loading = false;
      } catch (e) {
        _log_error(e);
      }
      return success;
    },
    async tare__power() {
      state.loading = true;
      let success = false;
      try {
        success = await api.query("clear__datalog");
        _show_success("Datalog deleted!");
        state.loading = false;
      } catch (e) {
        _log_error(e);
      }
      return success;
    },
    async calibrate__temp_channel(adc_key, temp_ch_idx, value_key) {
      state.loading = true;
      let success = false;
      try {
        // Modulus as the index can be from a linear list of more than one ADC
        temp_ch_idx %= state.config.adcs[adc_key].temp_chs.length;
        state.config.adcs = await api.query(
          "calibrate__temp_channel",
          {adc_key, temp_ch_idx, value_key}
        );
        _show_success(`ADC ${adc_key}, Channel ${temp_ch_idx} calibrated!`);
        state.loading = false;
      } catch (e) {
        _log_error(e);
      }
      return success;
    },
    log__error(e_or_msg) {
      _log_error(e_or_msg);
    },
    acknowledge__errors() {
      state.errors_highlighted = false;
    },
    clear__errors() {
      state.error_log = [];
      state.errors_highlighted = false;
    },
    show__success(msg) {
      _show_success(msg);
    },
    async reconnect__api() {
      try {
        return await api.reconnect();
      } catch (e) {
        _log_error(e);
      }
    },
    async poweroff() {
      state.loading = true;
      let success = false;
      try {
        success = await api.query("poweroff");
        _show_success("Picalor hardware shutdown committed!");
        state.loading = false;
      } catch (e) {
        _log_error(e);
      }
      return success;
    },
  };


  // Returns undefined or a promise object for await inside an async function
  function dispatch(action, value=true, ...args) {
    if (Object.hasOwn(actions, action)) {
      return actions[action](value, ...args);
    } else {
      return _log_error(`Dispatch: No such action: ${action}`)
    }
  }


  function _log_error(e) {
    console.error(e);
    state.error_log.push(String(e));
    state.errors_highlighted = true;
  }

  function _show_success(msg) {
    state.snack_note_text = msg;
    state.snack_note_visible = true;
  }

  // Called after all API queries returning an updated config response
  function _update_config(new_config) {
    if (debug_state_updates) {
      const value_str = JSON.stringify(new_config);
      console.log(`Updating config with object:\n${value_str}`);
    }
    for (const [k, v] of Object.entries(new_config)) {
      // Only accept pre-defined config attributes
      if (Object.hasOwn(state.config, k)) {
        state.config[k] = v;
      }
    }
    state.config_stale = false;
  }

  // Called by API callback when data topic channel receives a message
  function _cb_update_results(results) {
    // Receive results only when configuration is valid
    if (state.config_stale) {
      return;
    } 
    if (debug_state_updates) {
      const value_str = JSON.stringify(results);
      console.log(`Updating results with object:\n${value_str}`);
    }
    state.results = results;
  }

  async function _cb_on_api_connected() {
    await dispatch("load__config");
    state.api_connected = true;
    setTimeout(() => dispatch("acknowledge__errors"), 2000);
  }

  // Automatic reconnects are enabled, if this fails, user must reload page..
  function _cb_on_api_disconnect() {
    state.api_connected = false;
  }

  api.register_data_cb("results", _cb_update_results);
  api.register_data_cb("errors", msg => _log_error(`Core Error:\n${msg}`));
  api.register_on_connected_cb(_cb_on_api_connected);
  api.register_on_connection_lost_cb(_cb_on_api_disconnect);

  api.connect();

  return {
    state,
    dispatch,
  }
}
