<template>
  <div id="oneline-map" class="oneline-map"></div>
</template>

<script>
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
  name: "OneLine",
  data() {
    return {
      map: null,
      subLayer: null,
      lineLayer: null,
      otherSubLayer: null,
      otherLineLayer: null,
    };
  },
  methods: {
    initMap() {
      this.map = L.map("oneline-map", {
        center: [32, -99.4936],
        maxZoom: 18,
        zoom: 7,
        preferCanvas: true,
      });

      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        { attribution: '&copy; OpenStreetMap &copy; CARTO' }
      ).addTo(this.map);

      this.subLayer = L.layerGroup().addTo(this.map);
      this.lineLayer = L.layerGroup().addTo(this.map);
      this.otherSubLayer = L.layerGroup().addTo(this.map);
      this.otherLineLayer = L.layerGroup().addTo(this.map);

      const legend = L.control({ position: "topright" });
      legend.onAdd = function () {
        const div = L.DomUtil.create("div", "");
        div.style.cssText = "background:rgba(30,30,30,0.88);color:#e0e0e0;padding:10px 14px;font-size:13px;line-height:2;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.3);";
        const dot = function (color) {
          return '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:' + color + ';margin-right:6px;vertical-align:middle;border:1px solid rgba(255,255,255,0.15);"></span>';
        };
        const line = function (color, label) {
          return '<span style="display:inline-block;width:18px;height:3px;background:' + color + ';margin-right:6px;vertical-align:middle;border-radius:2px;"></span>' + label;
        };
        div.innerHTML =
          '<div style="font-weight:600;margin-bottom:4px;">Substations</div>' +
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
      for (const sub of this.$store.state.subData) {
        const attrs = sub.attributes || {};
        let color = SUB_COLORS.default;
        let radius = 5;
        if (attrs.Gen) { color = SUB_COLORS.Gen; radius = 7; }
        else if (attrs.Shunt) { color = SUB_COLORS.Shunt; radius = 6; }

        L.circleMarker([sub.value[1], sub.value[0]], {
          radius,
          color,
          fillOpacity: 0.9,
          weight: 1,
          opacity: 1,
        }).addTo(this.subLayer).bindTooltip("Substation: " + sub.name);
      }
    },

    drawLines() {
      this.lineLayer.clearLayers();
      for (const line of this.$store.state.lineData) {
        const volt = line.attributes ? line.attributes.volt : 0;
        const color = VOLT_COLORS[volt] || "#757575";
        const coords = line.coords.map(function (c) { return [c[1], c[0]]; });

        L.polyline(coords, {
          color,
          weight: 1.5,
          opacity: 1,
        }).addTo(this.lineLayer).bindTooltip("Branch: " + line.name);
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
        L.polyline(b.coords.map(function (c) { return [c[1], c[0]]; }), {
          color: "#757575",
          weight: 0.5,
          opacity: 0.5,
        }).addTo(this.otherLineLayer);
      }
    },
  },
  mounted() {
    this.initMap();

    const drawData = () => {
      if (this.$store.state.subData.length > 0 && this.subLayer.getLayers().length === 0) {
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
  beforeDestroy() {
    if (this._unwatch) this._unwatch();
    if (this.map) { this.map.remove(); this.map = null; }
  },
};
</script>

<style scoped>
.oneline-map {
  height: calc(100vh - 64px - 50px);
  width: 100%;
}
</style>
