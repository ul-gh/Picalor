<template align="start">
<div>
  <LiveEditTable
    title = "Measurement Calibration"
    empty_text="No Measurements Configured"
    :headers="headers"
    :rows_feedback="state.config.measurements.chs"
    :show_add_delete="false"
    row_key="info"
    @content_changed="rows => dispatch('set__config_measurements_chs', rows)"
  >
    <template v-slot:footer-prepend>
      <v-btn
          :loading="state.loading"
          :disabled="state.loading"
          color="warning"
          class="ml-2 white--text"
          @click="upload__config">
          <v-icon dark>mdi-arrow-top-right-thick</v-icon>Apply/Upload
      </v-btn>
      <v-btn
          :loading="state.loading"
          :disabled="state.loading"
          color="red"
          class="ml-2 white--text"
          @click="upload_save__config">
          <v-icon dark>mdi-content-save</v-icon>Upload and Save as Default
      </v-btn>
    </template>
  </LiveEditTable>
</div>
</template>

<script>
import LiveEditTable from "../widgets/LiveRowEditTable.vue";

export default {
  components: {
    LiveEditTable,
  },

  data() {
    return {
      headers: [
        {
          text: "Description",
          value: "info",
          input_type: "text",
          sortable: false,
        },
        {
          text: "Base Resistance Up",
          value: "r_0_up",
          input_type: "number",
          sortable: false,
        },
        {
          text: "Base Resistance Dn",
          value: "r_0_dn",
          input_type: "number",
          sortable: false,
        },
        {
          text: "Wiring Resistance Up",
          value: "r_wires_up",
          input_type: "number",
          sortable: false,
        },
        {
          text: "Wiring Resistance Dn",
          value: "r_wires_dn",
          input_type: "number",
          sortable: false,
        },
        {
          text: "Power Offset",
          value: "power_offset",
          input_type: "number",
          sortable: false,
        },
        {
          text: "Power Gain",
          value: "power_gain",
          input_type: "number",
          sortable: false,
        },
      ],
  };},

  methods: {
    async upload__config() {
      try {
        await this.dispatch("upload__config")
        this.snack_note_text = `Config uploaded to device!`;
      } catch (e) {
        this.snack_note_text = `Error uploading: ${e}`;
      }
      this.snack_note_visible = true;
    },
    async upload_save__config() {
      try {
        await this.dispatch("upload_save__config")
        this.snack_note_text = `Config uploaded to device!`;
      } catch (e) {
        this.snack_note_text = `Error uploading: ${e}`;
      }
      this.snack_note_visible = true;
    },
  },

  beforeCreate() {
      // Shortcuts for global state store
      this.state = this.$root.state;
      this.dispatch = this.$root.dispatch;
  },

  mounted() {
    // this.create_meas_conf_rows();
    window.mc = this;
  },
};
</script>