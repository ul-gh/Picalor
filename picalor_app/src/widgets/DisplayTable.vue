<template>
<v-card class="mx-auto mt-10" outlined>
  <v-card-title>{{title}}</v-card-title>
  <v-data-table
    :headers="headers_actions"
    :items="items"
    class="elevation-1" fixed-header
  >
    <v-divider inset></v-divider>
    <template v-slot:top>
      <slot name="top-prepend">
      </slot>
    </template>
    <!-- eslint-disable-next-line -->
    <template v-slot:footer.prepend>
      <slot name="footer-prepend">
      </slot>
    </template>
    <template
      v-for="header in headers"
      v-slot:[column_slot(header.value)]="{ item }"
    >
      <v-switch
        :key="header.value"
        v-if='header.input_type === "switch"'
        v-model="item[header.value]"
        @change="emit_immediately"
        :autofocus="true"
      >
      </v-switch>
      <!-- <v-text-field
        :key="header.value"
        v-else-if='header.input_type === "text"'
        v-model="item[header.value]" 
        :hide-details="true" :autofocus="true" dense single-line
      >
      </v-text-field> -->
      <span
        :key="header.value"
        v-else
      >
        {{format_display_cell(item, header)}}
      </span>
    </template>
    <!-- eslint-disable-next-line -->
    <template v-slot:item.actions="{ item, index }">
      <slot name="item-actions-append" :item="item" :index="index">
      </slot>
    </template>
    <template v-slot:no-data>
      <h2 class="font-weight-light">{{empty_text}}</h2>
    </template>
  </v-data-table>
</v-card>
</template>

<script>
export default {
  name: "DisplayTable",
  
  props: {
    title: String,
    headers: [],
    items: [],
    item_key: String,
    empty_text: String,
  },

  emits: ["content_changed"],

  computed: {
    headers_actions() {
      return this.headers.concat(
        {
          text: "Actions",
          value: "actions",
          sortable: false,
          width: "100px",
        }
      );
    },
  },

  data() {
    return {
    }
  },

  created() {
  },

  methods: {
    emit_immediately(){
      this.$emit('content_changed', this.items)
    },
    format_display_cell(item, header) {
      const value = item[header.value];
      if (Object.hasOwn(header, "digits") && typeof(value) === "number") {
        return value.toFixed(header.digits);
      } else {
        return value;
      }
    },
    column_slot(header_value_key) {
      return `item.${header_value_key}`;
    },
  },
};
</script>

<style scoped>
.theme--light.v-data-table.v-data-table--fixed-header thead th {
  background: #555;
  color: #fff;
}

.w-100 {
  width: 100%
}
</style>