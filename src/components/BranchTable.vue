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
          :items="branches"
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
            <span slot="activator">{{ props.header.text }}</span>
          </template>
          <template v-slot:items="props">
            <tr :active="props.selected" @click="props.selected = !props.selected">
              <td>
                <v-checkbox :input-value="props.selected" primary hide-details></v-checkbox>
              </td>
              <td class="text-xs-left">{{ props.item.name }}</td>
              <td class="text-xs-left">{{ props.item.vStatus }}</td>
              <td class="text-xs-right">{{ props.item.MWFrom }}</td>
              <td class="text-xs-right">{{ props.item.MvarFrom }}</td>
              <td class="text-xs-right">{{ props.item.MVAFrom }}</td>
              <td class="text-xs-right">{{ props.item.AmpsFrom }}</td>
              <td class="text-xs-right">{{ props.item.MVALimit }}</td>
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
  background-color: rgba(255, 255, 255, 0);
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

.theme--dark.v-card {
  backdrop-filter: blur(12px) saturate(100%);
  -webkit-backdrop-filter: blur(12px) saturate(100%);
  background-color: rgba(17, 25, 40, 0.7);
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
        { text: "Branch", align: "left", value: "name", width: "15%" },
        { text: "Status", value: "Status" },
        { text: "MWFrom", value: "MWFrom" },
        { text: "MvarFrom", value: "MvarFrom" },
        { text: "MVAFrom", value: "MVAFrom" },
        { text: "AmpsFrom", value: "AmpsFrom" },
        { text: "MVA Limit", value: "MVALimit" },
        { text: "Actions", value: "Actions", sortable: false }
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
        if (item.vStatus) {
          await deviceApi.closeBranch(item.key);
        } else {
          await deviceApi.openBranch(item.key);
        }
      } catch (e) {
        console.error("Failed to toggle branch:", e);
      }
    },
  },
  computed: {
    ...mapGetters(["getBranchData", "getCaseData", "getStatus"]),
    branches() {
      if (!this.getCaseData) return [];
      const branches = this.getCaseData.content.Branch || {};
      const buses = this.getCaseData.content.Bus || {};
      const branchLive = {};
      this.getBranchData.forEach(b => { branchLive[b.key] = b; });
      return Object.entries(branches).map(([key, data]) => {
        const live = branchLive[key] || {};
        const fromBus = buses[key.split(",")[0]];
        const toBus = buses[key.split(",")[1]];
        return {
          key,
          name: (fromBus?.["String.Name"] || "") +
            "-" +
            (toBus?.["String.Name"] || "") +
            " " + (data["String.CircuitID"] || ""),
          Status: live.status != null ? live.status : 1,
          vStatus: live.status != null ? live.status === 1 : 1,
          MWFrom: live.mw_from || 0,
          MvarFrom: live.mvar_from || 0,
          MVAFrom: live.mva_from || 0,
          AmpsFrom: live.amps_from || 0,
          MWTo: live.mw_to || 0,
          MvarTo: live.mvar_to || 0,
          MVATo: live.mva_to || 0,
          AmpsTo: live.amps_to || 0,
          MVALimit: data["Single.MVA Limit"] || 0,
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
