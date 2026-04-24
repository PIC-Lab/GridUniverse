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
          class="fixed-header"
          :headers="headers"
          :items="transformers"
          :items-per-page-options="defaultRowItems"
          v-model="selected"
          show-select
          item-key="name"
        >
          <template slot="headerCell" slot-scope="props">
            <span slot="activator">{{ props.header.text }}</span>
          </template>
          <template slot="items" slot-scope="props">
            <tr :active="props.selected">
              <td>
                <v-checkbox
                  v-model="props.selected"
                  primary
                  hide-details
                  @click="props.selected = !props.selected"
                ></v-checkbox>
              </td>
              <td class="text-xs-left">{{ props.item.name }}</td>
              <td class="text-xs-left">{{ props.item.Phase }}</td>
              <td class="text-xs-right">{{ props.item.Tap }}</td>
              <td class="text-xs-right">{{ props.item.Temperature }}</td>
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

.chip {
  width: 60px;
}
.fixed-header table {
  table-layout: fixed;
}

.fixed-header th {
  background-color: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
}

.fixed-header tr.datatable__progress th {
  top: 56px;
}

.fixed-header .table__overflow {
  overflow: auto;
  height: 100%;
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
        { text: "Transformer", align: "left", value: "name", width: "15%" },
        { text: "Phase", align: "left", value: "Degree" },
        { text: "Tap", align: "left", value: "Ratio" },
        { text: "Temperature", value: "Fahrenheit" }
      ],
      selected: [],
      defaultRowItems: [
        15,
        30,
        { text: "$vuetify.dataIterator.rowsPerPageAll", value: -1 }
      ],
    };
  },
  computed: {
    ...mapGetters(["getTransformerData", "getCaseData", "getStatus"]),
    transformers() {
      if (!this.getCaseData) return [];
      const transformers = this.getCaseData.content.Transformer || {};
      const buses = this.getCaseData.content.Bus || {};
      const transLive = {};
      this.getTransformerData.forEach(t => { transLive[t.key] = t; });
      return Object.entries(transformers).map(([key, data]) => {
        const live = transLive[key] || {};
        const fromBus = buses[key.split(",")[0]];
        const toBus = buses[key.split(",")[1]];
        return {
          key,
          name: (fromBus?.["String.Name"] || "") +
            "-" +
            (toBus?.["String.Name"] || ""),
          id: data["String.CircuitID"],
          Phase: live.phase_angle || 0,
          Tap: live.tap || 1,
          Temperature: 100,
        };
      });
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
