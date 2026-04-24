<template>
  <div id="pie" class="chartdiv"></div>
</template>
<style scoped>
.chartdiv {
  z-index: 0;
  height: 300px;
  width: 100%;
}
</style>

<script>
import Material from "vuetify/es5/util/colors";
import { mapGetters } from "vuex";
import * as echarts from "echarts/core";
import { PieChart } from "echarts/charts";
import { TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import darkTheme from "../assets/dark.js";
echarts.registerTheme('dark', darkTheme);

echarts.use([TooltipComponent, LegendComponent, PieChart, CanvasRenderer]);

export default {
  props: {
    areatotal: Number,
  },
  data() {
    return {
      chart: "",
      color: Material,
      Process: null,
    };
  },
  methods: {
    initdraw() {
      this.chart = echarts.init(document.getElementById("pie"), "dark");
      this.chart.setOption({
        legend: { bottom: "0" },
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
        this.chart.setOption({
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
    resizeChart() {
      window.onresize = () => {
        if (this.chart) {
          this.chart.resize();
        }
      };
    },
  },
  computed: {
    ...mapGetters(["getGenStat"]),
  },
  mounted() {
    this.initdraw();
    this.resizeChart();
    this.Process = setInterval(() => {
      this.updateData();
    }, 1000);
  },
  beforeDestroy() {
    clearInterval(this.Process);
    this.chart.clear();
  },
};
</script>
