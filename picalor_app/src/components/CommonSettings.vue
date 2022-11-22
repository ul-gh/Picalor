<template align="start">
  <v-card>
    <v-card-title>Common Settings</v-card-title>
    <v-card-text>
    <v-row>
      <v-col>
      <v-text-field
        class="ms-5"
        type="text"
        label="MQTT API hosts (separated by space)"
        :value="$root.api_conf.hosts.join(' ')"
        @change="reconnect_api_to"
      >
      </v-text-field>
      </v-col>
    </v-row>
    <v-col>
    <v-row>
      <v-text-field
        class="ms-5"
        type="number"
        label="Power Graph Y MIN"
        v-model="state.config.display_settings.power_chart_min_w"
      >
      </v-text-field>
      <v-text-field
        class="ms-5"
        type="number"
        label="Power Graph Y MAX"
        v-model="state.config.display_settings.power_chart_max_w"
      >
      </v-text-field>
      <v-text-field
        disabled
        class="ms-5"
        type="number"
        label="Bar Chart Y MIN"
        v-model="state.config.display_settings.power_chart_min_w"
      >
      </v-text-field>
      <v-text-field
        disabled
        class="ms-5"
        type="number"
        label="Bar Chart Y MAX"
        v-model="state.config.display_settings.power_chart_max_w"
      >
      </v-text-field>
    </v-row>
      <v-btn
          :loading="state.loading"
          :disabled="state.loading"
          color="warning"
          class="ml-2 white--text"
          @click="dispatch('upload__config')">
          <v-icon dark>mdi-arrow-top-right-thick</v-icon>Apply/Upload
      </v-btn>
      <v-btn
          :loading="state.loading"
          :disabled="state.loading"
          color="red"
          class="ml-2 white--text"
          @click="dispatch('upload_save__config')">
          <v-icon dark>mdi-content-save</v-icon>Upload and Save as Default
      </v-btn>
    <v-row>
    </v-row>
    </v-col>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  methods: {
    async reconnect_api_to(hosts_str){
      const hosts_arr = hosts_str.split(" ");
      this.$root.api_conf.hosts = hosts_arr;
      this.$root.api_conf.ports = Array(hosts_arr.length).fill(9001);
      this.$root.api.reconnect();
    },
  },

  beforeCreate() {
      // Shortcuts for global state store
      this.state = this.$root.state;
      this.dispatch = this.$root.dispatch;
  },

  mounted() {
    // this.create_meas_conf_rows();
    window.cs = this;
  },
};
</script>