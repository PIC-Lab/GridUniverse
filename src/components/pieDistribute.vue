<template>
  <div id="pie" class="chartdiv"></div>
</template>
<style scoped>
.chartdiv {
  height: 900px;
  width: 100%;
}
</style>

<script>
import Material from "vuetify/es5/util/colors";
import { mapGetters } from "vuex";
import * as echarts from "echarts/core";
import { PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import darkTheme from "../assets/dark.js";
echarts.registerTheme('dark', darkTheme);

echarts.use([
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  PieChart,
  CanvasRenderer,
]);

let chart = null;

export default {
  props: {
    areatotal: Number,
  },
  data() {
    return {
      color: Material,
      Process: null,
    };
  },
  methods: {
    initdraw() {
      chart = echarts.init(document.getElementById("pie"), "dark");
      chart.setOption({
        title: {
          text: "Area Generation Overview",
          textStyle: { fontSize: 24 },
          x: "center",
        },
        legend: { bottom: 20 },
        color: [
          this.color.lightBlue.base,
          this.color.indigo.base,
          this.color.pink.base,
        ],
        series: [
          {
            id: "pie",
            type: "pie",
            center: ["50%", "50%"],
            radius: ["30%", "60%"],
            selectedMode: "single",
            label: {
              position: "outside",
              formatter: "{a|{b}}\n{hr|}\n{c|{c} MW}\n{hr|}\n{per|{d}%}{abg|}",
              backgroundColor: "#eee",
              borderColor: "#aaa",
              borderWidth: 1,
              borderRadius: 4,
              rich: {
                a: { color: "#000", lineHeight: 22, align: "center" },
                abg: { backgroundColor: "#333", width: "100%", align: "right", height: 15, borderRadius: [0, 0, 4, 4] },
                hr: { borderColor: "#aaa", width: "100%", borderWidth: 0.5, height: 0 },
                b: { fontSize: 16, lineHeight: 33 },
                c: { color: "#999", lineHeight: 20, align: "center" },
                per: { color: "#eee", align: "center" },
              },
            },
            labelLine: { show: true },
            data: [],
            emphasis: {
              itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0, 0, 0, 0.5)" },
            },
          },
        ],
      });
    },
    updateData() {
      try {
        const genStat = this.getGenStat || [0, 0];
        chart.setOption({
          series: {
            id: "pie",
            data: [
              { value: Math.round(this.areatotal), name: "Current Generation" },
              { value: genStat[0], name: "Online Capacity" },
              { value: Math.round(genStat[1]), name: "Offline Capacity" },
            ],
          },
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
    ...mapGetters(["getGenStat"]),
  },
  mounted() {
    this.initdraw();
    this.Process = setInterval(() => {
      this.updateData();
    }, 1000);
    window.addEventListener("resize", this.reload);
  },
  beforeDestroy() {
    clearInterval(this.Process);
    chart.clear();
  },
  destroyed() {
    window.removeEventListener("resize", this.reload);
  },
};
</script>
