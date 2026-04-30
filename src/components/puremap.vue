/* eslint-disable */
<template>
  <div>
    <v-layout row class="align-center layout px-4 pt-4 app--page-header mb-2">
      <v-icon larg>home</v-icon>
      <div class="page-header-left">
        <h3 class="pl-5">Overview</h3>
      </div>
      <v-spacer></v-spacer>
      <userInfo></userInfo>
    </v-layout>
    <v-container grid-list-xl text-xs-center fluid>
      <v-layout row wrap>
        <v-flex lg3 sm6 xs12>
          <mini-statistic
            :name="'GenMW'"
            icon="fa fa-facebook"
            title="Total Generation (MW)"
            :sub-title="areaData ? areaData.gen_mw : 0"
            color="rgba(63, 81, 181, 0.8)"
            :img="require('../assets/icons8-factory-64.png')"
            id="step5"
          ></mini-statistic>
        </v-flex>
        <v-flex lg3 sm6 xs12>
          <mini-statistic
            :name="'LoadMW'"
            icon="fa fa-google"
            title="Total Load (MW)"
            :sub-title="areaData ? areaData.load_mw : 0"
            color="rgba(244, 67, 54, 0.8)"
            :img="require('../assets/kitchen-set.png')"
          ></mini-statistic>
        </v-flex>
        <v-flex lg3 sm6 xs12>
          <mini-statistic
            :name="'Freq'"
            icon="fa fa-twitter"
            title="Average Frequency (Hz)"
            :sub-title="areaData ? areaData.frequency : 60"
            color="rgba(3, 169, 244, 0.8)"
            :img="require('../assets/icons8-frequency-64.png')"
          ></mini-statistic>
        </v-flex>
        <v-flex lg3 sm6 xs12>
          <mini-statistic
            :name="'ExportMW'"
            icon="fa fa-instagram"
            title="Export Power (MW)"
            :sub-title="areaData ? areaData.export_mw : 0"
            color="rgba(156, 39, 176, 0.8)"
            :img="require('../assets/export.png')"
          ></mini-statistic>
        </v-flex>
        <v-flex lg8 sm8 xs12>
          <m-widget
            title="Interactive Site Map"
            content-bg="white"
            @clicked="restore"
          >
            <div slot="widget-content" id="main" class="chart"></div>
          </m-widget>
        </v-flex>
        <v-flex lg4 sm4 xs12>
          <v-layout row wrap>
            <v-flex xs12>
              <m-widget title="Load Forecast" content-bg="white">
                <div slot="widget-content">
                  <loadForecast></loadForecast>
                </div>
              </m-widget>
            </v-flex>
            <v-flex lg12 sm12 xs12>
              <branchTable
                title="High-load Branches"
                :tabledata="riskBranches"
              ></branchTable>
            </v-flex>
          </v-layout>
        </v-flex>
      </v-layout>
    </v-container>
    <linepop
      v-if="lineshowDialog"
      :visible="lineshowDialog"
      :type="type"
      :id="id"
      :name="name"
      :volt="volt"
      @close="lineshowDialog = false"
    />
    <subpop
      v-if="subshowDialog"
      :visible="subshowDialog"
      :children="children"
      :type="type"
      :id="id"
      :name="name"
      :volt="volt"
      @close="subshowDialog = false"
    />
  </div>
</template>
<style scoped>
.chart {
  z-index: 0;
  height: 700px;
  width: 100%;
}
</style>

<script>
import { mapGetters } from "vuex";
import MWidget from "@/components/MWidget";
import MiniStatistic from "@/components/MiniStat";
import branchTable from "@/components/RiskBranchTable";
import loadForecast from "@/components/loadForecast";
import userInfo from "@/components/userInfo";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const VOLT_COLORS = {
  500: "#e53935",
  230: "#3949ab",
  115: "#1565c0",
 13.8: "#7c4dff",
};

const SUB_COLORS = {
  Gen: "#ff5722",
  Shunt: "#8d6e63",
  default: "#283593",
};

