<template>
  <div>
    <chatpop
      v-if="chatShow"
      :visible="chatShow"
      :topic="chatTopic"
      @close="chatShow = false"
    ></chatpop>
    <linepop
      v-if="lineshowDialog"
      :visible="lineshowDialog"
      :type="type"
      :id="id"
      :name="name"
      @close="lineshowDialog = false"
    />
    <subpop
      v-if="subshowDialog"
      :visible="subshowDialog"
      :children="children"
      :type="type"
      :id="id"
      :name="name"
      @close="subshowDialog = false"
    />
  </div>
</template>

<script>
import iziToast from "izitoast/dist/js/iziToast.min.js";
import { caseApi, setBaseUrl } from "../services/api";

let ws = null;
let reconnectTimer = null;

export default {
  name: "ConnectionManager",
  data() {
    return {
      chatShow: false,
      chatTopic: "",
      id: null,
      type: null,
      lineshowDialog: false,
      subshowDialog: false,
      children: {},
      name: "",
    };
  },
  mounted() {
    this.connect();
  },
  beforeDestroy() {
    this.disconnect();
  },
  methods: {
    async connect() {
      const info = this.$store.state.loginInfo;
      const serverUrl = info.serverUrl || this.$store.state.serverUrl;
      setBaseUrl(serverUrl);

      try {
        const caseData = await caseApi.getCase();
        this.$store.commit("setCaseData", caseData);
        iziToast.success({
          title: "System",
          message: "Case data loaded",
          position: "topRight",
        });
      } catch (e) {
        iziToast.error({
          title: "System",
          message: "Failed to load case data: " + e.message,
          position: "topRight",
          timeout: 5000,
        });
        return;
      }

      this.connectWebSocket(serverUrl);
    },

    connectWebSocket(serverUrl) {
      const wsUrl = serverUrl
        .replace(/^http/, "ws")
        .replace(/^https/, "wss");
      const url = `${wsUrl}/ws/sim`;

      ws = new WebSocket(url);

      ws.onopen = () => {
        this.$store.commit("setWsConnected", true);
        iziToast.success({
          title: "System",
          message: "WebSocket connected",
          position: "topRight",
        });
      };

      ws.onclose = () => {
        this.$store.commit("setWsConnected", false);
        iziToast.error({
          title: "System",
          message: "WebSocket disconnected, reconnecting...",
          position: "topRight",
        });
        reconnectTimer = setTimeout(() => this.connectWebSocket(serverUrl), 3000);
      };

      ws.onerror = () => {
        // onclose will fire after this
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };
    },

    disconnect() {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        ws.close();
        ws = null;
      }
    },

    handleMessage(msg) {
      if (msg.type === "tick") {
        this.$store.commit("updateSimState", msg.data);
      } else if (msg.type === "event") {
        this.handleSimEvent(msg.data);
      } else if (msg.type === "note") {
        this.handleNotification(msg.data);
      }
    },

    handleSimEvent(text) {
      iziToast.warning({
        title: "System",
        message: text,
        position: "topCenter",
        timeout: 6500,
      });

      if (
        text.includes("blackout") ||
        text.includes("aborted") ||
        text.includes("finished")
      ) {
        this.$store.commit("setstartready");
      }

      this.$store.commit("updatebadge");
      this.$store.commit("updatebadgelist", {
        title: text,
        source: "System",
        color: "red",
        time: Date.now(),
      });
    },

    handleNotification(text) {
      if (this.$store.state.notMuted) {
        iziToast.warning({
          title: "System",
          message: text,
          position: "topCenter",
          timeout: 3000,
          buttons: [
            [
              "<button>What?!</button>",
              () => {
                const temp = text.split("@");
                if (text.includes("Branch")) {
                  this.id = temp[1];
                  this.name = temp[2] || "";
                  this.type = "Branch";
                  this.lineshowDialog = true;
                } else if (
                  text.includes("Load") ||
                  text.includes("Gen") ||
                  text.includes("Shunt")
                ) {
                  const busid = (temp[1] || "").split(",")[0];
                  this.name = (temp[2] || "").split("Bus")[0];
                  this.type = "Substation";
                  const subDetail = this.$store.state.caseData?.content?.Substation;
                  if (subDetail && busid) {
                    for (const subidx in subDetail) {
                      const found = (subDetail[subidx].Bus || []).find(
                        (ele) => ele["Int.Bus Number"] == busid
                      );
                      if (found) {
                        this.id = subidx;
                        this.children = subDetail[subidx].Bus;
                        this.subshowDialog = true;
                        break;
                      }
                    }
                  }
                }
              },
            ],
          ],
        });
      }

      this.$store.commit("updatebadge");
      this.$store.commit("updatebadgelist", {
        title: text,
        source: "System",
        color: "yellow",
        time: Date.now(),
      });
    },
  },
  components: {
    chatpop: () => import("./chatpop"),
    linepop: () => import("./linepop"),
    subpop: () => import("./subpop"),
  },
};
</script>
