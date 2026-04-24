<template></template>

<script>
import { orderBy } from "lodash";
import { mapGetters } from "vuex";

export default {
  data() {
    return {
      show: false,
      Interval: null,
    };
  },
  methods: {
    async dispatchAGC(unit) {
      let new_setpoint, command;
      const ace = this.getAreaData ? this.getAreaData.ace || 0 : 0;
      new_setpoint = Math.min(
        unit.MWMax,
        Math.max(unit.MW + ace, 0)
      ).toFixed(2);
      if (new_setpoint != unit.MWSetpoint) {
        command = "Set Power " + new_setpoint + " MW";
        try {
          const { deviceApi } = await import("@/services/api");
          await deviceApi.setGenPower(unit.key + "," + unit.id, parseFloat(new_setpoint));
          this.$store.commit("addReportUser", {
            time: this.getCurrentTime,
            event: ["AGC", unit.key + "," + unit.id, command],
          });
        } catch (e) {
          console.error("AGC dispatch failed:", e);
        }
      }
    },
    updateAGC() {
      this.Interval = setInterval(() => {
        if (this.getStatus === "running") {
          const ace = this.getAreaData ? this.getAreaData.ace || 0 : 0;
          if (ace) {
            const activeunits = this.getGenData.filter(g => g.AGC);
            if (activeunits.length > 0) {
              let sorted_units;
              if (ace > 0) {
                sorted_units = orderBy(activeunits, ["MarginalCost"], ["asc"]);
              } else {
                sorted_units = orderBy(activeunits, ["MarginalCost"], ["desc"]);
              }
              for (let i in sorted_units) {
                if (sorted_units[i].MWSetpoint < sorted_units[i].MWMax && ace > 0) {
                  this.dispatchAGC(sorted_units[i]);
                  break;
                } else if (sorted_units[i].MWSetpoint > sorted_units[i].MWMin && ace < 0) {
                  this.dispatchAGC(sorted_units[i]);
                  break;
                }
              }
            }
          }
        }
      }, 3000);
    },
  },
  computed: {
    ...mapGetters(["getGenData", "getAreaData", "getStatus", "getCurrentTime"]),
  },
  created() {
    this.updateAGC();
  },
  beforeDestroy() {
    clearInterval(this.Interval);
  },
};
</script>
