<template>
  <v-dialog v-model="show" :key="id" width="900">
    <v-toolbar color="cyan" dark tabs>
      <v-toolbar-title>{{ name }} {{ volt }} {{ type }}</v-toolbar-title>
      <v-tabs slot="extension" centered color="cyan" slider-color="yellow">
        <v-tab> General </v-tab>
      </v-tabs>
    </v-toolbar>
    <v-card>
      <v-card-title class="headline"> Data </v-card-title>
      <v-data-table
        :headers="headers"
        :items="display"
        hide-default-footer
        class="elevation-1"
      >
        <template slot="items" slot-scope="props">
          <td class="text-xs-right" v-for="item in props.item" :key="item.text">
            {{ item }}
          </td>
        </template>
      </v-data-table>
      <v-card-title class="headline"> Control </v-card-title>
      <v-overflow-btn
        dense
        :items="dropdown"
        label="Commands"
        segmented
        target="#dropdown-example"
      ></v-overflow-btn>
      <v-card-actions>
        <v-btn color="primary" text @click.stop="show = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  data() {
    return {
      dropdown: [
        { text: "OPEN BOTH", callback: () => this.sendCommand("OPEN BOTH") },
        { text: "CLOSE BOTH", callback: () => this.sendCommand("CLOSE BOTH") },
      ],
      display: [],
      headers: [
        { text: "From Bus", value: "From Bus" },
        { text: "To Bus", value: "To Bus" },
        { text: "Circuit ID", value: "Circuit ID" },
        { text: "MVA Limit", value: "MVA Limit" },
        { text: "Status", value: "Status" },
      ],
    };
  },
  props: {
    visible: { type: Boolean, default: false },
    type: { type: String },
    id: { type: String },
    name: { type: String, default: "NULL" },
    volt: { type: String, default: "" },
    data: { default: () => [] },
  },
  computed: {
    show: {
      get() { return this.visible; },
      set(value) { if (!value) this.$emit("close"); },
    },
  },
  watch: {
    visible(val) {
      if (val) this.getData();
    },
  },
  methods: {
    async sendCommand(command) {
      try {
        const { deviceApi } = await import("@/services/api");
        if (command === "OPEN BOTH") {
          await deviceApi.openBranch(this.id);
        } else {
          await deviceApi.closeBranch(this.id);
        }
      } catch (e) {
        console.error("Branch command failed:", e);
      }
    },
    getData() {
      const caseData = this.$store.state.caseData;
      const simState = this.$store.state.simState;
      if (!caseData) return;
      const branch = (caseData.content.Branch || {})[this.id];
      const liveBranch = (simState && simState.branch) ? simState.branch[this.id] : null;
      if (branch) {
        const fromBus = caseData.content.Bus[this.id.split(",")[0]];
        const toBus = caseData.content.Bus[this.id.split(",")[1]];
        this.display = [{
          "From Bus": fromBus ? fromBus["String.Name"] : this.id.split(",")[0],
          "To Bus": toBus ? toBus["String.Name"] : this.id.split(",")[1],
          "Circuit ID": branch["String.CircuitID"] || "",
          "MVA Limit": branch["Single.MVA Limit"] || 0,
          "Status": liveBranch ? liveBranch.status : 1,
        }];
      }
    },
  },
};
</script>
