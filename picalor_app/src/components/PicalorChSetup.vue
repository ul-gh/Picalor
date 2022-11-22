<template align="start">
<div>
  <LiveEditTable
    :key="state.config_stale"
    title = "Measurement Channel Setup"
    empty_text="No Measurements Configured"
    :headers="headers"
    :rows_feedback="state.config.measurements.chs"
    :default_row="state.config.measurements.default_ch"
    row_key="info"
    @content_changed="rows => dispatch('set__config_measurements_chs', rows)"
  >
    <template v-slot:footer-prepend>
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
    </template>
  </LiveEditTable>
</div>
</template>

<script>
import LiveEditTable from "../widgets/LiveEditTable.vue";

export default {
  components: {
    LiveEditTable,
  },

  computed: {
    headers() {
      return [
        {
          text: "Description",
          value: "info",
          input_type: "text",
          sortable: false,
        },
        // active flag is set from PicalorDisplay tab
        {
          text: "ADC",
          value: "adc_device",
          input_type: "text",
          sortable: false,
        },
        {
          text: "Temp CH Up",
          value: "temp_ch_up",
          input_type: "number",
          min: 0,
          max: Object.values(this.state.config.adcs)[0].temp_chs.length - 1,
          digits: 0,
          sortable: false,
        },
        {
          text: "Temp CH Dn",
          value: "temp_ch_dn",
          input_type: "number",
          min: 0,
          max: Object.values(this.state.config.adcs)[0].temp_chs.length - 1,
          digits: 0,
          sortable: false,
        },
        {
          text: "Flow Sensor",
          value: "flow_sensor",
          input_type: "number",
          min: 0,
          max: this.state.config.flow_sensors.length - 1,
          digits: 0,
          sortable: false,
        },
        {
          text: "Flow Temp CH",
          value: "flow_sensor_temp_ch",
          input_type: "number",
          min: 0,
          max: Object.values(this.state.config.adcs)[0].temp_chs.length - 1,
          digits: 0,
          sortable: false,
        },
      ]
    },
  },

  beforeCreate() {
      // Shortcuts for global state store
      this.state = this.$root.state;
      this.dispatch = this.$root.dispatch;
  },

  mounted() {
    window.chs = this;
  },
};
</script>