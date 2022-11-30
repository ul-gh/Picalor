import Vue from 'vue'
import router from './router'
import vuetify from './plugins/vuetify'
import useStoreApi from './api/useStoreApi.js';
import MqttWebsocketsApi from './api/mqtt_websockets_api.js';
import PicalorApp from './PicalorApp.vue'

Vue.config.productionTip = false

const api_conf = {
  hosts: ["isoflux1.local", "isoflux.local", "isoflux", "localhost", "169.254.207.204"],
  ports: [9001, 9001, 9001, 9001, 9001],
  path: "/mqtt",
  useSSL: false,
  timeout: 15,
  data_topic: "data/picalor/core",
  cmd_req_topic: "cmd/picalor/core/req",
  cmd_resp_topic: "cmd/picalor/core/resp",
  id_prefix: "picalor_gui_",
};

const api = new MqttWebsocketsApi(api_conf);

const {
  state,
  dispatch,
} = useStoreApi(api);

const picalor_app = {
  router,
  vuetify,
  render: h => h(PicalorApp),

  data() {
    return {
      api_conf,
    };
  },

  computed: {
    state: () => state,
  },

  methods: {
    dispatch,
  },
};

const app = new Vue(picalor_app);

app.$mount('#app');

// Debug:
window.app = app;
