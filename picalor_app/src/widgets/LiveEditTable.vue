<template>
<v-card class="mx-auto mt-10" outlined>
  <v-card-title>{{title}}</v-card-title>
  <v-data-table
    :headers="headers_actions"
    :items="rows"
    @dblclick:row="on_dblclick"
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
            <slot name="footer-prepend"> <!-- Can add more buttons here -->
            </slot>
          </div>
      </v-toolbar>
    </template>
    <template
      v-for="header in headers"
      v-slot:[column_slot(header.value)]="{ item, index }"
    >
      <v-switch
        :key="header.value"
        v-if='header.input_type === "switch"'
        v-model="item[header.value]"
        @change="emit_immediately"
        :readonly="index !== edited_idx"
        :autofocus="true"
      >
      </v-switch>
      <v-text-field
        :key="header.value"
        v-else-if='header.input_type === "text"'
        v-model="item[header.value]"
        :readonly="index !== edited_idx"
        :hide-details="true" :autofocus="true" dense single-line
      >
      </v-text-field>
      <v-text-field
        :key="header.value"
        v-else-if='header.input_type === "number"'
        :value="format_number_cell(item, header)"
        @change="text => set_number_item(text, item, header)"
        :readonly="index !== edited_idx"
        :rules="[v => validate_number(v, header)]"
        :hint="number_hint(header)"
        :hide-details="false" :autofocus="true" dense single-line
      >
      </v-text-field>
      <span
        :key="header.value"
        v-else
      >
        {{format_display_cell(item, header)}}
      </span>
    </template>
    <!-- eslint-disable-next-line -->
    <template v-slot:item.actions="{ item, index }">
      <span v-if="index === edited_idx" class="nowrap">
        <v-icon color="red" class="mr-3" @click="stop_edit(true)">
          mdi-window-close
        </v-icon>
        <v-icon color="green" @click="stop_edit()">
          mdi-content-save
        </v-icon>
      </span>
      <span v-else class="nowrap">
        <v-icon color="green" class="mr-3" @click="edit_row(item, index)">
          mdi-pencil
        </v-icon>
        <v-icon v-if="show_add_delete" class="mr-3" color="red" @click="delete_row(item)">
          mdi-delete
        </v-icon>
        <slot name="item-actions-not-edited-append" :item="item" :index="index">
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
import Vue from 'vue'

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
        this.rows = Array.from(rows_in);
      },
      immediate: true
    }
  },

  data() {
    return {
      rows: Array(),
      editing: Boolean(),
      edited_row_copy: Object(),
      edited_idx: -1,
    }
  },

  methods: {
    emit_immediately(){
      this.$emit('content_changed', this.rows)
    },
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

    edit_row(row, index) {
      this.editing = true;
      this.edited_idx = index;
      this.edited_row_copy = Object.assign({}, row);
      document.addEventListener("keydown", this.on_keydown);
    },

    stop_edit(abort=false) {
      document.removeEventListener("keydown", this.on_keydown);
      if (abort) {
        if (this.edited_row_copy === null) {
          this.rows.pop();
        } else {
          // Does not work: this.rows[this.edited_idx] = this.edited_row_copy;
          Vue.set(this.rows, this.edited_idx, this.edited_row_copy);
        }
      } else {
        this.$emit("content_changed", this.rows);
      }
      this.edited_idx = -1;
      this.editing = false;
    },

    delete_row(row) {
      const index = this.rows.indexOf(row);
      this.rows.splice(index, 1);
      this.$emit("content_changed", this.rows);
    },

    add_row() {
      const new_row = Object.assign({}, this.default_row);
      this.edited_idx = this.rows.length;
      this.rows.push(new_row);
      this.edited_row_copy = null;
      this.edit_row(new_row);
    },

    on_keydown(keyb_evt) {
      if (keyb_evt.key === "Escape") {
        this.stop_edit(true);
      } else if (keyb_evt.key === "Enter") {
        this.stop_edit();
      }
    },

    on_dblclick(_mouse_event, slot_data) {
      this.edit_row(slot_data.item, slot_data.index);
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