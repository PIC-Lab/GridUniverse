<template>
  <v-card>
    <v-app-bar flat dense color="transparent">
      <v-toolbar-title>
        <h4>{{ title }}</h4>
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
          :items="riskBuses"
          :items-per-page-options="defaultRowItems"
          v-model="selected"
          show-select
          item-key="name"
        >
          <template slot="headerCell" slot-scope="props">
            <v-tooltip bottom>
              <span slot="activator">
                {{ props.header.text }}
              </span>
              <span>
                {{ props.header.text }}
              </span>
            </v-tooltip>
          </template>
          <template v-slot:item.Vpu="{ item }">
            <v-chip
              label
              small
              :color="getColorByValue(item.Vpu)"
              text-color="white"
              >{{ item.Vpu }}</v-chip
            >
          </template>
          <template v-slot:items="props">
            <tr
              :active="props.selected"
              @click="props.selected = !props.selected"
            >
              <td>
                <v-checkbox
                  :input-value="props.selected"
                  primary
                  hide-details
                ></v-checkbox>
              </td>
              <td class="text-xs-left">{{ props.item.name }}</td>
              <td class="text-xs-right">{{ props.item.Max }}</td>
              <td class="text-xs-right">{{ props.item.Min }}</td>
            </tr>
          </template>
          <template slot="no-data">
            <v-card dark color="success">
              <v-card-text> Currently no violating buses! </v-card-text>
            </v-card>
          </template>
        </v-data-table>
      </template>
      <v-divider></v-divider>
    </v-card-text>
  </v-card>
</template>

<script>
import { mapGetters } from "vuex";

export default {
  props: {
    data: Array,
    title: String,
  },
  data() {
    return {
      headers: [
        { text: "Bus", align: "left", value: "name" },
        { text: "Vpu", value: "Vpu" },
        { text: "Max", value: "Max" },
        { text: "Min", value: "Min" },
      ],
      selected: [],
      defaultRowItems: [
        10,
        30,
        { text: "$vuetify.dataIterator.rowsPerPageAll", value: -1 },
      ],
    };
  },
  computed: {
    ...mapGetters(["getRiskBuses", "getCaseData"]),
    riskBuses() {
      const buses = this.getRiskBuses;
      const caseBuses = this.getCaseData ? this.getCaseData.content.Bus : {};
      return buses.map(b => ({
        name: b.bus_key,
        Vpu: b.vpu,
        Max: caseBuses[b.bus_key] ? caseBuses[b.bus_key]["Single.Max Limit"] : 0,
        Min: caseBuses[b.bus_key] ? caseBuses[b.bus_key]["Single.Min Limit"] : 0,
      }));
    },
  },
  methods: {
    getColorByValue(value) {
      if (value >= 1.1) return "red";
      if (value < 0.9) return "blue";
      return undefined;
    },
  },
  watch: {
    selected: function (newval) {
      this.$store.commit("updateVBuses", newval);
    },
    data: function (newval) {
      if (this.data && this.data.length > 0) {
        this.$store.commit("triggerAlarm", "Bus");
      } else {
        this.$store.commit("dismissAlarm", "Bus");
      }
    },
  },
};
</script>