export default {
  name: "puremap",
  data() {
    return {
      linedata: [],
      subdata: [],
      subdetail: [],
      subshowDialog: false,
      lineshowDialog: false,
      children: {},
      type: "",
      id: "",
      name: "",
      volt: "",
      statusArray: [],
      openLineData: [],
      highRiskLines: {},
      formatRiskLines: [],
      mapCenter: [27.4241, -98.4936],
      Interval: null,
      map: null,
      subLayer: null,
      lineLayer: null,
      openLineLayer: null,
      riskLineLayer: null,
      otherSubLayer: null,
      otherLineLayer: null,
    };
  },
  methods: {
    initMap() {
      this.map = L.map("main", {
        center: this.mapCenter,
        maxZoom: 18,
        zoom: 8,
        preferCanvas: true,
      });
      const url = "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png";
      L.tileLayer(url).addTo(this.map);

      this.subLayer = L.layerGroup().addTo(this.map);
      this.lineLayer = L.layerGroup().addTo(this.map);
      this.openLineLayer = L.layerGroup().addTo(this.map);
      this.riskLineLayer = L.layerGroup().addTo(this.map);
      this.otherSubLayer = L.layerGroup().addTo(this.map);
      this.otherLineLayer = L.layerGroup().addTo(this.map);

      const legend = L.control({ position: "topright" });
      legend.onAdd = function (map) {
        const div = L.DomUtil.create("div", "");
        div.style.cssText = "background:rgba(255,255,255,0.92);color:#212121;padding:10px 14px;font-size:13px;line-height:2;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.15);";
        const dot = function (color) {
          return '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:' + color + ';margin-right:6px;vertical-align:middle;border:1px solid rgba(0,0,0,0.15);"></span>';
        };
        const line = function (color, label) {
          return '<span style="display:inline-block;width:18px;height:3px;background:' + color + ';margin-right:6px;vertical-align:middle;border-radius:2px;"></span>' + label;
        };
        div.innerHTML =
          '<div style="font-weight:600;margin-bottom:4px;font-size:13px;">Substations</div>' +
          '<div>' + dot(SUB_COLORS.default) + 'Substation</div>' +
          '<div>' + dot(SUB_COLORS.Gen) + 'w/ Generator</div>' +
          '<div>' + dot(SUB_COLORS.Shunt) + 'w/ Shunt</div>' +
          '<div style="font-weight:600;margin-top:6px;margin-bottom:4px;">Voltage (kV)</div>' +
          '<div>' + line(VOLT_COLORS[500], '500 kV') + '</div>' +
          '<div>' + line(VOLT_COLORS[230], '230 kV') + '</div>' +
          '<div>' + line(VOLT_COLORS[115], '115 kV') + '</div>' +
          '<div>' + line(VOLT_COLORS[13.8], '13.8 kV') + '</div>';
        return div;
      };
      legend.addTo(this.map);
    },

    drawSubstations() {
      this.subLayer.clearLayers();
      const self = this;
      for (const sub of this.subdata) {
        const attrs = sub.attributes || {};
        let color = SUB_COLORS.default;
        let radius = 5;
        if (attrs.Gen) { color = SUB_COLORS.Gen; radius = 7; }
        else if (attrs.Shunt) { color = SUB_COLORS.Shunt; radius = 6; }

        const marker = L.circleMarker([sub.value[1], sub.value[0]], {
          radius,
          color,
          fillOpacity: 0.9,
          weight: 1,
          opacity: 1,
        }).addTo(this.subLayer);

        marker.on("click", function () {
          self.type = "Substation";
          self.name = sub.name;
          self.id = sub.id;
          self.volt = "";
          self.children = self.subdetail[+sub.id]
            ? self.subdetail[+sub.id].Bus
            : [];
          self.subshowDialog = true;
        });

        marker.bindTooltip("Substation: " + sub.name);
      }
    },

    drawLines() {
      this.lineLayer.clearLayers();
      const self = this;
      for (const line of this.linedata) {
        const volt = line.attributes ? line.attributes.volt : 0;
        const color = VOLT_COLORS[volt] || "#757575";
        const coords = line.coords.map(function(c) { return [c[1], c[0]]; });

        const poly = L.polyline(coords, {
          color,
          weight: 1,
          opacity: 1,
        }).addTo(this.lineLayer);

        poly.on("click", function () {
          self.type = "Branch";
          self.name = line.name;
          self.id = line.id;
          self.volt = (line.attributes ? line.attributes.volt : 0) + "kV";
          self.lineshowDialog = true;
        });

        const limit = line.attributes ? line.attributes.MVALimit : 999;
        const mva = line.attributes ? line.attributes.MVA : 0;
        const pct = limit > 0 ? ((mva * 100) / limit).toFixed(0) : "0";
        const tipColor = pct >= 100 ? "#ba000d" : pct >= 90 ? "#ffd600" : "#1b5e20";
        poly.bindTooltip(
          `<span style="color:${tipColor}">${line.name} — ${pct}%</span>`
        );
      }
    },

    drawOtherArea() {
      this.otherSubLayer.clearLayers();
      this.otherLineLayer.clearLayers();
      const otherSubs = this.$store.state.otherArea.Substation;
      const otherBranches = this.$store.state.otherArea.Branch;
      for (const s of otherSubs) {
        L.circleMarker([s.value[1], s.value[0]], {
          radius: 3,
          color: "#616161",
          fillOpacity: 0.5,
          weight: 0.5,
        }).addTo(this.otherSubLayer);
      }
      for (const b of otherBranches) {
        L.polyline(b.coords.map(function(c) { return [c[1], c[0]]; }), {
          color: "#757575",
          weight: 0.5,
          opacity: 0.5,
        }).addTo(this.otherLineLayer);
      }
    },

    getData() {
      this.subdata = this.$store.state.subData;
      this.linedata = this.$store.state.lineData;
      this.subdetail = this.$store.state.subDetail;
    },

    initUpdateLines() {
      const branches = this.$store.state.caseData ? this.$store.state.caseData.content.Branch : {};
      this.statusArray = Array(Object.keys(branches).length).fill(1);
    },

    updateLinesCycle() {
      this.Interval = setInterval(() => {
        if (this.getStatus === "running") {
          this.updateLines();
        }
      }, 1500);
    },

    updateLines() {
      const simBranches = this.$store.state.simState ? this.$store.state.simState.branch : {};
      const statusTemp = [];
      const self = this;
      const caseData = this.$store.state.caseData;
      if (!caseData) return;

      const subs = caseData.content.Substation || {};
      const buses = caseData.content.Bus || {};

      for (let index in this.linedata) {
        const live = simBranches[this.linedata[index].id] || {};
        const status = live.status != null ? live.status : 1;
        statusTemp.push(status);
        this.linedata[index].attributes.MVA = live.mva_from || 0;
        this.linedata[index].attributes.MVFrom = live.mvar_from || 0;

        // Power flow direction — reverse coords if negative
        if (this.linedata[index].attributes.MVFrom < 0) {
          this.linedata[index].coords = [this.linedata[index].coords[1], this.linedata[index].coords[0]];
        }

        // Open/close tracking
        if (this.statusArray[index] == 1 && [0, 2, 3].includes(status)) {
          this.updateLineOpen(index);
        } else if ([0, 2, 3].includes(this.statusArray[index]) && status == 1) {
          this.updateLineClose(index);
        }

        // High-risk tracking
        const key = this.linedata[index].id;
        const mva = live.mva_from || 0;
        const limit = this.linedata[index].attributes.MVALimit;
        if (mva >= 0.85 * limit) {
          this.highRiskLines[key] = {
            name: key,
            MVA: mva,
            Ratio: ((mva * 100) / limit).toFixed(2),
            MVALimit: limit,
            coords: this.linedata[index].coords,
          };
        } else if (key in this.highRiskLines) {
          delete this.highRiskLines[key];
        }
      }
      this.statusArray = statusTemp;
      this.formatRiskLines = Object.values(this.highRiskLines);
      this._refreshLineLayers();
    },

    _refreshLineLayers() {
      this.lineLayer.clearLayers();
      this.openLineLayer.clearLayers();
      this.riskLineLayer.clearLayers();

      const self = this;
      for (let index in this.linedata) {
        const line = this.linedata[index];
        const volt = line.attributes ? line.attributes.volt : 0;
        const color = VOLT_COLORS[volt] || "#757575";
        const coords = line.coords.map(function(c) { return [c[1], c[0]]; });
        const mva = line.attributes ? line.attributes.MVA : 0;
        const limit = line.attributes ? line.attributes.MVALimit : 999;
        const pct = limit > 0 ? ((mva * 100) / limit).toFixed(0) : "0";

        // Normal line
        if (this.openLineData.findIndex(function(o) { return o.id === line.id; }) === -1) {
          const tipColor = pct >= 100 ? "#ba000d" : pct >= 90 ? "#ffd600" : "#1b5e20";
          L.polyline(coords, {
            color, weight: 1, opacity: 1,
          }).addTo(this.lineLayer).bindTooltip(
            `<span style="color:${tipColor}">${line.name} — ${pct}%</span>`
          );
        }

        // Open line (dashed red)
        const openItem = this.openLineData.find(function(o) { return o.id === line.id; });
        if (openItem) {
          L.polyline([coords[0], coords[0]], {
            color: "#c82800", weight: 1, dashArray: [5, 5], opacity: 1,
          }).addTo(this.openLineLayer).bindTooltip(
            `<span style="color:#c82800">${line.name} — OPEN</span>`
          );
        }

        // High-risk line (thick red)
        if (this.highRiskLines[line.id]) {
          L.polyline(coords, {
            color: "#f44336", weight: 6, opacity: 0.5,
          }).addTo(this.riskLineLayer);
        }
      }
    },

    updateLineOpen(branchIndex) {
      const line = this.linedata[branchIndex];
      this.openLineData.push({ id: line.id, coords: [line.coords[0], line.coords[1]] });
      this.linedata[branchIndex]["coords"] = [line.coords[0], line.coords[0]];
    },

    updateLineClose(branchIndex) {
      for (let i in this.openLineData) {
        if (this.openLineData[i].id == this.linedata[branchIndex].id) {
          this.linedata[branchIndex].coords = this.openLineData[i].coords;
          this.openLineData.splice(i, 1);
          break;
        }
      }
    },

    restore() {
      this.map.flyTo(this.mapCenter, 8, { animate: true, duration: 1.5 });
    },
  },
  mounted() {
    this.initUpdateLines();
    this.initMap();

    const drawData = () => {
      if (this.$store.state.subData.length > 0 && this.subdata.length === 0) {
        this.getData();
        this.drawSubstations();
        this.drawLines();
        this.drawOtherArea();
      }
    };

    drawData();
    this._unwatch = this.$store.watch(
      (state) => state.subData.length,
      () => drawData()
    );
    setTimeout(drawData, 500);
    setTimeout(drawData, 2000);
  },
  activated() {
    if (this.map) {
      this.map.invalidateSize();
    }
    this.updateLinesCycle();
  },
  deactivated() {
    clearInterval(this.Interval);
  },
  beforeDestroy() {
    clearInterval(this.Interval);
    if (this._unwatch) this._unwatch();
    if (this.map) { this.map.remove(); this.map = null; }
  },
  computed: {
    ...mapGetters(["getAreaData", "getRiskBranches", "getStatus", "getSubData", "getLineData", "getBranchData", "getTransformerData"]),
    areaData() { return this.getAreaData; },
    riskBranches() { return this.getRiskBranches; },
  },
  watch: {},
  components: {
    linepop: () => import("./linepop"),
    subpop: () => import("./subpop"),
    MWidget,
    MiniStatistic,
    branchTable,
    loadForecast,
    userInfo,
  },
};
</script>
