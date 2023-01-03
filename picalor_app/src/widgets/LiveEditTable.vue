<template>
<v-card class="mx-auto mt-10" outlined>
  <v-card-title>{{title}}</v-card-title>
  <v-data-table
    :headers="headers_actions"
    :items="rows"
    class="elevation-1" fixed-header
  > 
    <v-divider inset></v-divider>
    <template v-slot:top>
      <slot name="top-prepend">
      </slot>
    </template>
    <!-- eslint-disable-next-line -->
    <template v-slot:footer.prepend>
      <v-toolbar flat color="white">
        <div class="d-flex w-100">
          <v-btn
              v-if="show_add_delete"
              color="primary"
              class="ml-2 white--text"
              @click="add_row">
              <v-icon dark>mdi-plus</v-icon>Add
          </v-btn>
          <slot
            name="footer-prepend"
          >
          </slot>
          <slot
            name="footer-actions"
            :editing="editing"
            :do_save="stop_save_edit"
            :do_cancel="cancel_edit"
          >
            <v-btn
              v-if="editing"
              color="warning"
              class="ml-2 white--text"
              @click="cancel_edit()"
            >
              <v-icon dark>mdi-cancel</v-icon>Cancel Edit
            </v-btn>
          </slot>
        </div>
      </v-toolbar>
    </template>
    <template
      v-for="header in headers"
      v-slot:[column_slot(header.value)]="{ item }"
    >
      <span :key="header.value">
        <v-switch
          v-if='header.input_type === "switch"'
          v-model="item[header.value]"
          @change="$emit('content_changed', rows)"
          :autofocus="true"
        >
        </v-switch>
        <v-text-field
          v-else-if='header.input_type === "text"'
          v-model="item[header.value]"
          :hide-details="true" :autofocus="true" dense single-line
        >
        </v-text-field>
        <!-- I don't know why only the number input is not reactive without the update_trigger approach.. -->
        <v-text-field
          v-else-if='header.input_type === "number"'
          :key="update_trigger"
          :value="format_number_cell(item, header)"
          @change="text => set_number_item(text, item, header)"
          :rules="[v => validate_number(v, header)]"
          :hint="number_hint(header)"
          :hide-details="false" :autofocus="true" dense single-line
        >
        </v-text-field>
        <v-select
          v-else-if='header.input_type === "select"'
          :items="typeof(header.select_items) === 'function' ? header.select_items(item) : header.select_items"
          v-model="item[header.value]"
          :hide-details="true" :autofocus="true" dense single-line
        >
        </v-select>
        <span
          v-else
        >
          {{format_display_cell(item, header)}}
        </span>
      </span>
    </template>
    <!-- eslint-disable-next-line -->
    <template v-slot:item.actions="{ item, index }">
      <span class="nowrap">
        <v-icon v-if="show_add_delete" class="mr-3" color="red" @click="delete_row(item)">
          mdi-delete
        </v-icon>
        <slot name="item-actions-append" :item="item" :index="index">
        </slot>
      </span>
    </template>
    <template v-slot:no-data>
      <h2 class="font-weight-light">{{empty_text}}</h2>
    </template>
  </v-data-table>
</v-card>
</template>

<script>

export default {
  name: "LiveEditTable",
  
  props: {
    title: String,
    empty_text: String,
    headers: Array,
    rows_feedback: [Array, Object],
    default_row: Object,
    row_key: String,
    show_add_delete: {type: Boolean, default: true}
  },

  emits: ["content_changed"],

  created() {
    document.addEventListener("input", this.start_edit);
  },

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

  watch: {
    rows_feedback: {
      handler(rows_in) {
        if (this.editing || rows_in.length == 0) {
            return;
        }
        this.rows = Array.from(rows_in, row => Object.assign({}, row));
        this.update_trigger = ! this.update_trigger;
      },
      immediate: true
    }
  },

  data() {
    return {
      rows: [],
      editing: false,
      update_trigger: false,
    }
  },

  methods: {
    validate_number(value, header) {
      const num = Number(value);
      if (isNaN(num)){
        return false;
      }
      const min = Object.hasOwn(header, "min") ? header.min : -Infinity;
      const max = Object.hasOwn(header, "max") ? header.max : Infinity;
      if (num < min || num > max) {
        return false;
      }
      return true;
    },
    set_number_item(value, item, header) {
      const num = Number(value);
      if (this.validate_number(num, header)) {
        if (Object.hasOwn(header, "digits")) {
          const scale = 10**header.digits;
          item[header.value] = Math.round((num + Number.EPSILON) * scale) / scale;
        } else {
          item[header.value] = num;
        }
      }
    },
    number_hint(header) {
      const h_min = Object.hasOwn(header, "min") ? `min: ${header.min}` : "";
      const h_max = Object.hasOwn(header, "max") ? `max: ${header.max}` : "";
      return `min: ${h_min}\xa0\xa0max: ${h_max}`;
    },
    format_number_cell(item, header) {
      if (Object.hasOwn(header, "digits")) {
        return item[header.value].toFixed(header.digits);
      } else {
        return item[header.value];
      }
    },
    format_display_cell(item, header) {
      if (Object.hasOwn(header, "digits")) {
        return item[header.value].toFixed(header.digits);
      } else {
        return item[header.value];
      }
    },

    clear() {
      this.rows = [];
      this.$emit("content_changed", this.rows);
    },

    start_edit() {
      this.editing = true;
      document.addEventListener("keydown", this.on_keydown);
    },

    stop_save_edit() {
      document.removeEventListener("keydown", this.on_keydown);
      this.$emit("content_changed", this.rows);
      this.editing = false;
    },

    cancel_edit() {
      document.removeEventListener("keydown", this.on_keydown);
      this.rows = Array.from(this.rows_feedback, row => Object.assign({}, row));
      this.editing = false;
      this.update_trigger = ! this.update_trigger;
    },

    delete_row(row) {
      const index = this.rows.indexOf(row);
      this.rows.splice(index, 1);
      this.$emit("content_changed", this.rows);
    },

    add_row() {
      const new_row = Object.assign({}, this.default_row);
      this.rows.push(new_row);
      this.start_edit();
    },

    on_keydown(keyb_evt) {
      if (keyb_evt.key === "Escape") {
        this.cancel_edit();
      } else if (keyb_evt.key === "Enter") {
        this.stop_save_edit();
      }
    },

    column_slot(key) {
      return `item.${key}`;
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
  width: 100%;
}

.nowrap {
  white-space: nowrap;
}
</style>