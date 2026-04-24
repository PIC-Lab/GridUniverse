<template>
  <!-- Creates a container to store all of our components. -->
  <v-container grid-list-xl text-xs-center fluid>
    <!-- Creating the generation bar chart. -->
    <v-layout row wrap>
      <v-flex lg12 sm12 xs12>
        <div id="barplot" class="barplot"/>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<style>
/** For PowerWeb, the size needs to be in pixel format. */
.barplot {
  width: 100%;
  height: 800px;
}
</style>

<script>
import { mapGetters } from "vuex";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  SingleAxisComponent,
} from "echarts/components";
import darkTheme from "../assets/dark.js";
echarts.registerTheme('dark', darkTheme);

echarts.use([
  CanvasRenderer,
  BarChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  SingleAxisComponent,
]);

let chart = '';

export default {
  name: "barplot",
  data() {
    return {
      genXaxis: [],
      genYaxis: [],
      maxGen: [],
    };
  },
  methods: {
    initGenPlot() {
      const genData = this.getGenData;
      for (let i in genData) {
        this.genXaxis.push(genData[i]["name"]);
        this.genYaxis.push(genData[i]["MW"]);
        this.maxGen.push(genData[i]["MWMax"]);
      }
    },
    updateGenPlot() {
      try {
        var temp = [];
        const genData = this.getGenData;
        for (let i in genData) {
          temp.push(genData[i]["MW"]);
          this.genYaxis = temp;
        }
        chart.setOption(this.genBar);
      } catch (e) {
        console.log(e);
      }
    },
  },
  computed: {
    ...mapGetters(["getGenData"]),
    genBar() {
      return {
        title: {
          text: "Current Generation",
          left: "center",
          textStyle: {
            fontSize: 48,
          },
        },
        grid: {
          right: "3%",
          left: "3%",
          bottom: 100,
        },
        xAxis: {
          type: "category",
          data: this.genXaxis,
          axisLabel: {
            rotate: 90,
            inside: true,
            fontWeight: "bold",
            fontSize: 16,
          },
          z: 3,
        },
        yAxis: {
          type: "value",
          axisLine: {
            show: false,
          },
        },
        tooltip: {
          trigger: "axis",
        },
        series: [
          {
            name: "Current Generation",
            data: this.genYaxis,
            type: "bar",
          },
          {
            name: "Maximum Generation",
            data: this.maxGen,
            type: "bar",
            itemStyle: {
              color: "none",
              borderColor: "#ddd",
              borderWidth: 3,
              borderRadius: 0,
            },
            barGap: "-100%",
            barCategoryGap: "40%",
          },
        ],
      };
    },
  },
  mounted() {
    this.initGenPlot();
    chart = echarts.init(document.getElementById("barplot"), "dark");
    chart.setOption(this.genBar);
    this.Process = setInterval(() => {
      this.updateGenPlot();
    }, 1000);
  },
  beforeDestroy() {
    clearInterval(this.Process);
  },
};
</script>
