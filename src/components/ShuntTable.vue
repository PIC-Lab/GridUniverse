<template>
  <v-card>
    <v-app-bar flat dense color="transparent">
      <v-toolbar-title>
        <h4>{{title}}</h4>
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn icon>
        <v-icon>more_vert</v-icon>
      </v-btn>
    </v-app-bar>
    <v-divider></v-divider>
    <v-card-text class="pa-0">
      <template>
        <v-data-table
          :headers="headers"
          :items="shunts"
          :items-per-page-options="defaultRowItems"
          v-model="selected"
          show-select
          item-key="name"
        >
        <template v-slot:item.Actions="{ item }">
            <v-switch
              class="mt-3"
              v-model="item.vStatus"
              @click.native="toggle(item)"
              :disabled="disable"
            ></v-switch>
          </template>
          <template slot="headerCell" slot-scope="props">
            <v-tooltip bottom>
              <span slot="activator">{{ props.header.text }}</span>
              <span style="color:white;">{{ props.header.text }}</span>
            </v-tooltip>
          </template>
          <template v-slot:items="props">
            <tr :active="props.selected" @click="props.selected = !props.selected">
              <td>
                <v-checkbox :input-value="props.selected" primary hide-details></v-checkbox>
              </td>
              <td class="text-xs-left">{{ props.item.name }}</td>
              <td class="text-xs-left">{{ props.item.Status }}</td>
              <td class="text-xs-right">{{ props.item.Mvar }}</td>
              <td class="text-xs-right">{{ props.item.Vpu }}</td>
              <td class="text-xs-right">{{ props.item.FreqHz }}</td>
            </tr>
          </template>
        </v-data-table>
      </template>
      <v-divider></v-divider>
    </v-card-text>
  </v-card>
</template>

<style scoped>
table.v-table tbody td:first-child,
table.v-table tbody td:not(:first-child),
table.v-table tbody th:first-child,
table.v-table tbody th:not(:first-child),
table.v-table thead td:first-child,
table.v-table thead td:not(:first-child),
table.v-table thead th:first-child,
table.v-table thead th:not(:first-child) {
  padding: 0 10px;
}
td {
  width: auto;
}
</style>

<script>
import { mapGetters } from "vuex";

export default {
  props: {
    title: String
  },
  data() {
    return {
      headers: [
        { text: "Shunt", align: "left", value: "name" },
        { text: "Status", value: "Status", align: "left" },
        { text: "Mvar", value: "Mvar", align: "right" },
        { text: "Vpu", value: "Vpu", align: "right" },
        { text: "FreqHz", value: "FreqHz", align: "right" },
        { text: "Actions", value: "Actions", sortable: false, align: "right" }
      ],
      selected: [],
      defaultRowItems: [
        15,
        30,
        { text: "$vuetify.dataIterator.rowsPerPageAll", value: -1 }
      ],
    };
  },
  methods: {
    async toggle(item) {
      try {
        const { deviceApi } = await import("@/services/api");
        if (item.Status == 1) {
          await deviceApi.openShunt(item.key_cmd);
        } else {
          await deviceApi.closeShunt(item.key_cmd);
        }
      } catch (e) {
        console.error("Failed to toggle shunt:", e);
      }
    },
  },
  computed: {
    ...mapGetters(["getShuntData", "getStatus"]),
    shunts() {
      return this.getShuntData;
    },
    disable() {
      return this.getStatus !== "running";
    },
  },
  watch: {
    selected: function(newval) {
      this.$store.commit("updateSelectedShunts", newval);
    }
  },
};
</script>
