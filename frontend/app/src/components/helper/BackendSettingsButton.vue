<template>
  <v-bottom-sheet v-model="visible" width="98%" class="backend-settings-button">
    <template #activator="{ on: menu, attrs }">
      <v-tooltip left max-width="280">
        <template #activator="{ on: tooltip }">
          <v-btn
            v-bind="attrs"
            text
            fab
            depressed
            :disabled="!connected"
            color="primary"
            v-on="{ ...menu, ...tooltip }"
          >
            <v-icon>mdi-cog</v-icon>
          </v-btn>
        </template>
        <span>{{ $t('backend_settings_button.tooltip') }}</span>
      </v-tooltip>
    </template>
    <backend-settings v-if="visible" @dismiss="visible = false" />
  </v-bottom-sheet>
</template>

<script lang="ts">
import { defineComponent, ref, toRefs } from 'vue';
import BackendSettings from '@/components/settings/BackendSettings.vue';
import { useMainStore } from '@/store/main';

export default defineComponent({
  name: 'BackendSettingsButton',
  components: { BackendSettings },
  setup() {
    const visible = ref<boolean>(false);
    const { connected } = toRefs(useMainStore());
    return { visible, connected };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
  .v-card {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
  }
}

.backend-settings-button {
  height: calc(100vh - 80px);
}
</style>
