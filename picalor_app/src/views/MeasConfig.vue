<template align="start">
<v-container fluid>
  <v-row>
    <v-col>
    <CommonSettings></CommonSettings>
    </v-col>
  </v-row>
  <v-row>
    <v-col>
    <ChSetup adc_device="adc_1"></ChSetup>
    </v-col>
  </v-row>
  <v-row>
    <v-col>
    <MeasCalibration></MeasCalibration>
    </v-col>
  </v-row>
</v-container>
</template>

<script>
import CommonSettings from "../components/CommonSettings.vue"
import ChSetup from "../components/ChSetup.vue";
import MeasCalibration from "../components/MeasCalibration.vue";

export default {
  components: {
    CommonSettings,
    ChSetup,
    MeasCalibration,
  },

  methods: {
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