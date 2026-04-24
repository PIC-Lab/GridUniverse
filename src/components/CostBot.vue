<template>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  computed: {
    ...mapGetters(['getGenData', 'getAreaData', 'getStatus']),
  },
  methods: {
    updateTotalCost() {
      this.Interval = setInterval(() => {
        if (this.getStatus !== "running") return;
        const gens = this.getGenData;
        if (!gens || gens.length === 0) return;
        let deltaCost = 0;
        let deltaMWh = 0;
        for (let i in gens) {
          const coeffs = gens[i].MarginalCostCoefficients || [0, 0];
          deltaCost += coeffs[0] * gens[i].MW + coeffs[1] * gens[i].MW * gens[i].MW;
          deltaMWh += gens[i].MW;
        }
        this.$store.commit('updateUnitTimeCost', +deltaCost.toFixed(0));
        deltaCost = deltaCost / 120;
        deltaMWh = deltaMWh / 120;
        this.$store.commit('addCost', +deltaCost.toFixed(0));
        this.$store.commit('addMWh', +deltaMWh.toFixed(2));
      }, 500);
    }
  },
  created() {
    this.updateTotalCost();
  },
  beforeDestroy() {
    clearInterval(this.Interval);
  }
};
</script>
