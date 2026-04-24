<template>
  <!-- Creates a container to store all of our components. -->
  <v-container grid-list-xl text-xs-center fluid>
    <!-- Creating the generation bar chart. -->
    <v-layout row wrap>
      <v-flex lg6 sm12 xs12>
        <pieDistribute :areatotal="areaGenMw"></pieDistribute>
      </v-flex>
      <v-flex lg6 sm12 xs12>
        <div id="genpie" class="genpie" />
      </v-flex>
    </v-layout>
  </v-container>
</template>

<style>
/** For PowerWeb, the size needs to be in pixel format. */
.genpie {
  width: 100%;
  height: 900px;
}
</style>

<script>
import pieDistribute from "@/components/pieDistribute";
import { mapGetters } from "vuex";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from "echarts/components";
import darkTheme from "../assets/dark.js";

echarts.use([
  CanvasRenderer,
  BarChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
]);
echarts.registerTheme('dark', darkTheme);

let chart = null;

export default {
  name: "genpie",
  components: {
    pieDistribute,
  },

  data() {
    return {
      genName: [],
      genPie: {
        title: {
          text: "Current Generation Distribution (By Generator)",
          textStyle: {
            fontSize: 24,
          },
          x: "center",
        },
        grid: {
          right: "3%",
          left: "3%",
          bottom: 100,
        },
        tooltip: {
          trigger: "item",
          formatter: "{a} <br/>{b} : {c} ({d}%)",
        },
        legend: {
          type: "scroll",
          orient: "horizontal",
          bottom: 20,
          data: [],
        },
        series: [
          {
            name: "Current Generation",
            id: "gen",
            data: [],
            type: "pie",
          },
        ],
      },
    };
  },
  methods: {
    initGenPlot() {
      const genData = this.getGenData;
      for (let i in genData) {
        this.genName.push(genData[i]["name"]);
      }
      this.genPie.legend.data = this.genName;
    },
    updateGenPlot() {
      try {
        const genData = this.getGenData;
        var temp = [];
        for (let i in genData) {
          temp.push({
            name: genData[i]["name"],
            value: genData[i]["MW"],
          });
        }
        chart.setOption({
          series: [
            {
              id: "gen",
              data: temp,
            },
          ],
        });
      } catch (e) {
        console.log(e);
      }
    },
    reload() {
      setTimeout(() => {
        if (chart) {
          chart.resize();
        }
      }, 800);
    },
  },
  computed: {
    ...mapGetters(["getGenData", "getAreaData"]),
    areaGenMw() {
      return this.getAreaData ? this.getAreaData.gen_mw : 0;
    },
  },
  mounted() {
    this.initGenPlot();
    chart = echarts.init(document.getElementById("genpie"), "dark");
    chart.setOption(this.genPie);
    this.Process = setInterval(() => {
      this.updateGenPlot();
    }, 1000);
    window.addEventListener("resize", this.reload);
  },
  beforeDestroy() {
    clearInterval(this.Process);
  },
  destroyed() {
    window.removeEventListener("resize", this.reload);
  },
};
</script>
