<template>
  <v-container grid-list-md text-xs-center>
    <v-layout row wrap>
      <v-flex xs12>
        <div id="sanddance"></div>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<script>
import * as deck from "@deck.gl/core";
import * as layers from "@deck.gl/layers";
import * as luma from "@luma.gl/core";
import * as vega from "vega";
import { SandDance } from "@msrvida/sanddance-vue";

SandDance.use(vega, deck, layers, luma);

var scatterplotTest = {};
var data, insight;
var buses;

export default {
  data() {
    return {
      Interval: "",
    };
  },
  mounted() {
    this.initTable();
    this.init();
    this.Interval = setInterval(() => {
      this.change();
    }, 5000);
  },
  methods: {
    init() {
      scatterplotTest.viewer = new SandDance.Viewer(
        document.getElementById("sanddance"),
        { hideSidebarControls: true }
      );
      scatterplotTest.viewer.options.colors.axisLine = [255, 255, 255, 255];
      scatterplotTest.viewer.options.colors.axisText = [255, 255, 255, 255];
      scatterplotTest.viewer.options.colors.hoveredCube = [255, 255, 255, 255];
      var glDiv = scatterplotTest.viewer.presenter.getElement(
        SandDance.VegaDeckGl.PresenterElement.gl
      );
      insight = {
        colorBin: "quantize",
        columns: {
          color: "Vpu",
          sort: "FreqHz",
          uid: "Id",
          x: "Longitude",
          y: "Latitude",
          z: "LoadMW",
          size: "LoadMW",
          group: "GenMW",
        },
        facets: null,
        hideLegend: false,
        signaValues: null,
        view: "2d",
        scheme: "redblue",
        size: {
          height: glDiv.offsetHeight,
          width: glDiv.offsetWidth,
        },
        chart: "scatterplot",
      };
      scatterplotTest.viewer.render(insight, buses);
    },
    change() {
      this.updateTable();
      if (insight["chart"] == "barchartV") {
        insight["chart"] = "density";
      } else if (insight["chart"] == "scatterplot") {
        insight["chart"] = "barchartV";
      } else if (insight["chart"] == "density") {
        insight["chart"] = "scatterplot";
      }
      scatterplotTest.viewer.render(insight, buses);
    },
    initTable() {
      const caseData = this.$store.state.caseData;
      if (!caseData) return;
      let temp = [];
      const busData = caseData.content.Bus || {};
      const subs = caseData.content.Substation || {};
      const area = this.$store.state.area;
      for (let i in busData) {
        if (busData[i]["Int.Area Number"] == +area) {
          const subID = busData[i]["Int.Sub Number"];
          const sub = subs[String(subID)] || {};
          temp.push({
            Id: i,
            "Symbol(vega_id)": i,
            Latitude: sub["Double.Latitude"] || 0,
            Longitude: sub["Double.Longitude"] || 0,
            name: (busData[i]["String.Name"] || "") + " " + i,
            Status: 1,
            Vpu: 1,
            FreqHz: 60,
            GenMW: 0,
            GenMvar: 0,
            LoadMW: 0,
          });
        }
      }
      buses = temp;
    },
    updateTable() {
      const simState = this.$store.state.simState;
      if (!simState || !buses) return;
      const simBuses = simState.bus || {};
      const simGens = simState.gen || {};
      const simLoads = simState.load || {};
      for (let i in buses) {
        const busId = buses[i].Id;
        const live = simBuses[busId] || {};
        buses[i].Vpu = live.vpu || 1;
        buses[i].FreqHz = simState.area ? simState.area.frequency : 60;
        buses[i].Status = live.status != null ? live.status : 1;
        // Sum gen MW at this bus
        let genMW = 0;
        for (let gk in simGens) {
          if (gk.startsWith(busId)) genMW += simGens[gk].mw || 0;
        }
        buses[i].GenMW = genMW;
        // Sum load MW at this bus
        let loadMW = 0;
        for (let lk in simLoads) {
          if (lk.startsWith(busId)) loadMW += simLoads[lk].mw || 0;
        }
        buses[i].LoadMW = loadMW;
      }
    },
  },
  beforeDestroy() {
    clearInterval(this.Interval);
  },
};
</script>

<style>
.deckgl-overlay .label {
  color: white;
}
.sanddance-gl {
  border: 1px solid #ccc;
  float: left;
  height: 1080px;
  width: 90%;
  margin-right: 1em;
}
.sanddance-tooltip table {
  background: #333;
  color: #fff;
  font-size: smaller;
  margin: 1em;
  min-width: 16em;
  padding: 6px;
  position: absolute;
}
.sanddance-tooltip td {
  text-align: left;
  vertical-align: top;
  width: 75%;
}
.sanddance-tooltip td:first-child {
  width: 25%;
}
</style>
