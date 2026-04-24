<template>
  <div>
    <v-dialog v-model="show" :key="id" width="900">
      <v-toolbar dark flat>
        <v-toolbar-title>{{ name }} {{ volt }} {{ type }}</v-toolbar-title>
        <template v-slot:extension>
          <v-tabs centered v-model="currentItem">
            <v-tabs-slider color="brown"></v-tabs-slider>
            <v-tab
              :key="'General'"
              :href="'#tab-General'"
              @click="atDefault = true"
              >General</v-tab
            >
            <v-tab
              v-for="item in tabs"
              :key="item"
              :href="'#tab-' + item"
              @click="atDefault = false"
              >{{ item }}</v-tab
            >
          </v-tabs>
        </template>
      </v-toolbar>
      <v-tabs-items v-model="currentItem">
        <v-tab-item :value="'tab-General'" :key="'General'">
          <v-card>
            <v-card-title class="headline"> Data </v-card-title>
            <v-data-table
              :headers="headers"
              :items="display"
              hide-default-footer
              class="elevation-1"
              lazy
            >
              <template slot="items" slot-scope="props">
                <td
                  class="text-xs-right"
                  v-for="item in props.item"
                  :key="item.text"
                >
                  {{ item }}
                </td>
              </template>
            </v-data-table>
          </v-card>
        </v-tab-item>
        <v-tab-item
          v-for="(item, index) in tabs"
          :value="'tab-' + item"
          :key="item"
        >
          <popchild
            v-if="show"
            :name="item"
            :detail="children[index]"
            :subname="name"
            :show="currentItem"
            lazy
          ></popchild>
        </v-tab-item>
      </v-tabs-items>
    </v-dialog>
  </div>
</template>

<script>
export default {
  data() {
    return {
      currentItem: "tab-General",
      display: [],
      atDefault: true,
      headers: [
        { text: "Substation", value: "Substation" },
        { text: "Latitude", value: "Latitude" },
        { text: "Longitude", value: "Longitude" },
      ],
    };
  },
  props: {
    visible: { type: Boolean, default: false },
    type: { type: String },
    id: { type: String },
    name: { type: String },
    volt: { type: String },
    children: {},
  },
  computed: {
    show: {
      get() { return this.visible; },
      set(value) {
        if (!value) {
          this.display = [];
          this.$emit("close");
        }
      },
    },
    tabs: function () {
      let temp = [];
      for (var ele in this.children) {
        temp.push("Bus " + this.children[ele]["Int.Bus Number"].toString());
      }
      return temp;
    },
  },
  watch: {
    visible: function(val) {
      if (val && this.atDefault) {
        this.getData();
      }
    },
  },
  methods: {
    getData() {
      const caseData = this.$store.state.caseData;
      if (!caseData) return;
      const subs = caseData.content.Substation || {};
      const sub = subs[this.id];
      if (sub) {
        this.display = [{
          Substation: sub["String.Name"],
          Latitude: sub["Double.Latitude"],
          Longitude: sub["Double.Longitude"],
        }];
      }
    },
  },
  components: {
    popchild: () => import("./popchild"),
  },
};
</script>
