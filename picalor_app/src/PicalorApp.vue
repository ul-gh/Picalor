<template>
<v-app>
  <v-snackbar
    top
    v-model="state.snack_note_visible"
    :timeout="8000"
  >
    <span style="white-space: pre-wrap;">{{ state.snack_note_text }}</span>
    <!-- Vuetify 3 -->
    <!-- <template v-slot:actions>
      <v-btn
        color="blue"
        variant="text"
        @click="state.snack_note_visible = false"
      >
        Close
      </v-btn>
    </template> -->
    <template v-slot:action="{ attrs }">
      <v-btn
        text
        color="blue"
        v-bind="attrs"
        @click="state.snack_note_visible=false"
      >
        Close
      </v-btn>
    </template>
  </v-snackbar>
  <v-navigation-drawer app permanent>
    <template v-slot:prepend>
      <v-list-item three-line>
        <v-list-item-avatar>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 27.452 66.148">
            <path fill="red" d="M13.307 66.146l-2.897-16.43 3.2 4.572 4.042-23.543L0 40.936
              10.97 0h10.46L9.885 30.02l17.568-10.143-9.084 35.147 5.178-3.5-10.24 14.624"/>
          </svg>
        </v-list-item-avatar>
        <v-list-item-content>
          <v-list-item-title>Picalor</v-list-item-title>
          <v-list-item-subtitle :class="state.api_connected ? '' : 'red--text font-weight-bold'">
            {{ state.api_connected ? "MQTT connection: OK" : "MQTT disconnected!" }}
          </v-list-item-subtitle>
          <v-list-item-subtitle :class="state.config_stale ? 'red--text font-weight-bold' : ''">
            {{ state.config_stale ? "Config changed!" : "Live updates: ON" }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
      <!-- <div class="pa-2 d-flex justify-center">
        <v-btn
            v-if="state.config_stale && state.api_connected"
            :loading="state.loading"
            :disabled="state.loading"
            color="warning"
            class="ml-2 white--text"
            @click="dispatch('upload__config')">
            <v-icon dark>mdi-arrow-top-right-thick</v-icon>Apply/Upload
        </v-btn>
      </div> -->
    </template>

    <v-divider></v-divider>

    <v-list>
      <v-list-item-group v-model="page_selected_idx" color="primary">
        <v-list-item
            v-for="route in $router.options.routes"
            :key="route.name"
            @click="$router.push(route.path)"
            link
        >
          <v-list-item-icon>
              <v-icon>{{ route.icon }}</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title>{{ route.name }}</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list-item-group>
    </v-list>

    <template v-slot:append>
      <div v-if="state.errors_highlighted">
        <div class="text-center text-caption">Error Log (Click to acknowledge)!</div>
        <v-textarea
          :value="state.error_log.join('\n')"
          @click="dispatch('acknowledge__errors')"
          @click:clear="dispatch('clear__errors')"
          class="d-block text-caption font-weight-black"
          readonly
          outlined
          clearable
          color="red"
          background-color="#FFCDD2"
        >
        </v-textarea>
      </div>
      <!-- <div class="text-center text-caption">State Log</div>
      <v-textarea
        :value="state.state_log.join('\n')"
        @click:clear="state.state_log = []"
        clearable
        readonly
        filled
      >
      </v-textarea> -->
      <div class="pa-2 d-flex justify-center">
        <v-btn
            color="red"
            class="ml-2 white--text"
            @click="confirm_poweroff">
            <v-icon dark>mdi-power-off</v-icon>Power OFF
        </v-btn>
      </div>
    </template>
  </v-navigation-drawer>

  <v-main>
    <keep-alive>
      <router-view></router-view>
    </keep-alive>
  </v-main>

</v-app>
</template>

<script>
export default {
  name: 'PicalorApp',
  data() {
    return {
      page_selected_idx: 0,
  };},
  methods: {
    confirm_poweroff() {
      if (confirm('Power OFF Picalor measurement hardware?')) {
        this.dispatch('poweroff');
      }
    },
  },
  beforeCreate() {
    this.state = this.$root.state;
    this.dispatch = this.$root.dispatch;
  },
}
</script>

<style src="./fonts/roboto/css/roboto.css"></style>
<style src="./fonts/mdi/css/materialdesignicons.min.css"></style>
<!-- vuetify.css -->
<style scoped>
</style>
