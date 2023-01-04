<template align="start">
  <v-container fluid>
    <LiveEditTable
      title = "ADC Calibration"
      empty_text="No ADCs Configured"
      :headers="headers"
      :rows_feedback="adc_conf_rows"
      :show_add_delete="false"
      row_key="info"
      @content_changed="update_config_adcs"
    >
      <template v-slot:footer-actions="{ editing, do_save, do_cancel }">
        <v-btn
          v-if="editing"
          color="warning"
          class="ml-2 white--text"
          @click="do_cancel()"
        >
          <v-icon dark>mdi-cancel</v-icon>Cancel Edit
        </v-btn>
        <v-btn
          :loading="state.loading"
          :disabled="state.loading"
          color="red"
          class="ml-2 white--text"
          @click="do_save(); dispatch('upload_save__config')">
          <v-icon dark>mdi-content-save</v-icon>
          Store Permanently (Calibrate channels first!)
        </v-btn>
      </template>
      <template v-slot:item-actions-append="{ item, index, do_save }">
        <v-btn
          :loading="state.loading"
          color="secondary"
          class="white--text"
          small
          rounded
          @click="do_save(); dispatch('calibrate__temp_channel', item.adc_key, index, 'cal_r_a', item.cal_r_a)"
          :disabled="item.cal_wh_a !== false && item.cal_wh_b === false"
        >
          Calibrate Resistance A
        </v-btn>&nbsp;
        <v-btn
          :loading="state.loading"
          color="secondary"
          class="white--text"
          small
          rounded
          @click="do_save(); dispatch('calibrate__temp_channel', item.adc_key, index, 'cal_r_b', item.cal_r_b)"
          :disabled="item.cal_wh_a === false && item.cal_wh_b !== false"
        >
          Calibrate Resistance B
        </v-btn>
      </template>
    </LiveEditTable>
  </v-container>
</template>

<script>
import LiveEditTable from "../widgets/LiveEditTable.vue";

export default {
  components: {
    LiveEditTable,
  },

  data() {
    return {
      headers: [
        {
          text: "ADC",
          value: "adc_key",
          input_type: "",
          sortable: false,
        },
        {
          text: "Description",
          value: "info",
          input_type: "",
          sortable: false,
        },
        {
          text: "Calibration Resistance A [Ω]",
          value: "cal_r_a",
          input_type: "number",
          min: 10,
          max: 10e3,
          digits: 1,
          sortable: false,
        },
        {
          text: "Calibration Resistance B [Ω]",
          value: "cal_r_b",
          input_type: "number",
          min: 10,
          max: 10e3,
          digits: 1,
          sortable: false,
        },
        {
          text: "Resulting Bias R [Ω]",
          value: "r_s",
          input_type: "",
          digits: 3,
          sortable: false,
        },
        {
          text: "Resulting Offset R [Ω]",
          value: "r_offset",
          input_type: "",
          digits: 3,
          sortable: false,
        },
      ],
    };
  },

  computed: {
    adc_conf_rows() {
      const adc_conf_rows = [];
      for (const [adc_key, adc_conf] of Object.entries(this.state.config.adcs)) {
        for (let temp_ch of adc_conf.temp_chs) {
          temp_ch = Object.assign({adc_key}, temp_ch);
          adc_conf_rows.push(temp_ch);
        }
      }
      return adc_conf_rows;
    },
  },

  methods: {
    update_config_adcs(rows_in) {
      const config_adcs = Object.assign({}, this.state.config.adcs);
      for (let [i, temp_ch] of rows_in.entries()) {
        // One linear list index is used for multiple ADCs haveing the same
        // number of physical input channels. ADC key is stored as an attribute
        // of the object computed above as "adc_conf_rows".
        // Modulus converts the linear list index back into an index into each
        // ADCs configuration array.
        i %= config_adcs[temp_ch.adc_key].temp_chs.length;
        config_adcs[temp_ch.adc_key].temp_chs[i] = temp_ch;
        this.dispatch("set__config_adcs", config_adcs);
      }
    },
    confirm_leave_unsaved() {
      if (this.state.config_stale) {
        return confirm("Unsaved changes present. Really leave the page?");
      } else {
        return true;
      }
    },
    on_before_unload(e) {
      if (!this.confirm_leave_unsaved()) {
        // Cancel
        e.preventDefault();
        // Chrome requires returnValue to be set
        e.returnValue = '';
      } 
    },
  },

  beforeCreate() {
    this.state = this.$root.state;
    this.dispatch = this.$root.dispatch;
  },
  created() {
    window.addEventListener('beforeunload', this.on_before_unload);
  },
  activated() {
    this.dispatch("load__config");
  },
  beforeRouteLeave (_to, _from, next) {
    if (!this.confirm_leave_unsaved()){
      next(false);
    } else {
      next();
    }
  },
  beforeDestroy() {
    window.removeEventListener('beforeunload', this.on_before_unload);
  },
};
</script>