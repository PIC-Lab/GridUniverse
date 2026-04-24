<template>
  <div>
    <v-layout row class="align-center layout px-4 pt-4 app--page-header">
      <div class="page-header-left">
        <h3 class="pr-3">Transformer</h3>
      </div>
      <v-icon larg>view_carousel</v-icon>
      <v-spacer></v-spacer>
      <div class="page-header-right">
        <h4 class="pr-1">
          Hi {{ $store.state.username }}
          <status-indicator
            :negative="$store.state.alarm"
            :positive="!$store.state.alarm"
            pulse
          ></status-indicator>
        </h4>
      </div>
    </v-layout>
    <v-container grid-list-xl text-xs-center fluid>
      <v-layout row wrap>
        <v-flex lg6 sm6 xs12>
          <!-- <v-widget title="Realtime Data" content-bg="white">
          <div slot="widget-content">-->
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
                  class="fixed-header"
                  :headers="headers"
                  :items="Transformers"
                  :items-per-page-options="defaultRowItems"
                  item-key="name"
                >
                  <template v-slot:items="props">
                    <td class="text-xs-left">{{ props.item.name }}</td>
                    <td class="text-xs-center">{{ props.item.kv }}</td>
                    <!-- <td class="text-xs-left">{{ props.item.Phase }}</td>
                    <td class="text-xs-center">{{ props.item.Tap }}</td>-->
                    <td class="text-xs-center">{{ props.item.Temperature }}</td>
                    <td class="text-xs-center">
                      {{ props.item.GICNeutralCurrent }}
                    </td>
                    <td class="text-xs-center">
                      {{ props.item.GICMvarLosses }}
                    </td>
                    <td class="text-xs-center">{{ props.item.GICIEff }}</td>
                  </template>
                </v-data-table>
              </template>
              <v-divider></v-divider>
            </v-card-text>
          </v-card>
          <!-- </div>
          </v-widget>-->
        </v-flex>
        <v-flex lg6 sm6 xs12>
          <v-layout row wrap>
            <v-flex lg12 sm12 xs12>
              <div id="v-widget">
                <v-card>
                  <v-app-bar
                    color="transparent"
                    flat
                    dense
                    v-if="enableHeader"
                  >
                    <v-toolbar-title>
                      <h4>{{ transformerChartTitle }}</h4>
                    </v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn
                      outlined
                      small
                      :disabled="gicEnabled"
                      color="primary"
                      @click="enableGIC"
                      >GICNeutralCurrent</v-btn
                    >
                    <v-btn
                      outlined
                      small
                      :disabled="tempEnabled"
                      color="primary"
                      @click="enableTemp"
                      >Temperature</v-btn
                    >
                  </v-app-bar>
                  <v-divider v-if="enableHeader"></v-divider>
                  <slot name="widget-content"></slot>
                  <div id="transMap" class="transformerChart"></div>
                </v-card>
              </div>
            </v-flex>
          </v-layout>
        </v-flex>
      </v-layout>
    </v-container>
  </div>
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
  /* background-color: #fff; just for LIGHT THEME, change it to #474747 for DARK */
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
.transformerChart {
  z-index: 0;
  height: 600px;
}
.temperatureChart {
  z-index: 0;
  height: 400px;
}
</style>

<script>
import { abs } from 'mathjs/lib/esm/number';

