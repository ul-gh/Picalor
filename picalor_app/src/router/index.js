import Vue from 'vue'
import VueRouter from 'vue-router'
import PicalorDisplay from '../views/MainDisplay.vue'
import PicalorMeasConfig from '../views/MeasConfig.vue'
import PicalorAdcCalibration from '../views/AdcCalibration.vue'

Vue.use(VueRouter)

const picalor_routes = {
  PicalorDisplay: {
      path: '/',
      name: 'Picalor Live Display',
      icon: 'mdi-chart-line',
      component: PicalorDisplay,
  },
  PicalorMeasConfig: {
      path: '/measurement-config',
      name: 'Measurement Config',
      icon: 'mdi-tune-vertical',
      component: PicalorMeasConfig,
  },
  PicalorAdcCalibration: {
      path: '/adc-calibration',
      name: 'ADC Calibration',
      icon: 'mdi-wrench-cog',
      component: PicalorAdcCalibration,
  },
  Default: {
      // Catch-all route
      path: '/:pathMatch(.*)*',
      redirect: '/',
  },
};

const router = new VueRouter({
  mode: "hash",
  routes: Object.values(picalor_routes),
})

export default router