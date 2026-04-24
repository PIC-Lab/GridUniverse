<template>
	<v-layout row justify-center>
		<v-dialog v-model="show" max-width="500px">
			<v-card>
				<v-card-title>
					<span class="headline">Start</span>
				</v-card-title>
				<v-card-text>
					<v-container grid-list-md>
						<v-layout wrap>
							<v-flex xs12>
								<v-text-field disabled label="Seconds to stop" v-model.lazy="time" required :rules="[rules.prohibited]" @keyup.enter="enterClicked"></v-text-field>
							</v-flex>
						</v-layout>
					</v-container>
				</v-card-text>
				<v-card-actions>
					<v-spacer></v-spacer>
					<v-btn color="blue darken-1" text @click.native="activate">Activate</v-btn>
				</v-card-actions>
			</v-card>
		</v-dialog>
	</v-layout>
</template>

<script>
import { simApi } from "../services/api";

export default {
	props: {
		visible: {
			type: Boolean,
			default: false,
		},
		topic: {
			default: "",
		},
	},
	data() {
		return {
			content: "",
			time: null,
			rules: {
				prohibited: (value) =>
					(value != "data" && value != "user" && value != "note") ||
					"Cannot use the reserved topic",
			},
		};
	},
	computed: {
		show: {
			get() {
				return this.visible;
			},
			set(value) {
				if (!value) {
					this.display = [];
					this.childshow = false;
					this.$emit("close");
				}
			},
		},
	},
	methods: {
		async activate() {
			try {
				if (!this.time) {
					if (this.$store.state.simState?.status !== "paused") {
						await simApi.start();
					} else {
						await simApi.continue();
					}
				} else {
					await simApi.runTo(parseInt(this.time));
				}
			} catch (e) {
				console.error("Failed to start simulation:", e);
			}
			this.show = false;
		},
		enterClicked() {
			this.activate();
		},
	},
};
</script>
