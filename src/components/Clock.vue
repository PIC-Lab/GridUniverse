<template>
    <div id="MyClockDisplay" class="clock"></div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
    methods: {
        showTime() {
            if (this.getClockTime) {
                document.getElementById("MyClockDisplay").innerText = this.getClockTime;
                document.getElementById("MyClockDisplay").textContent = this.getClockTime;
            }
        }
    },
    mounted() {
        this.showTime();
    },
    computed: {
        ...mapGetters(['getClockTime', 'getCurrentTime'])
    },
    watch: {
        getCurrentTime: function() {
            this.showTime();
        }
    }
}
</script>

<style>
.clock {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translateX(-50%) translateY(-50%);
    color: rgb(201, 239, 248);
    font-size: 20px;
}
</style>
