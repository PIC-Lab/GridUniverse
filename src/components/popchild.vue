<template>
  <v-card>
    <v-tabs vertical v-model="activeTab">
      <v-tab v-for="tab in tabs" :key="tab">
        {{ tab }}
      </v-tab>

      <v-tab-item v-for="tab in tabs" :key="tab">
        <v-card flat>
          <v-card-title class="headline"> Data </v-card-title>
          <v-data-table
            :headers="headers"
            :items="display"
            hide-default-footer
            class="elevation-1"
          >
            <template slot="items" slot-scope="props">
              <td
                class="text-xs-right"
                v-for="item in props.item"
                :key="item.text"
              >
                {{ item }}
              </td>
            </template>
          </v-data-table>
        </v-card>
        <v-card flat v-if="activeTab != 0">
          <v-card-title class="headline"> Control </v-card-title>
          <v-form>
            <v-container>
              <v-layout row wrap align-baseline>
                <v-flex xs4 v-show="showInput">
                  <v-text-field
                    :disabled="InputDisabled"
                    label="Value"
                    solo
                    clearable
                    v-model="value"
                  ></v-text-field>
                </v-flex>
                <v-flex xs8 v-if="showInput">
                  <v-overflow-btn
                    @change="cmddetection"
                    dense
                    :items="dropdown"
                    label="Commands"
                    segmented
                    target="#dropdown-example"
                  ></v-overflow-btn>
                </v-flex>
                <v-flex xs12 v-else>
                  <v-overflow-btn
                    dense
                    :items="dropdown"
                    label="Commands"
                    segmented
                    target="#dropdown-example"
                  ></v-overflow-btn>
                </v-flex>
              </v-layout>
            </v-container>
          </v-form>
        </v-card>
      </v-tab-item>
    </v-tabs>
  </v-card>
</template>

<script>
export default {
  props: {
    name: {},
    detail: {},
    subname: { type: String },
    data: { default: () => [] },
    show: {},
    busnum: { type: Number },
  },
  data() {
    return {
      dropdown: [],
      showInput: false,
      InputDisabled: true,
      value: null,
      type: "Bus",
      display: [],
      activeObj: "Bus",
      id: this.detail["Int.Bus Number"].toString(),
      activeTab: 0,
    };
  },
  computed: {
    tabs: function () {
      let temp = ["Bus"];
      const caseData = this.$store.state.caseData;
      if (!caseData) return temp;
      const busNum = this.name.split(" ")[1];
      for (let ele in caseData.content.Gen || {}) {
        if (ele.startsWith(busNum)) temp.push("Gen " + ele.split(",")[1]);
      }
      for (let ele in caseData.content.Load || {}) {
        if (ele.startsWith(busNum)) temp.push("Load " + ele.split(",")[1]);
      }
      for (let ele in caseData.content.Shunt || {}) {
        if (ele.startsWith(busNum)) temp.push("Shunt " + ele.split(",")[1]);
      }
      return temp;
    },
    headers: function () {
      return [
        { text: "Field", value: "field" },
        { text: "Value", value: "value" },
      ];
    },
  },
  methods: {
    cmddetection(ele) {
      if (this.showInput) {
        this.InputDisabled = !(ele !== "OPEN" && ele !== "CLOSE");
        if (ele === "OPEN" || ele === "CLOSE") this.value = null;
      } else {
        this.value = null;
        this.InputDisabled = true;
      }
    },
    async sendCommand(command) {
      try {
        const { deviceApi } = await import("@/services/api");
        const key = this.id;
        if (this.activeObj === "Gen") {
          if (command === "OPEN") await deviceApi.openGen(key);
          else if (command === "CLOSE") await deviceApi.closeGen(key);
          else if (this.value != null) await deviceApi.setGenPower(key, parseFloat(this.value));
        } else if (this.activeObj === "Load") {
          if (command === "OPEN") await deviceApi.openLoad(key);
          else if (command === "CLOSE") await deviceApi.closeLoad(key);
          else if (this.value != null) await deviceApi.setLoadPower(key, parseFloat(this.value));
        } else if (this.activeObj === "Shunt") {
          if (command === "OPEN") await deviceApi.openShunt(key);
          else if (command === "CLOSE") await deviceApi.closeShunt(key);
        }
      } catch (e) {
        console.error("Device command failed:", e);
      }
    },
    getData() {
      const caseData = this.$store.state.caseData;
      const simState = this.$store.state.simState;
      if (!caseData) return;

      if (this.activeObj === "Bus") {
        const bus = (caseData.content.Bus || {})[this.id];
        const liveBus = simState && simState.bus ? simState.bus[this.id] : null;
        if (bus) {
          this.display = [
            { field: "Name", value: bus["String.Name"] },
            { field: "Voltage (p.u.)", value: liveBus ? liveBus.vpu : bus["Single.Nominal kV"] },
            { field: "Angle (deg)", value: liveBus ? liveBus.vangle : 0 },
            { field: "Nominal kV", value: bus["Single.Nominal kV"] },
            { field: "Area", value: bus["Int.Area Number"] },
          ];
        }
      } else {
        const device = (caseData.content[this.activeObj] || {})[this.id];
        if (!device) return;
        const simDevices = simState ? simState[this.activeObj.toLowerCase()] || {} : {};
        const live = simDevices[this.id] || {};
        let rows = Object.entries(device)
          .filter(([k]) => !k.startsWith("Int."))
          .map(([k, v]) => ({ field: k, value: v }));
        if (live) {
          rows.push({ field: "MW (live)", value: live.mw || 0 });
          rows.push({ field: "Mvar (live)", value: live.mvar || 0 });
          rows.push({ field: "Status (live)", value: live.status != null ? live.status : 1 });
        }
        this.display = rows;
      }
    },
    buildDropdown() {
      let temp = [];
      if (this.activeObj === "Gen") {
        this.showInput = true;
        temp = [
          { text: "OPEN", callback: () => this.sendCommand("OPEN") },
          { text: "CLOSE", callback: () => this.sendCommand("CLOSE") },
          { text: "Set Power xxx MW", callback: () => this.sendCommand("Set Power " + this.value + " MW") },
        ];
      } else if (this.activeObj === "Load") {
        this.showInput = true;
        temp = [
          { text: "OPEN", callback: () => this.sendCommand("OPEN") },
          { text: "CLOSE", callback: () => this.sendCommand("CLOSE") },
          { text: "Set MW xxx", callback: () => this.sendCommand("Set MW " + this.value) },
        ];
      } else if (this.activeObj === "Shunt") {
        this.showInput = false;
        temp = [
          { text: "OPEN", callback: () => this.sendCommand("OPEN") },
          { text: "CLOSE", callback: () => this.sendCommand("CLOSE") },
        ];
      } else {
        this.showInput = false;
      }
      this.dropdown = temp;
    },
  },
  watch: {
    activeTab(newValue) {
      let ele = this.tabs[newValue];
      this.activeObj = ele;
      if (this.activeObj === "Bus") {
        this.id = this.detail["Int.Bus Number"].toString();
      } else {
        let strArray = ele.split(" ");
        let key = strArray[1];
        this.id = this.name.split(" ")[1] + "," + key;
      }
      this.buildDropdown();
      this.getData();
    },
    show: {
      immediate: true,
      handler(val) {
        if (val && this.activeTab === 0) this.getData();
      },
    },
  },
};
</script>
