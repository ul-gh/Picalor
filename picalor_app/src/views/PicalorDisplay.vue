<template>
<v-container fluid>
  <v-row justify="center">
    <v-col cols="12" lg="7">
      <v-card>
        <v-card-text id="power_graph" style="width: 100%; height:600px;"></v-card-text>
      </v-card>
    </v-col>
    <v-col  cols="12" lg="5">
      <v-card>
      <div id="power_bar_chart" style="width: 100%; height:600px;"></div>
      </v-card>
    </v-col>
  </v-row>

  <v-row justify="center">
    <v-col>
      <v-card>
        <DisplayTable
          title = "Measurement Display Settings"
          empty_text="No Results Received"
          @content_changed="set_measurements_active"
          :headers="display_table_headers"
          :items="display_table_rows"
        >
          <template v-slot:item-actions-append="{ index }">
            <v-btn
              :loading="state.loading"
              :disabled="state.loading"
              color="secondary"
              class="white--text"
              small
              rounded
              @click="dispatch('tare__power', index)"
            >
              Tare Power
            </v-btn>
          </template>
          <template v-slot:footer-prepend>
            <v-switch
              label="Enable Datalog"
              v-model="state.config.measurements.datalog_enabled"
              @change="v => dispatch('activate__datalog', v)"
              :autofocus="true"
              class="ml-5"
            >
            </v-switch>
            <v-btn
              class="ml-2 white--text"
              color="primary"
              :loading="state.loading"
              :disabled="state.loading"
              @click="dispatch('save__results')"
            >
              <v-icon>mdi-content-save</v-icon>Save Datalog
            </v-btn>
            <a href="/savedata/" target="_blank">
              <v-btn
                class="ml-2 white--text"
                color="secondary"
              >
                <v-icon>mdi-download</v-icon>Download
              </v-btn>
            </a>
            <v-btn
              class="ml-2 white--text"
              color="red"
              :loading="state.loading"
              :disabled="state.loading"
              @click="confirm__clear__datalog()"
            >
              <v-icon>mdi-delete</v-icon>Clear Datalog
            </v-btn>
            <!-- <v-btn
              class="ml-2"
              :loading="state.loading"
              :disabled="state.loading"
              @click="dispatch('load__config')"
            >
              <v-icon>mdi-cog-refresh</v-icon>Reload Config
            </v-btn> -->
          </template>
        </DisplayTable>
      </v-card>
    </v-col>
  </v-row>
</v-container>
</template>

<script>
// Imported as a global instead as echarts loads too slowly via vue-sfc-loader..
import * as echarts from "echarts";
//import * as echarts from '../../uibuilder/vendor/echarts/dist/echarts.esm.min.js';
import DisplayTable from "../widgets/DisplayTable.vue";