export default {
  // props: {
  // 	title: String
  // },
  data() {
    return {
      title: "Realtime Data",
      transformerChartTitle: "Transformer Monitor",
      enableHeader: {
        type: Boolean,
        default: true,
      },
      contentBg: {
        type: String,
        default: "white",
      },
      focus: {
        type: String,
      },
      height: {
        type: String,
        default: "300px",
      },
      headers: [
        {
          text: "Transformer",
          align: "left",
          // sortable: false,
          value: "name",
          width: "15%",
        },
        // { text: 'Phase', align: 'left', value: 'Degree' },
        // { text: 'Tap', align: 'left', value: 'Ratio' },
        { text: "kV", value: "kV" },
        { text: "Temperature", value: "Temperature" },
        { text: "GICNeutralCurrent", value: "GICNeutralCurrent" },
        { text: "GICMvarLosses", value: "GICMvarLosses" },
        { text: "GICIEff", value: "GICIEff" },
      ],
      Transformers: [],
      selected: [],
      anchor: 0,
      TransformerDataLength: 0,
      defaultRowItems: [
        15,
        30,
        { text: "$vuetify.dataIterator.rowsPerPageAll", value: -1 },
      ],
      TransformerArray: [],
      transformerChart: {},
      temperatureChart: {},
      subdata: [],
      linedata: [],
      subdetail: [],
      busdetail: [],
      mapCenter: [27.4241, -98.4936],
      transformerMap: null,
      temperatureMap: null,
      mapStyle: {
        width: "100%",
        height: this.height,
      },
      transData: [],
      count: 0,
      gicEnabled: true,
      legend: {},
    };
  },
  methods: {
    initdraw() {
      let heatmapData = [];
      for (let ele in this.$store.state.transformerDict) {
        heatmapData.push([
          this.$store.state.transformerDict[ele].coords[0][0],
          this.$store.state.transformerDict[ele].coords[0][1],
          100,
        ]);
      }
      // console.log(this.$store.state.transformerDict)
      const url = "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png";
      const options = {
        // redirect: true,
        // time: '',
        // maxZoom: 8,
        // tilematrixset: 'GoogleMapsCompatible_Level',
        // format: 'jpg',
        // attribution:
        // 	'&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, Tiles courtesy of <a href="http://hot.openstreetmap.org/" target="_blank">Humanitarian OpenStreetMap Team</a>'
      };
      this.transformerMap = new window.L.map("transMap", {
        // crs: L.CRS.EPSG4326,
        center: this.mapCenter, //this.$store.state.center, //this.mapCenter,
        maxZoom: 18,
        zoom: 7,
      });
      const tran_bg = new window.L.tileLayer(url, options);
      tran_bg.addTo(this.transformerMap);
      this.legend = window.L.control({ position: "bottomleft" });
      this.legend.onAdd = function (map) {
        var div = window.L.DomUtil.create("div", "legend legend-background");
        let labels = ["<strong>Categories</strong>"];
        const categories = [
          "Positive Neutral Current",
          "Negative Neutral Current",
        ];
        const color = ["rgba(0, 200, 0, 0.5)", "rgba(0, 0, 200, 0.5)"];
        for (var i = 0; i < categories.length; i++) {
          div.innerHTML +=
            '<span class="circle" style="background:' +
            color[i] +
            '"></span>' +
            categories[i] +
            "<br>";
        }
        // div.innerHTML = labels.join('<br>');
        // console.log(div)
        return div;
      };
      this.legend.addTo(this.transformerMap);
      // this.chart = echarts.init(document.getElementById('map'));
      var echartsOptions = {
        animation: false,
        tooltip: {
          show: true,
          trigger: "item",
        },
        // visualMap: {
        // 	show: false,
        // 	top: 'top',
        // 	min: 50,
        // 	max: 300,
        // 	seriesIndex: 7,
        // 	calculable: true,
        // 	inRange: {
        // 		color: ['#000080', 'blue', 'green', 'yellow', 'red']
        // 	}
        // },
        series: [
          {
            id: "transformer",
            type: "effectScatter",
            name: "transformer",
            coordinateSystem: "leaflet",
            symbol: "circle",
            symbolSize: (value, params) => {
              if (params.data.attribute.GICNeutralCurrent) {
                const current = abs(
                  params.data.attribute.GICNeutralCurrent
                );
                if (current < 1) {
                  return 5;
                } else if (current < 5) {
                  return 10;
                } else if (current < 10) {
                  return 15;
                } else if (current < 20) {
                  return 20;
                } else if (current < 50) {
                  return 25;
                } else {
                  return 50;
                }
              }
            },
            // showEffectOn: 'emphasis',
            // zindex: 2,
            zlevel: 3,
            progressive: 100,
            progressiveThreshold: 200,
            data: this.transData, //this.$store.state.subData,
            tooltip: {
              formatter: (params) => {
                return params.data.attribute.GICNeutralCurrent.toString();
              },
            },
            itemStyle: {
              color: (params) => {
                if (params.data.attribute.GICNeutralCurrent) {
                  if (params.data.attribute.GICNeutralCurrent > 0) {
                    return "rgba(0, 200, 0, 0.5)";
                  } else {
                    return "rgba(0, 0, 200, 0.5)";
                  }
                }
              },
            },
          },
          {
            id: "temperature",
            type: "scatter",
            coordinateSystem: "leaflet",
            data: this.transData,
            symbolSize: 0,
            tooltip: {
              formatter: (params) => {
                return params.data.attribute.Temperature.toString();
              },
            },
            itemStyle: {
              color: (params) => {
                if (params.data.attribute.Temperature) {
                  if (params.data.attribute.Temperature < 60) {
                    return "rgba(0, 0, 200, 0.8)";
                  } else if (params.data.attribute.Temperature < 80) {
                    return "rgba(0, 200, 0, 0.8)";
                  } else if (params.data.attribute.Temperature < 100) {
                    return "rgba(200,200,0,0.8)";
                  } else {
                    return "rgba(255, 0, 0, 1)";
                  }
                }
              },
            },
          },
        ],
      };
      const layerOptions = {
        loadWhileAnimating: false,
        attribution: "",
      };
      this.transformerChart = new window.L.supermap.echartsLayer(
        echartsOptions,
        layerOptions
      ); // _ec is the echartsInstance
      this.transformerChart.addTo(this.transformerMap);

      // var ramdompts_ipl = window.turf.randomPoint(25, {
      // 	bbox: [-98, 28.0, -94, 31.0]
      // });

      // window.turf.featureEach(ramdompts_ipl, function(point) {
      // 	point.properties.obs = Math.random() * 25;
      // });
      // // var tin = turf.tin(ramdompts_ipl, 'obs');
      // var contours_pts = window.turf.interpolate(ramdompts_ipl, 2, {
      // 	gridType: 'points',
      // 	property: 'obs',
      // 	units: 'kilometers'
      // });
      // var contours = window.turf.isobands(contours_pts, [0, 5, 10, 15, 20, 25, 30], {
      // 	zProperty: 'obs'
      // });
      // function getColor(x) {
      // 	return x < 5
      // 		? '#bd0026'
      // 		: x < 10
      // 		? '#f03b20'
      // 		: x < 15
      // 		? '#fd8d3c'
      // 		: x < 20
      // 		? '#fecc5c'
      // 		: '#ffffb2';
      // }
      // var contoursLayer = L.geoJson(contours, {
      // 	// onEachFeature: function(feature, layer) {
      // 	// 	layer.bindPopup(feature.properties.obs);
      // 	// },
      // 	style: function(feature) {
      // 		return {
      // 			interactive: false,
      // 			fillColor: getColor(parseInt(feature.properties.obs.split('-')[0])),
      // 			weight: 0.5,
      // 			color: '#bd0026',
      // 			opacity: 1
      // 		};
      // 	}
      // }).addTo(this.map);
      // console.log(tin);
      // var ecModel = this.chart._model;
      // var leafletMap;
      // ecModel.eachComponent('leaflet', function(leafletModel) {
      // 	if (leafletMap == null) {
      // 		// console.log(leafletModel)
      // 		leafletMap = leafletModel.__map;
      // 	}
      // });
      // leafletMap.zoomControl.remove();
    },
    preProcess() {
      // No longer needed
    },
    initTable() {
      let temp = [];
      let subid;
      const caseData = this.$store.state.caseData;
      if (!caseData) return Promise.reject("No case data");
      const trans = caseData.content.Transformer || {};
      const buses = caseData.content.Bus || {};
      for (let i in trans) {
        if (
          [trans[i]["FromArea"], trans[i]["ToArea"]].includes(+this.$store.state.area)
        ) {
          temp.push({
            value: false,
            key: i,
            name:
              (buses[i.split(",")[0]] || {})["String.Name"] +
              "-" +
              (buses[i.split(",")[1]] || {})["String.Name"] +
              "-" +
              trans[i]["String.CircuitID"],
            kv:
              (buses[i.split(",")[0]] || {})["Single.Nominal kV"] +
              "/" +
              (buses[i.split(",")[1]] || {})["Single.Nominal kV"],
            id: trans[i]["String.CircuitID"],
            Phase: 0,
            Tap: 1,
            Temperature: null,
            GICNeutralCurrent: null,
            GICMvarLosses: null,
            GICIEff: null,
          });
          subid =
            (buses[i.split(",")[0]] || {})["Int.Sub Number"];
          const subs = caseData.content.Substation || {};
          this.transData.push({
            value: [
              (subs[subid] || {})["Double.Longitude"],
              (subs[subid] || {})["Double.Latitude"],
            ],
            attribute: {
              GICNeutralCurrent: null,
              Temperature: null,
            },
          });
        }
      }
      this.Transformers = temp;
      // console.log(this.Transformers);
      if (this.Transformers.length > 1) {
        return Promise.resolve("Table initialized properly");
      } else {
        return Promise.reject("Error in initialization");
      }
    },
    updateTable() {
      setInterval(() => {
        try {
          // TODO: Update transformer data from backend simState when available
          const simTrans = this.$store.state.simState
            ? this.$store.state.simState.transformer || {}
            : {};
          for (let i in this.Transformers) {
            const live = simTrans[this.Transformers[i].key] || {};
            this.Transformers[i].Phase = live.phase_angle || 0;
            this.Transformers[i].Tap = live.tap || 1;
            this.Transformers[i].Temperature = 100;
            this.transData[i].attribute["Temperature"] = 100;
          }
          // this.transformerChart.setOption(temp);
          if (this.gicEnabled) {
            this.transformerChart.setOption({
              series: [
                {
                  id: "transformer",
                  data: this.transData,
                },
              ],
            });
          } else {
            this.transformerChart.setOption({
              series: [
                {
                  id: "temperature",
                  data: this.transData,
                },
              ],
            });
          }

          if (this.$store.state.status === "running") {
            this.count += 1;
          } else {
            this.count = 0;
          }
        } catch (e) {
          console.log(e);
          console.log("The raw data are not ready");
        }
      }, 500);
    },
    enableGIC() {
      this.gicEnabled = true;
      this.transformerMap.removeControl(this.legend);
      this.legend = window.L.control({ position: "bottomleft" });
      this.legend.onAdd = function (map) {
        var div = window.L.DomUtil.create("div", "legend legend-background");
        let labels = ["<strong>Categories</strong>"];
        const categories = [
          "Positive Neutral Current",
          "Negative Neutral Current",
        ];
        const color = ["rgba(0, 200, 0, 0.5)", "rgba(0, 0, 200, 0.5)"];
        for (var i = 0; i < categories.length; i++) {
          div.innerHTML +=
            '<span class="circle" style="background:' +
            color[i] +
            '"></span>' +
            categories[i] +
            "<br>";
        }
        // div.innerHTML = labels.join('<br>');
        // console.log(div)
        return div;
      };
      this.legend.addTo(this.transformerMap);
      let tempOption = {
        series: [
          {
            id: "transformer",
            symbolSize: (value, params) => {
              if (params.data.attribute.GICNeutralCurrent) {
                const current = Math.abs(
                  params.data.attribute.GICNeutralCurrent
                );
                if (current < 1) {
                  return 5;
                } else if (current < 5) {
                  return 10;
                } else if (current < 10) {
                  return 15;
                } else if (current < 20) {
                  return 20;
                } else if (current < 50) {
                  return 25;
                } else {
                  return 50;
                }
              }
            },
          },
          {
            id: "temperature",
            symbolSize: 0,
            data: [],
          },
        ],
      };
      this.transformerChart.setOption(tempOption);
    },
    enableTemp() {
      this.gicEnabled = false;
      this.transformerMap.removeControl(this.legend);
      this.legend = window.L.control({ position: "bottomleft" });
      this.legend.onAdd = function (map) {
        var div = window.L.DomUtil.create("div", "legend legend-background");
        let labels = ["<strong>Categories</strong>"];
        const categories = ["<60", "60~80", "80~100", ">100"];
        const color = [
          "rgba(0, 0, 200, 0.8)",
          "rgba(0, 200, 0, 0.8)",
          "rgba(200, 200, 0, 0.8)",
          "rgba(255, 0, 0, 1)",
        ];
        for (var i = 0; i < categories.length; i++) {
          div.innerHTML +=
            '<span class="circle" style="float:left;background:' +
            color[i] +
            '"></span>' +
            categories[i] +
            "<br>";
        }
        // div.innerHTML = labels.join('<br>');
        // console.log(div)
        return div;
      };
      this.legend.addTo(this.transformerMap);
      let tempOption = {
        series: [
          {
            id: "transformer",
            symbolSize: 0,
            data: [],
          },
          {
            id: "temperature",
            symbolSize: 10,
          },
        ],
      };
      this.transformerChart.setOption(tempOption);
    },
    toggle(item) {
      var command;
      if (item.vStatus) {
        item.vStatus = 1;
        command = "CLOSE BOTH";
      } else {
        item.vStatus = 0;
        command = "OPEN BOTH";
      }
      // console.log(item);
      this.toggleTransformer(item, command);
    },
    async toggleTransformer(item, command) {
      try {
        const { deviceApi } = await import("@/services/api");
        if (command === "OPEN BOTH") {
          await deviceApi.openBranch(item.key);
        } else {
          await deviceApi.closeBranch(item.key);
        }
      } catch (e) {
        console.error("Transformer command failed:", e);
      }
    },
  },
  created() {
    // this.preProcess();
    // this.initTable();
  },
  mounted() {
    // this.initTable();
    this.initTable().then(() => this.updateTable());
    this.initdraw();
  },
  watch: {},
  computed: {
    tempEnabled() {
      return !this.gicEnabled;
    },
  },
  beforeDestroy() {
    this.updateTable = () => {};
  },
};
</script>