export default {
    components: {
      DisplayTable,
    },

    data() { return {
      meas_index: 0,
      display_table_rows: [],
      display_table_headers: [
        {
          text: "Active",
          value: "active",
          input_type: "switch",
          sortable: false,
        },
        {
          text: "Info",
          value: "info",
          sortable: false,
        },
        {
          text: "Power [W]",
          value: "power_w",
          digits: 1,
          sortable: false,
        },
        {
          text: "Temp Up",
          value: "t_upstream",
          digits: 3,
          sortable: false,
        },
        {
          text: "Temp Dn",
          value: "t_downstream",
          digits: 3,
          sortable: false,
        },
        {
          text: "Flow [g/s]",
          value: "flow_g_sec",
          digits: 3,
          sortable: false,
        },
      ],
    };},

    watch: {
      "state.config.display_settings": {
        handler() {
          this.update_chart_config();
        },
        deep: true,
      },
      "state.config.measurements"() {
        this.update_chart_config();
      },
      "state.results.measurements"() {
        this.update_displaydata();
      },
    },

    methods: {
      confirm__clear__datalog() {
        confirm('Delete Datalog?') && this.dispatch('clear__datalog');
      },
      set_measurements_active(display_rows) {
        const active_flags = Array.from(display_rows, ch => ch.active);
        this.dispatch("set_upload_norestart__measurements_active", active_flags);
        this.update_chart_config();
      },
      update_chart_config() {
        const active_series_names = [];
        // First empty array is later filled with time axis values.
        // More rows are filled in below representing the power graph time series.
        const line_graph_series = [];
        for (const [i, ch] of this.state.config.measurements.chs.entries()) {
          if (ch.active) {
            active_series_names.push(ch.info);
            line_graph_series.push(
              {
                name: ch.info,
                type: 'line',
                //stack: 'Total',
                showSymbol: false,
                seriesLayoutBy: "row",
                // Important: Axis configuration.
                // First row is time ("x") axis, other rows are power ("y") values
                encode: {x: 0, y: i+1},
              }
            );
          }
        }
        // Draw bar chart
        this.bar_chart.setOption(
          {
            title: {
              text: 'Power Measurements',
              left: 'center',
            },
            tooltip: {
              valueFormatter: v => typeof(v) === "number" ? v.toFixed(3) : v,
            },
            xAxis: {
              name: "Measurement",
              nameLocation: "center",
              nameGap: 20,
              data: active_series_names,
            },
            yAxis: {
              name: "Power /W",
              min: this.state.config.display_settings.power_chart_min_w,
              max: this.state.config.display_settings.power_chart_max_w,
            },
            series: [
              {
                name: 'Power /W',
                type: 'bar',
                label: {
                  show: true,
                  position: 'top',
                  formatter: ({value: v}) => typeof(v) === "number" ? v.toFixed(3) : v,
                },
                //label: {show: true, position: 'inside'},
                data: [],
              }
            ]
          },
          // Do not merge with existing options object but re-create instance..
          true
        );
        this.power_graph.setOption(
          {
            title: {
              text: 'Power Chart',
              left: 'center',
            },
            tooltip: {
              trigger: 'axis',
              valueFormatter: v => typeof(v) === "number" ? v.toFixed(3) : v,
            },
            legend: {
              //data: Array.from(active_series_names, name => ({name})),
              top: '30',
            },
            grid: {
              left: '3%',
              right: '4%',
              bottom: '3%',
              containLabel: true
            },
            toolbox: {
              feature: {
                saveAsImage: {}
              }
            },
            xAxis: {
              name: "Time /s",
              nameGap: 20,
              type: "value",
              nameLocation: "center",
              min: 0,
              max: "dataMax",
            },
            yAxis: {
              name: "Power /W",
              type: "value",
              min: this.state.config.display_settings.power_chart_min_w,
              max: this.state.config.display_settings.power_chart_max_w,
            },
            dataset: {
              source: Array(1 + this.state.config.measurements.chs.length).fill([]),
              sourceHeader: false,
            },
            series: line_graph_series,
          },
          // Do not merge with existing options object but re-create instance..
          true
        );
      },
      update_displaydata() {
        //console.log((Date.now()/1000).toFixed(0))
        const table_rows = [];
        const bar_chart_power = [];
        for (const [i, ch] of this.state.results.measurements.chs.entries()) {
          const ch_conf = this.state.config.measurements.chs[i];
          const flow_g_sec = ch.flow_kg_sec * 1000;
          table_rows.push(Object.assign({active: ch_conf.active, flow_g_sec}, ch));
          // Generate bar chart data
          if (ch_conf.active) {
            bar_chart_power.push(ch.power_w);
          }
        }
        // This is a reactive property, thus table is updated
        this.display_table_rows = table_rows;
        // Update bar chart
        if ("bar_chart" in this) {
          this.bar_chart.setOption({
            series: [
              {data: bar_chart_power},
            ],
          });
        }
        // Update power graph if data_log is enabled
        if ("power_graph" in this && this.state.results.data_log) {
          const time = this.state.results.data_log.time_s;
          // Array of as many measurement data series as are configured
          const power_series = this.state.results.data_log.power_w;
          this.power_graph.setOption({
            dataset: {source: [time].concat(power_series)},
          });
        }
      },
      resize_charts() {
        const pg_el = document.getElementById("power_graph");
        if (this.bar_chart === null
            || this.bar_chart === undefined
            || pg_el === null
        ) {
          return;
        }
        this.power_graph.resize({width: pg_el.offsetWidth - 30});
        this.bar_chart.resize();
      },
    },

    beforeCreate() {
      // Shortcuts for global state store
      this.state = this.$root.state;
      // Methods
      this.dispatch = this.$root.dispatch;
    },

    mounted() {
        window.dpy = this;
        this.throttling_timer = null;
        // initialize bar chart
        this.bar_chart = echarts.init(
            document.getElementById("power_bar_chart"),
            null,
            {renderer: "svg"}
        );
        // initialize power graph
        this.power_graph = echarts.init(
            document.getElementById('power_graph'),
            null,
            {renderer: "svg"}
        );
        addEventListener("resize", () => {
          // Does nothing for invalid timer ID
          clearTimeout(this.throttling_timer);
          this.throttling_timer = setTimeout(this.resize_charts, 250);
        });
        setTimeout(this.resize_charts, 1000);
    },

    activated() {
      this.dispatch("load__config");
    },
};
</script>
